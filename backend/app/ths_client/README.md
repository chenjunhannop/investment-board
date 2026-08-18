# THS 只读客户端（同花顺扫码登录）

> **合规声明**：本模块为**只读**客户端，仅实现扫码登录与会话保活、自选列表与持仓查询。
> 严禁添加任何下单/撤单/委托/交易方法。相关约束见 `web_client.py` 顶部注释与计划全局约束。

## Endpoint 前缀

默认前缀：`https://upass.10jqka.com.cn`（可通过环境变量 `IB_THS_ENDPOINT` 覆盖，见 `app/config.py`）。

登录态以 **cookie 会话** 传递（不再使用 `Authorization: Bearer <token>`）。登录成功时捕获
`Set-Cookie`，经 `Vault`（AES-256-GCM + Keychain）加密持久化；查询前由 `_apply_session()` 恢复 cookie。

## 接口契约

### GET `/scan/creatCode` — 获取登录二维码 qrid

**请求**：无参数（GET）。

**响应**：

```json
{ "qrid": "usk_xxx" }
```

**处理**：`login_qrcode()` 取 `qrid`，随后请求 `/scan/creatImg` 取二维码图片。

### GET `/scan/creatImg?qrid=<qrid>` — 取二维码 PNG 图片

**请求**：`qrid`（来自 creatCode）。

**响应**：二进制 PNG 图片。

**处理**：base64 编码后对外返回 `{"qrid": "<qrid>", "qrcode_img": "<base64 png>"}`，
供前端 `<img src="data:image/png;base64,...">` 展示。

### POST `/scan/getInfoNew` — 轮询扫码结果

**请求**（form）：

```text
qrid=<qrid>&state=1&source=pc_web&page_source=web_screen&request_type=login
```

**响应**：

```json
{ "status": 0 }
```

**处理**：`poll_login(qrid)` 按 `status` 映射：

| status | 语义 | 返回 |
| --- | --- | --- |
| `0` | 二维码过期 | `{"ok": false, "reason": "expired"}` |
| `1` | 等待扫码 | `{"ok": false, "reason": "waiting"}` |
| `2` | 已扫码，待手机确认 | `{"ok": false, "reason": "confirmed"}` |
| `3` | 扫码确认成功 | 跟随跳转 `https://www.10jqka.com.cn/` 捕获 cookie → `{"ok": true}` |

异常 / 非 JSON 一律优雅降级返回 `{"ok": false, "reason": "waiting"}`，不抛 500。

### 自选 / 持仓查询

**请求**：需登录 cookie。查询 URL 由环境变量 `IB_THS_WATCHLIST_URL` / `IB_THS_POSITIONS_URL`
指定（默认空串，未配置时查询返回空列表并记 WARNING 日志）。

**响应**（默认假定包裹）：

```json
{ "data": [ { "code": "600519", "name": "贵州茅台", "market": "SH" } ] }
```

**处理**：`query_watchlist()` 经 `parse_watchlist()` 转为 `list[Stock]`（`market` 缺省 `"SH"`）；
`query_positions()` 经 `parse_positions()` 转为 `list[Position]`。
映射：`amount → quantity`（股数）、`cost → cost_price`、`enable_amount → available`（缺省 0）。
`_json_text()` 保留 `{"data": ...}` 包裹兼容；若实测新接口不包裹，需在真实扫码抓包确认后调整
（见计划 As-Built）。

## 字段来源说明

- 以上 endpoint 路径与字段（`creatCode`、`creatImg`、`getInfoNew`、`status` 0/1/2/3）来自对
  同花顺网页版（`upass.10jqka.com.cn`）扫码登录流程的逆向分析。
- **需通过浏览器开发者工具抓包核实，若有出入以实测为准。**（建议在接入前用真实扫码流程校验各字段名与嵌套层级）

## 测试

```bash
cd backend && .venv/bin/pytest tests/test_ths_client.py -q
```

测试使用 `respx` 模拟 HTTP，不依赖真实账号与网络；解析器为纯函数，用 fixture 文本驱动。
