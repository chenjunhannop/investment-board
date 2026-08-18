# 同花顺网页版接口逆向记录（THS Reverse-Engineering Notes）

> ⚠️ **已废弃（2026-08-18）：项目已移除同花顺集成，本文件仅作历史记录。**
> 同花顺客户端（`ths_client`）、会话保险箱（`vault`）与持仓模块均已删除，
> 项目回归纯公开数据源，不再引用本文件中的任何接口。

> 本文档记录对同花顺网页版登录 / 自选 / 持仓接口的逆向分析结果，供复现、校验与
> 失效时修复参考。**代码实现见 `backend/app/ths_client/README.md`（更权威、以代码为准）。**

> ⚠️ **合规提醒**：本模块为**只读**客户端，仅实现扫码登录与会话保活、自选与持仓查询。
> 严禁添加任何下单 / 撤单 / 委托 / 交易方法；相关约束由 `web_client.py` 顶部注释、
> `ThsAdapter` 抽象接口与 `scripts/check_no_trade.py` 静态检查三重保证。

## 接口契约表

默认前缀：`https://upass.10jqka.com.cn`（环境变量 `IB_THS_ENDPOINT` 可覆盖）。
登录态以 **cookie 会话** 传递（不再使用 `Authorization: Bearer <token>`）；cookie 在登录成功时
捕获，经 Vault AES-256-GCM 加密存本机，查询前由 `_apply_session()` 恢复。

| # | 路径 | 用途 | 请求参数 | 响应（简化） | 本地处理 |
| --- | --- | --- | --- | --- | --- |
| 1 | `GET /scan/creatCode` | 获取登录二维码 qrid | 无 | `{"qrid":"usk_xxx"}` | 取 `qrid`，随后请求 creatImg |
| 2 | `GET /scan/creatImg?qrid=<qrid>` | 取二维码 PNG 图片 | `qrid` | 二进制 PNG 图片 | base64 编码后返回 `{"qrid","qrcode_img"}` |
| 3 | `POST /scan/getInfoNew` | 轮询扫码结果 | `qrid`、`state=1`、`source=pc_web`、`page_source=web_screen`、`request_type=login`（form） | `{"status": 0\|1\|2\|3}` | 按轮询语义映射（见下表） |
| 4 | `GET https://www.10jqka.com.cn/` | 跟随跳转捕获登录态 cookie | 无 | 200 + `Set-Cookie` | 收集 cookies → Vault 持久化 |
| 5 | 自选 / 持仓查询 | 需登录 cookie | 见 `IB_THS_WATCHLIST_URL` / `IB_THS_POSITIONS_URL` | `{"data":[...]}`（包裹层级待实测） | `parse_watchlist` / `parse_positions` |

### 轮询语义（getInfoNew 的 `status`）

| status | 语义 | 本地处理 |
| --- | --- | --- |
| `0` | 二维码过期 | `{"ok": false, "reason": "expired"}`（前端自动刷新二维码） |
| `1` | 等待扫码 | `{"ok": false, "reason": "waiting"}` |
| `2` | 已扫码，待手机确认 | `{"ok": false, "reason": "confirmed"}`（前端提示「请在手机上确认登录」） |
| `3` | 扫码确认成功 | 跟随跳转捕获 cookie → `{"ok": true}` |
| 异常 / 非 JSON | 接口不可用 | `{"ok": false, "reason": "waiting"}`（优雅降级，不抛 500） |

### 字段映射

| 接口字段 | 本地字段 | 说明 |
| --- | --- | --- |
| `qrid` | `LoginQrcode.qrid` | 扫码二维码 ID（后续轮询入参） |
| 二维码 PNG | `LoginQrcode.qrcode_img` | base64，前端 `<img src="data:image/png;base64,...">` 展示 |
| `status` | `LoginPoll.reason` | 0/1/2/3 → expired/waiting/confirmed/成功（见轮询语义表） |
| cookie 会话 | Vault `session.enc` | 登录态以 cookie 存储，**替代原 Bearer token** |
| `amount` | `Position.quantity` | 持股数量（股） |
| `cost` | `Position.cost_price` | 成本价 |
| `enable_amount` | `Position.available` | 可用数量（缺省 0） |
| `market` | `Stock.market` | 市场，缺省 `"SH"` |

### 校验状态

- 各 endpoint 路径与字段来自对同花顺网页版（`upass.10jqka.com.cn`）扫码登录流程的逆向分析。
- **需通过浏览器开发者工具抓包核实，若有出入以实测为准。** 建议在接入前用真实扫码流程
  校验字段名与嵌套层级（尤其 `getInfoNew` 的 `status` 语义与查询接口返回包裹层级）。

## 抓包方法

### 方法 A：浏览器开发者工具（推荐，无需额外工具）

1. 用 Chrome / Edge 打开同花顺网页版登录页。
2. `F12` → `Network`（网络）面板，勾选 `Preserve log`（保留日志）。
3. 执行扫码登录，观察以下请求：`/scan/creatCode`、`/scan/creatImg`、`/scan/getInfoNew`，
   登录成功后的 `www.10jqka.com.cn` 跳转（`Set-Cookie`）以及自选/持仓查询请求。
4. 逐个点击请求，查看 `Request URL`、`Request Headers`（cookie 会话，无 `Authorization`）与
   `Response`（Preview / Response）中的字段嵌套。
5. 与上表比对，记录差异。

### 方法 B：代理抓包（Charles / mitmproxy / Fiddler）

1. 配置系统代理（如 mitmproxy：`mitmweb --listen-port 8080`）。
2. 浏览器 / 移动端安装并信任根证书。
3. 复现登录与查询流程，过滤 `upass.10jqka.com.cn`（登录）/ `search.10jqka.com.cn`（查询）域名。

### 核实要点

- 响应是否包裹在 `{"data": ...}` 中、`data` 是对象还是数组。
- `getInfoNew` 的 `status` 是否仍是 0/1/2/3 语义（见轮询语义表）。
- 登录态是 cookie 还是 token；cookie 的字段名与域名。
- 二维码返回的是二进制 PNG 图片还是 base64 文本。

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
| `/scan/creatCode` 或 `/scan/getInfoNew` 返回 404 / 字段变化 | 登录接口改版 | 重新抓包，更新契约与解析器 |
| 扫码成功但 `status != 3` | 轮询语义变化 | 核实 `status` 含义，必要时加日志 |
| 请求被风控 / 429 | 访问过于频繁 | 确认限频（≥10s + 抖动）未被改动 |
| 会话保活频繁失败 | token 过期 / 接口变更 | 重新扫码登录；若持续失败按上文抓包核实 |
