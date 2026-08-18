# THS 只读客户端（同花顺扫码登录）

> **合规声明**：本模块为**只读**客户端，仅实现扫码登录与会话保活、自选列表与持仓查询。
> 严禁添加任何下单/撤单/委托/交易方法。相关约束见 `web_client.py` 顶部注释与计划全局约束。

## Endpoint 前缀

默认前缀：`https://eq.10jqka.com.cn`（可通过环境变量 `IB_THS_ENDPOINT` 覆盖，见 `app/config.py`）。

以下所有请求均由 `ThsWebClient` 发起，返回 JSON；`Authorization: Bearer <token>` 在会话有效时自动附带。

## 接口契约

### GET `/qrcode` — 获取登录二维码

**请求**：无参数（GET）。

**响应**：

```json
{ "data": { "qrcode": "<base64 二维码数据>" } }
```

**处理**：`login_qrcode()` 缓存 `data`，对外返回 `{"qrcode_data": "<qrcode>"}`。

### GET `/poll` — 轮询扫码结果

**请求**：无参数（GET）。

**响应**：

```json
{ "data": { "status": 1, "token": "<会话令牌>", "user": "<用户名>" } }
```

**处理**：`status == 1` 视为扫码成功，将 `token`/`user` 通过 `Vault`（AES-256-GCM + Keychain）加密持久化；否则返回 `False` 继续轮询。

### GET `/watchlist` — 自选列表

**请求**：无参数（GET，需登录态）。

**响应**（`data` 为数组）：

```json
{ "data": [ { "code": "600519", "name": "贵州茅台", "market": "SH" } ] }
```

**处理**：`query_watchlist()` 经 `parse_watchlist()` 转为 `list[Stock]`。字段 `market` 缺省为 `"SH"`。

### GET `/positions` — 持仓列表

**请求**：无参数（GET，需登录态）。

**响应**（`data` 为数组）：

```json
{
  "data": [
    { "code": "600519", "name": "贵州茅台", "amount": 100, "cost": 1600.0, "enable_amount": 100 }
  ]
}
```

**处理**：`query_positions()` 经 `parse_positions()` 转为 `list[Position]`。
映射：`amount → quantity`（股数）、`cost → cost_price`、`enable_amount → available`（可用数量，缺省 0）。

### GET `/session/check` — 会话保活

**请求**：无参数（GET，需登录态）。

**响应**：成功返回 `{"data": {...}}`（200）；失败抛错。

**处理**：`refresh_session()` 捕获异常并返回 `bool`（成功 `True` / 失败 `False`）。

## 字段来源说明

- 以上 endpoint 路径与字段（`qrcode`、`status`、`token`、`user`、`amount`、`cost`、`enable_amount`）
  来自对同花顺网页版登录/自选/持仓接口的逆向分析。
- **需通过浏览器开发者工具抓包核实，若有出入以实测为准。**（建议在接入前用真实扫码流程校验各字段名与嵌套层级）

## 测试

```bash
cd backend && .venv/bin/pytest tests/test_ths_client.py -q
```

测试使用 `respx` 模拟 HTTP，不依赖真实账号与网络；解析器为纯函数，用 fixture 文本驱动。
