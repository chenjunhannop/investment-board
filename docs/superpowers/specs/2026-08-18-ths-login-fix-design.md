# 同花顺登录链路修复设计文档（扫码登录）

- 日期：2026-08-18
- 状态：设计已获用户认可（Part 1-4 分节确认）
- 背景：原登录链路依赖 `eq.10jqka.com.cn` 逆向接口，2026-08 已整套失效（qrcode/watchlist/positions/session/check 全部 404/403）

## 1. 背景与调研结论

### 1.1 失效事实（2026-08 实测）

| 接口 | 状态 |
|---|---|
| `eq.10jqka.com.cn/qrcode`（原扫码登录） | 404/403 ❌ |
| `eq.10jqka.com.cn/poll`（原轮询） | 404 ❌ |
| `eq.10jqka.com.cn/watchlist`（原自选） | 404 ❌ |
| `eq.10jqka.com.cn/positions`（原持仓） | 404 ❌ |
| `eq.10jqka.com.cn/session/check`（原保活） | 404 ❌ |

### 1.2 调研结论（GitHub 开源项目）

- **easytrader**（10K⭐）：同花顺桌面客户端 UI 模拟（pywinauto，Windows-only）→ 不适用于 Web 看板，已否决
- **atomat/10jqka-API**（92⭐）：同花顺 APP 私有 TCP 协议逆向（设备指纹+加密），**交易向**（打新）→ 与只读定位冲突，已否决
- **wangh00/10jqka_login**（24⭐）：网页版账号密码+滑块逆向（RSA+设备指纹+v cookie+滑块破解）→ 极复杂、风控频繁，用户已否决
- **结论**：无开源项目走"Web 只读看板"路径；最合理方案是**逆向同花顺网页版扫码登录**（程序全自动，用户仅手机扫码确认）

### 1.3 新扫码接口已逆向并实测可用（upass.10jqka.com.cn）

逆向自登录页 `qrcode.js`（`upass.10jqka.com.cn/asset/login/js/web/qrcode.js`），3 个接口全部 curl 实测通过：

| 接口 | 方法 | 参数 | 响应（实测） |
|---|---|---|---|
| `GET /scan/creatCode` | GET | 无 | `{"qrid":"usk_...","errorCode":0}` ✅ |
| `GET /scan/creatImg?qrid=` | GET | qrid | 252×252 PNG 二维码图 ✅ |
| `POST /scan/getInfoNew` | POST | `qrid,state,source=pc_web,page_source=web_screen,request_type=login` | `{"status":1,...}` ✅（1等待/2已扫/3成功/0失效） |

轮询语义（来自 qrcode.js 逆向）：`status=0` 二维码失效需重新获取；`1` 等待扫码（1s 后继续）；`2` 已扫码待手机确认（1s 后继续，state 改为 2）；`3` 验证成功→跳转 `redir`（默认 `www.10jqka.com.cn`），跳转过程设置登录态 cookie。

## 2. 目标

修复同花顺登录链路：用户可在设置页扫码登录，程序获取登录态后查询**自选与持仓**，端到端可用。

## 3. 非目标（明确不做）

- 不做桌面客户端/APP 协议模拟（平台不匹配、交易向、改动过大）
- 不做账号密码+滑块自动登录（复杂、风控、合规风险）
- 不引入手动 Cookie 粘贴（用户明确否决，要求全自动）
- 不改后端对外 API 契约（`/api/login/qrcode`、`/api/login/poll`、`/api/logout`、`/api/status` 等保持）
- 不触碰行情（新浪/腾讯）与新闻（东财公告）链路
- 不涉及任何交易功能；只读红线不变

## 4. 登录链路设计（后端 ThsWebClient 重写）

### 4.1 流程

```
前端设置页[扫码登录]
  → POST /api/login/qrcode
  → 后端 GET /scan/creatCode 拿 qrid
  → 后端 GET /scan/creatImg?qrid 拿 PNG → 返回 {qrid, qrcode_img: <base64>}
  → 前端 <img> 展示二维码（手机同花顺 App 扫码）
  → POST /api/login/poll（2s 轮询，带 qrid）
  → 后端 POST /scan/getInfoNew 轮询：
       status=0 → 二维码失效，前端重新触发 /login/qrcode
       status=1 → 等待扫码（继续轮询）
       status=2 → 已扫码，请在手机确认（继续轮询，state=2）
       status=3 → 登录成功：跟随跳转 redir → 捕获登录态 cookie → Vault 加密保存 → 返回 ok
  → 前端刷新显示已登录
```

### 4.2 后端方法变更（`backend/app/ths_client/web_client.py`）

| 方法 | 原实现 | 新实现 |
|---|---|---|
| `login_qrcode()` | GET `eq.../qrcode`，返回文本 qrcode | GET `upass.10jqka.com.cn/scan/creatCode` 拿 qrid + `/scan/creatImg` 拿 PNG，返回 `{qrid, qrcode_img(base64)}` |
| `poll_login(qrid)` | GET `eq.../poll`，status==1 拿 token | POST `/scan/getInfoNew` 轮询 status；`status==3` 时跟随跳转捕获 cookie 存入 Vault |
| `query_watchlist()` | GET `eq.../watchlist` | 新自选接口（见 §5，配置化） |
| `query_positions()` | GET `eq.../positions` | 新持仓接口（见 §5，配置化） |
| `refresh_session()` | GET `eq.../session/check` | 适配新会话校验（见 §5） |

- `ThsAdapter` 抽象接口签名同步更新（`poll_login(qrid)` 增参、`login_qrcode` 返回结构变化）
- 会话存储：复用 Vault（cookie 以加密文本存 `~/.investment-board/session.enc`）
- 优雅降级保留：任何接口异常 → 返回明确 error 而非 500（沿用 2026-08-18 的降级模式）

### 4.3 前端变更（`frontend/src/pages/Settings.tsx` + `client.ts`）

- `startLogin()` 返回类型改为 `{ qrid: string; qrcode_img: string; error?: string }`
- 轮询驱动：**前端 2s 间隔驱动**，每次 `POST /api/login/poll` 携带 `{qrid}`，后端查一次 `getInfoNew` 并返回 `{ ok: boolean; reason?: 'expired' | 'waiting' | 'confirmed' }`（契约明确）：`ok=true` 登录成功；`reason='expired'` 二维码失效→前端自动重新 `startLogin()`；`reason='waiting'` 继续轮询；`reason='confirmed'` 已扫码请在手机确认
- 二维码渲染：MVP 的 `<pre>` 文本改为 `<img src="data:image/png;base64,...">` 展示
- 状态流转文案：等待扫码 → 已扫码请在手机确认 → 登录成功
- 错误提示保留（接口不可用时）

## 5. 查询接口（自选/持仓）——需真实登录抓包确认

### 5.1 已知线索

- 自选：`x.10jqka.com.cn/service/getSelfStock` 301 → `search.10jqka.com.cn/service/getSelfStock`（无登录态 404）
- 持仓：同花顺网页版持仓**需账号绑定券商账户**，数据源待确认

### 5.2 确认方式（实施计划内含真实扫码验证步骤）

1. 用户用手机同花顺 App 扫码完成一次登录
2. 用 browser-use / 代理抓包捕获登录后自选页/持仓页的真实请求（路径/参数/响应结构）
3. 据此实现 `query_watchlist`/`query_positions` 与响应解析
4. 接口路径配置化：`IB_THS_WATCHLIST_URL`、`IB_THS_POSITIONS_URL` 环境变量可覆盖默认值

### 5.3 持仓不可用时的降级

- 若持仓数据源确认不可用（网页版无券商持仓），则持仓页显示明确空态提示（"持仓需同花顺账号绑定券商后显示"），自选与行情/新闻不受影响——此降级在 spec 中作为已知边界，若用户需要持仓数据，另行评估（如绑定券商后的接口逆向）

## 6. 约束与合规

- **只读红线**：仅登录/查自选/查持仓，严禁任何交易语义；`scripts/check_no_trade.py` 必须始终 OK（新增代码不得含 buy/sell/trade/order 前缀标识符或中文交易业务词）
- **API 契约**：后端对外 `/api/login/*`、`/api/status`、`/api/quotes`、`/api/positions`、`/api/news` 保持兼容（`/api/positions` 仍返回 `Position[]`）
- **测试**：`backend/tests/test_ths_client.py` 的 respx mock 从旧接口契约更新为新契约；`test_api.py` 相关用例同步；**29 个测试全绿**保持
- **工具链**：ruff/yapf/mypy 全绿；前端 eslint/prettier/build 全绿
- **会话加密**：cookie 经 AES-256-GCM 存本机，测试用 `IB_TEST_KEYCHAIN` 注入不变
- **只改**：`backend/app/ths_client/*`、`backend/app/api/routes.py`（如需）、`backend/app/models.py`（如需）、`backend/tests/*`、`frontend/src/pages/Settings.tsx`、`frontend/src/api/client.ts`、`README.md`、`docs/ths-reverse-engineering.md`

## 7. 验收标准

1. `make check` OK（合规）｜`make lint` 零错｜`make typecheck` 通过｜`make test` 29 passed｜`make build` 成功
2. **真实扫码端到端**（用户配合扫码一次）：设置页扫码 → 手机确认 → 登录成功 → 自选列表展示 → 持仓展示（或按 §5.3 降级提示）
3. 二维码以图片正常显示、过期自动刷新、状态流转文案正确
4. 登出（`/api/logout`）清除本地 cookie 后恢复未登录态
5. README FAQ 与 `docs/ths-reverse-engineering.md` 契约表更新为新接口

## 8. 参考

- 逆向证据：`upass.10jqka.com.cn/asset/login/js/web/qrcode.js`（扫码接口契约）
- 调研：GitHub easytrader / atomat-10jqka-API / wangh00-10jqka_login（均否决）
- 现有代码：`backend/app/ths_client/web_client.py`（登录链路重写基线）
