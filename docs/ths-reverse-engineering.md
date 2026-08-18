# 同花顺网页版接口逆向记录（THS Reverse-Engineering Notes）

> 本文档记录对同花顺网页版登录 / 自选 / 持仓接口的逆向分析结果，供复现、校验与
> 失效时修复参考。**代码实现见 `backend/app/ths_client/README.md`（更权威、以代码为准）。**

> ⚠️ **合规提醒**：本模块为**只读**客户端，仅实现扫码登录与会话保活、自选与持仓查询。
> 严禁添加任何下单 / 撤单 / 委托 / 交易方法；相关约束由 `web_client.py` 顶部注释、
> `ThsAdapter` 抽象接口与 `scripts/check_no_trade.py` 静态检查三重保证。

## 接口契约表

默认前缀：`https://eq.10jqka.com.cn`（环境变量 `IB_THS_ENDPOINT` 可覆盖）。
所有请求为 GET，需登录态的请求自动附带 `Authorization: Bearer <token>`（token 来自 Vault 解密）。

| # | 路径 | 用途 | 请求参数 | 响应（简化） | 本地处理 |
| --- | --- | --- | --- | --- | --- |
| 1 | `GET /qrcode` | 获取登录二维码 | 无 | `{"data":{"qrcode":"<base64>"}}` | 缓存 `data`，返回 `{"qrcode_data": ...}` |
| 2 | `GET /poll` | 轮询扫码结果 | 无 | `{"data":{"status":1,"token":"...","user":"..."}}` | `status==1` → token 经 Vault 加密持久化，返回 `True` |
| 3 | `GET /watchlist` | 自选列表 | 无（需登录） | `{"data":[{"code","name","market"}]}` | `parse_watchlist` → `list[Stock]`，`market` 缺省 `"SH"` |
| 4 | `GET /positions` | 持仓列表 | 无（需登录） | `{"data":[{"code","name","amount","cost","enable_amount"}]}` | `parse_positions` → `list[Position]` |
| 5 | `GET /session/check` | 会话保活 | 无（需登录） | `{"data":{...}}`（200） | 成功 `True`，异常捕获返回 `False` |

### 字段映射

| 接口字段 | 本地字段 | 说明 |
| --- | --- | --- |
| `amount` | `Position.quantity` | 持股数量（股） |
| `cost` | `Position.cost_price` | 成本价 |
| `enable_amount` | `Position.available` | 可用数量（缺省 0） |
| `market` | `Stock.market` | 市场，缺省 `"SH"` |

### 校验状态

- 各 endpoint 路径与字段来自对同花顺网页版登录 / 自选 / 持仓流程的逆向分析。
- **需通过浏览器开发者工具抓包核实，若有出入以实测为准。** 建议在接入前用真实扫码流程
  校验字段名与嵌套层级。

## 抓包方法

### 方法 A：浏览器开发者工具（推荐，无需额外工具）

1. 用 Chrome / Edge 打开同花顺网页版登录页。
2. `F12` → `Network`（网络）面板，勾选 `Preserve log`（保留日志）。
3. 执行扫码登录，观察以下请求：`/qrcode`、`/poll`、`/watchlist`、`/positions`、`/session/check`。
4. 逐个点击请求，查看 `Request URL`、`Request Headers`（尤其是 `Authorization`）与
   `Response`（Preview / Response）中的字段嵌套。
5. 与上表比对，记录差异。

### 方法 B：代理抓包（Charles / mitmproxy / Fiddler）

1. 配置系统代理（如 mitmproxy：`mitmweb --listen-port 8080`）。
2. 浏览器 / 移动端安装并信任根证书。
3. 复现登录与查询流程，过滤 `eq.10jqka.com.cn` 域名。

### 核实要点

- 响应是否包裹在 `{"data": ...}` 中、`data` 是对象还是数组。
- `status == 1` 是否仍是「扫码成功」语义。
- token 字段名、`Authorization` 前缀（当前实现假定 `Bearer`）。
- 二维码返回的是 base64 图片数据还是其他编码。

## 失效时的降级行为

- **THS 接口失效**（404 / 超时 / 风控 / 会话过期）：
  - 登录与查询方法抛异常 → `Scheduler` 捕获并记 `WARNING` 日志；
  - 持仓循环仅在 `ths.is_logged_in` 为真时执行，失败返回空持仓；
  - 行情 / 新闻采集**不受影响**，照常运行；
  - 前端健康灯显示 THS 状态异常，界面提示「自选 / 持仓暂不可用」。
- **会话保活失败**：`refresh_session()` 返回 `False`，前端提示重新扫码登录。
- **全局原则**：所有外部调用均带超时（10s）与异常捕获，绝不因第三方接口变化导致崩溃。

## PR 指引（接口变化时的修复流程）

当抓包发现契约变化时，按以下流程提交修复：

1. **更新契约文档**：同步修改 `backend/app/ths_client/README.md` 与本文档的契约表。
2. **更新解析器**：`backend/app/ths_client/parsers.py`（字段名 / 嵌套层级映射）。
   - 保持向后兼容：新字段用 `.get()` 给默认值，不破坏旧格式。
3. **配套测试**：在 `backend/tests/test_ths_client.py` 中用 `respx` 模拟新响应文本，
   驱动纯函数解析器断言（不依赖真实账号与网络）。
   ```bash
   cd backend && .venv/bin/pytest tests/test_ths_client.py -q
   ```
4. **合规检查**：确保未引入任何交易语义代码：
   ```bash
   make check   # scripts/check_no_trade.py 必须通过
   ```
5. **全量回归**：`make check && make test && make build` 全绿。
6. 提交 PR，说明抓包截图与字段变更对照，方便 reviewer 快速核验。

## 常见接口失效现象

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| `/qrcode` 或 `/poll` 返回 404 / 字段变化 | 登录接口改版 | 重新抓包，更新契约与解析器 |
| 扫码成功但 `status != 1` | 轮询语义变化 | 核实 `status` 含义，必要时加日志 |
| 请求被风控 / 429 | 访问过于频繁 | 确认限频（≥10s + 抖动）未被改动 |
| 会话保活频繁失败 | token 过期 / 接口变更 | 重新扫码登录；若持续失败按上文抓包核实 |
