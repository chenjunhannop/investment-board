# 去同花顺化 + 本地自选列表设计文档

- 日期：2026-08-18
- 状态：设计已获用户认可
- 决策：彻底移除同花顺集成（登录/自选/持仓查询），项目回归纯公开数据源；自选改为本地自选列表

## 1. 背景与决策

### 1.1 决策链

1. 同花顺 `eq.10jqka.com.cn` 接口整套失效（2026-08），登录链路曾迁移到 `upass.10jqka.com.cn` 扫码并**已修复打通**（真实扫码验证成功）
2. 但同花顺网页版大规模改版（问财化 + 独立 SSO），**自选/持仓查询接口无法确认**（多路径实测受阻：search/x/user/m/i 站均无可用接口，问财收藏需独立 iwencai SSO）
3. 用户决定：**不依赖同花顺**——项目回归纯公开数据源（行情=新浪/腾讯、新闻=东财/财联社），自选改为本地自选列表

### 1.2 设计要点

- **自选**：本地自选列表（`~/.investment-board/watchlist.json`，用户在看板添加/删除股票代码，公开行情接口显示）
- **持仓**：移除（券商持仓数据敏感且网页版难拿，不依赖任何逆向）
- **同花顺登录**：移除（已修复的扫码登录代码保留在 git 历史，不作为功能暴露）
- **项目回归纯公开数据源**：更合规、更稳定、零脆弱逆向接口

## 2. 目标

移除全部同花顺依赖（登录/自选/持仓/会话存储），新增本地自选列表（增删改查 + 行情联动），项目纯公开数据源运行。

## 3. 非目标（明确不做）

- 不保留同花顺登录入口（即使已打通，无数据可查）
- 不保留持仓功能（数据源不存在）
- 不引入任何新的第三方逆向接口
- 不改行情（新浪/腾讯）与新闻（东财/财联社）链路
- 不改项目目录结构（只删减文件与改动现有文件）
- 只读红线不变；`make check` 合规更严格（移除逆向后更干净）

## 4. 后端改动

### 4.1 移除（删除/停用）

| 位置 | 处理 |
|---|---|
| `backend/app/ths_client/`（整个模块：base/parsers/web_client/README/__init__） | 删除 |
| `backend/app/vault/`（整个模块：store/__init__） | 删除（会话加密存储不再需要） |
| `backend/app/api/routes.py` | 移除 `/api/login/*`、`/api/logout`、`/api/status` 中 ths 部分 |
| `backend/app/config.py` | 移除 ths_endpoint_prefix/ths_watchlist_url/ths_positions_url 及环境变量 |
| `backend/app/core/scheduler.py` | 移除持仓循环（positions fetcher）与 ths 依赖 |
| `backend/app/core/portfolio.py` | 删除（持仓计算） |
| `backend/app/core/events.py` | 移除 positions 事件类型（若存在） |
| `backend/app/main.py` | 移除 ths 注入、positions_fetcher、登录相关 |
| `backend/tests/test_ths_client.py`、`test_vault.py` | 删除 |
| `frontend/src/pages/Positions.tsx`、`components/PositionsSummary.tsx` | 删除 |
| `frontend/src/store.tsx` | 移除 positions 状态/数据 |
| `frontend/src/pages/Settings.tsx` | 移除同花顺登录区 |
| `frontend/src/types.ts` | 移除 Position/Status 中 ths/positions 相关 |
| `frontend/src/App.tsx` | 移除持仓导航 tab |

### 4.2 新增：本地自选存储 + API

- **存储**：`~/.investment-board/watchlist.json`，格式 `[{"code": "600519", "name": "贵州茅台"}]`（name 可空，显示时由行情数据补齐）。读/写用 `Path.read_text/write_text`，文件不存在返回空列表；损坏时备份并重建
- **API**（`backend/app/api/routes.py` 新增）：

| 接口 | 方法 | 请求 | 响应 |
|---|---|---|---|
| `/api/watchlist` | GET | — | `[{code, name}]` |
| `/api/watchlist` | POST | `{code}` | 添加后的完整列表（校验 6 位数字代码） |
| `/api/watchlist/{code}` | DELETE | — | `{ok: true}` |

- **代码校验**：6 位数字（`^\d{6}$`），校验失败返回 400
- **名称补齐**：添加时尝试用公开行情接口查名称；失败时 name 存空串（显示层用行情补）
- **存储实现**：新增 `backend/app/core/watchlist.py`（独立小模块：`load_watchlist() -> list[dict]`、`add_watchlist(code) -> list[dict]`、`remove_watchlist(code) -> list[dict]`，含并发锁/原子写）

### 4.3 行情服务改本地自选

`backend/app/core/scheduler.py` 的 `_collect_codes()`：从 `load_watchlist()` 读代码（替代原 ths.query_watchlist）；无自选时行情循环返回空（与现逻辑一致，仅数据源变本地）。

## 5. 前端改动

| 位置 | 改动 |
|---|---|
| `frontend/src/api/client.ts` | 新增 `getWatchlist/addWatchlist/removeWatchlist`；移除 `startLogin/pollLogin/logout/getPositions` |
| `frontend/src/pages/Dashboard.tsx` | 状态条去掉"源: 新浪·腾讯"（行情源即新浪/腾讯），保留连接状态/时间 |
| `frontend/src/pages/Settings.tsx` | 移除登录区，保留"数据源健康"（行情/新闻源） |
| **新增 `frontend/src/pages/Watchlist.tsx`** | 本地自选列表管理页：输入框 + 添加按钮 + 每项删除 + 实时行情展示（复用现有行情 grid） |
| `frontend/src/App.tsx` | 导航改为：看板 / 自选 / 新闻 / 设置（持仓移除） |
| `frontend/src/store.tsx` | 移除 positions 相关；新增 watchlist 状态/操作（load/add/remove） |
| `frontend/src/types.ts` | 移除 Position 等 |

> 导航分工（明确）：**Dashboard（看板）** 保留现有行情总览（数据源=本地自选列表，与 Watchlist 页同一份数据）；**Watchlist（自选）** 承载自选管理（增删股票）+ 实时行情展示。两页共享 store 中的 watchlist 状态，展示同一份自选行情。

## 6. 约束与合规

- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`make check` 必须 OK
- **删除性改动**：删除 ths/vault/positions 相关测试后，剩余既有测试必须全绿 + 新增 watchlist 测试
- **工具链**：ruff/yapf/mypy/eslint/prettier 全绿；`make build` 成功
- **API 契约收敛**：`/api/quotes`、`/api/news`、`/api/status` 保留（status 中去掉 ths 字段）
- **数据目录**：watchlist.json 与既有 `~/.investment-board/` 一致，不新增目录
- **命令**：一律 `backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- 新代码 Google docstring；commit 用 `refactor:`（移除）与 `feat:`（本地自选）类型

## 7. 验收标准

1. `make check` OK（合规，无逆向依赖）｜`make lint` 零错｜`make typecheck` 通过｜`make test` 既有测试全绿 + 新增 watchlist 测试｜`make build` 成功
2. 设置页无同花顺登录区；导航无持仓；无 `/api/login/*` 路由
3. 自选页可添加/删除股票（输入代码 → 添加 → 行情实时显示 → 删除），watchlist.json 正确持久化
4. 行情（新浪/腾讯）与新闻（东财/财联社）不受影响
5. 手动冒烟：启动后端+前端，自选增删 + 行情联动正常

## 8. 参考

- 上一版 spec：`docs/superpowers/specs/2026-08-18-ths-login-fix-design.md`（登录修复已达成，本 spec 取代其后续部分）
- 现状：行情服务（新浪/腾讯）、新闻服务（东财/财联社）均可用；同花顺依赖集中在 ths_client/vault/positions
