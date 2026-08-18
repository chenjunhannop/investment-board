# 代码规范落地实施计划（阿里 f2e-spec + Google Python Style）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 investment-board 引入双轨权威代码规范（前端阿里 f2e-spec、后端 Google Python Style Guide），深度整理现有代码使其完全符合规范，且测试全绿、功能与 API 契约不变。

**Architecture:** 规范双轨——前端用阿里官方 npm 工具链（eslint-config-ali / prettier-config-ali / commitlint-config-ali）强制；后端用 Google 官方配套（yapf 格式化 + ruff lint + mypy 类型检查）强制。规范文档入库 `docs/coding-standards/`。Git 提交、CI、Makefile 全项目统一扩展。

**Tech Stack:** ESLint 9 (flat config) / prettier / commitlint（前端）；yapf / ruff / mypy / pytest（后端）；TypeScript 5.4 / React 18 / Vite 5（现有）。

## Global Constraints

以下约束来自 spec `docs/superpowers/specs/2026-08-18-coding-standards-design.md`，每个任务都隐含适用：

- **前端缩进 2 空格**（阿里通用规约强制）；**Python 缩进 4 空格**（Google/PEP8）；全文件 UTF-8 + LF + 末尾换行（`.editorconfig` 强制）。
- **行宽统一 100**：yapf `column_limit=100`、ruff `line-length=100`、prettier `printWidth=100`、`.editorconfig` `max_line_length=100`。
- **后端唯一 formatter 是 yapf**（`based_on_style="google"`），**禁止使用 ruff format**，避免与 yapf 冲突。
- **ruff lint 规则集**：E/W/F/I/UP/B/D/N/ASYNC；`pydocstyle.convention = "google"`（D 规则按 Google docstring 风格检查）。
- **后端环境命令一律用 `backend/.venv/bin/`**（Python 3.11；venv 已存在，勿用系统 python 3.9）。
- **前端 `eslint-config-ali@^16` 要求 `eslint@^9`**（flat config 语法，`eslint.config.mjs`）。
- **commitlint 只做 CI 校验**（`--from origin/main..HEAD`），**不引入本地 git hook**。
- **不改写已推送的 git 历史**（现有提交已符合 `feat:` 约定式格式）。
- **不拆组件、不改目录结构、不重写测试、不改变 API 契约**——只做符合规范的整理。
- **测试硬性全绿**：最终 `make check && make lint && make typecheck && make test && make build` 全过。
- **合规扫描** `make check`（`scripts/check_no_trade.py`，AST 版）必须始终通过——**重命名/加注释不得引入 buy/sell/trade/order 前缀标识符或委托/下单/撤单/成交/买入/卖出中文词**（注释与 docstring 中除外）。

---

### Task 1: 规范文档 + .editorconfig

**Files:**
- Create: `docs/coding-standards/README.md`
- Create: `docs/coding-standards/backend.md`
- Create: `docs/coding-standards/frontend.md`
- Create: `docs/coding-standards/git-commit.md`
- Create: `.editorconfig`（项目根）

**Interfaces:**
- Consumes: spec `docs/superpowers/specs/2026-08-18-coding-standards-design.md`（第 2 节规范体系）
- Produces: `docs/coding-standards/` 四份文档 + 根 `.editorconfig`（后续所有任务的代码环境基础）

- [ ] **Step 1: 创建 `.editorconfig`**

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
trim_trailing_whitespace = true
insert_final_newline = true

[*.{js,ts,tsx,jsx,json,css,html}]
indent_style = space
indent_size = 2

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100
```

- [ ] **Step 2: 创建 `docs/coding-standards/README.md`**

内容要点（用中文写）：
1. 规范总览表：前端编码/工程 → 阿里巴巴 `alibaba/f2e-spec`（含官方仓库 URL）；后端 → Google Python Style Guide（含官方 URL）；Git 提交 → 约定式提交。
2. 工具链矩阵：前端（eslint-config-ali/prettier-config-ali/commitlint-config-ali）、后端（yapf/ruff/mypy）、全项目（.editorconfig）。
3. "如何让规范持续生效"：CI 里 lint/format/typecheck 失败即拦截；IDE 配置指引（安装对应插件、.editorconfig 自动生效）。
4. 指向 `backend.md` / `frontend.md` / `git-commit.md` 的链接。

- [ ] **Step 3: 创建 `docs/coding-standards/backend.md`**

内容要点：Google Python Style Guide 映射到本项目的规则清单：
1. **命名**：`module_name` / `package_name` / `ClassName` / `method_name` / `CONSTANT_NAME` / `_internal_name`（ruff N 规则检查）。
2. **类型注解**：公开 API 全注解，参数/返回类型必填；容器用泛型 `list[str]`/`dict[str, X]`，禁止裸 `list`/`dict`（mypy 检查）。
3. **docstring**：模块、public 类/方法用 Google 风格——`"""一行摘要。` + 空行 + `Args:` + `Returns:` + `Raises:` 段（ruff D + google convention 检查）。给出模板：

```
def fetch_quotes(self, codes: list[str]) -> dict[str, Quote]:
    """按代码列表抓取实时行情。

    Args:
        codes: 6 位股票代码列表，如 ["600519", "000001"]。

    Returns:
        以代码为 key 的 Quote 字典；空列表返回空字典。
    """
```

4. **main() 入口**：`backend/app/main.py` 必须有 `def main() -> None` + `if __name__ == "__main__":`。
5. **异常**：捕获用具体异常类型，禁止裸 `except:`；抛出用 `raise XxxError(...)` 带信息。
6. **import**：分组 stdlib / 第三方 / 本地，每组内按字母序（ruff I 规则自动排）。
7. **字符串**：统一 f-string（Python 3.11）。
8. **工具配置说明**：`[tool.yapf]` / `[tool.ruff]` / `[tool.mypy]` 的实际值（与 Task 2 保持一致）。

- [ ] **Step 4: 创建 `docs/coding-standards/frontend.md`**

内容要点（f2e-spec 摘录映射）：
1. **React hooks**：依赖数组补全（`exhaustive-deps`）、禁止循环/条件内调用 hooks、自定义 hooks 以 `use` 开头。
2. **命名**：组件 PascalCase、文件名与组件名一致、props 回调以 `on` 前缀、布尔 props 以 `is`/`has` 前缀。
3. **类型**：禁 `any`、props 用 `interface`、纯类型导入用 `import type`。
4. **导入**：分组排序（外部包在前，内部相对导入在后）、`import type` 分离。
5. **Prettier 选项**：printWidth 100 / tabWidth 2 / singleQuote / semi / trailingComma all（来自 `prettier-config-ali`）。
6. **JSX**：自闭合标签、`key` 唯一。

- [ ] **Step 5: 创建 `docs/coding-standards/git-commit.md`**

内容要点（阿里 f2e-spec git.md 映射）：
1. 格式 `<type>[scope]: <description>`。
2. type 枚举：feat/fix/docs/style/test/refactor/chore/revert（每个给一句中文释义）。
3. description 用中文或英文（项目现有提交用中文，保持一致），动词开头、不超 50 字符。
4. 示例若干（含本项目真实提交：`feat: 行情服务（新浪/腾讯，去重合并，源切换）`）。
5. 说明：CI 用 commitlint 校验（`commitlint-config-ali`）。

- [ ] **Step 6: 验证与提交**

```bash
# 验证 5 个文件都存在且非空
ls -la .editorconfig docs/coding-standards/
git add .editorconfig docs/coding-standards/
git commit -m "docs: 引入代码规范文档（阿里 f2e-spec + Google Python Style）"
```

---

### Task 2: 后端工具链配置 + 基线 + 自动格式化

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.venv`（安装 yapf、mypy）

**Interfaces:**
- Consumes: `backend/pyproject.toml`（现有 `[tool.ruff] line-length=100, target-version="py311"`）
- Produces: 配置好的 yapf/ruff-lint/mypy（Task 3/4 重构的验证基础）；yapf 全量格式化后的 `backend/app/**`（Task 3/4 在格式化后代码上继续重构）

- [ ] **Step 1: 安装工具到 venv**

```bash
backend/.venv/bin/pip install yapf mypy
```

- [ ] **Step 2: 改写 `backend/pyproject.toml`**

保留现有 `[project]` / `[project.optional-dependencies]`（dev 里补 yapf、mypy）与 `[tool.pytest.ini_options]`，将 `[tool.ruff]` 扩展并新增：

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "D", "N", "ASYNC"]
ignore = ["E501"]  # 行宽由 yapf 保证

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.yapf]
based_on_style = "google"
column_limit = 100

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
warn_return_any = true
warn_unused_ignores = true
no_implicit_optional = true
```

- [ ] **Step 3: 跑 lint 基线并记录**

```bash
backend/.venv/bin/ruff check backend/app
```

Expected: 报 16 个错误（多为 F 类未使用导入等）+ 大量 D10x（缺 docstring，因为 D 规则已启用而现有函数基本无 docstring）。**记录错误清单**（供 Step 5 核对）。

- [ ] **Step 4: 自动修复 + 全量格式化**

```bash
backend/.venv/bin/ruff check backend/app --fix   # 自动修复可修复项（如 import 排序）
backend/.venv/bin/yapf -ri backend/app backend/tests   # 全量 Google 风格格式化
```

- [ ] **Step 5: 修复非 docstring 的 lint 错误**

```bash
backend/.venv/bin/ruff check backend/app
```

Expected: **非 D 规则（E/W/F/I/UP/B/N/ASYNC）零错误**；剩余 D10x 缺 docstring 错误属预期，将分别在 Task 3/4 补齐后清零（D 是最后一次门禁，见 Task 4 Step 4）。剩余手工修复（如未使用的 import 直接删、变量未用加 `_` 前缀）。若某条 ASYNC/N 规则与本项目实际冲突且无法合理解释，可在执行记录中说明并从 `select` 移除该规则，但需保持其他规则不变。注意：**不要**为了消除 lint 而改动测试断言或逻辑。

- [ ] **Step 6: 回归验证**

```bash
backend/.venv/bin/ruff check backend/app backend/tests --statistics   # 确认非 D 规则清零，剩余均为 D10x
backend/.venv/bin/yapf -d backend/app backend/tests   # 应为空 diff
backend/.venv/bin/pytest -q    # 期望 29 passed
```

- [ ] **Step 7: 提交**

```bash
git add backend/pyproject.toml backend/app backend/tests
git commit -m "chore: 后端配置 yapf/ruff-lint/mypy 并全量格式化"
```

---

### Task 3: 后端深度重构 A（models / market / news / vault）

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/market/parsers.py`
- Modify: `backend/app/market/service.py`
- Modify: `backend/app/news/parsers.py`
- Modify: `backend/app/news/service.py`
- Modify: `backend/app/vault/store.py`

**Interfaces:**
- Consumes: Task 2 配置好的 yapf/ruff/mypy；`backend/app/models.py` 现有 dataclass（Stock/Position/Quote/IntradayPoint/NewsItem，**类型与字段名不变**）
- Produces: 上述文件具备 Google 风格 docstring + 完整类型注解 + 规范 import；API 契约不变

> 本任务不新增测试（现有 29 测试即回归保障）。验证 = ruff check + mypy + pytest 全绿。

- [ ] **Step 1: 逐文件补充 Google 风格 docstring**

对以下文件的**每个 public 函数/方法**（模块级 docstring 也要有）按 Google 模板（见 backend.md）补充 `Args:` / `Returns:` / `Raises:`（无参数/无返回可省略对应段）。缺少 docstring 的函数清单（参考现有 AST 扫描，逐个补齐）：

- `models.py`：模块 docstring + 每个 dataclass 类 docstring（一句话用途）+ 字段保持原样。
- `market/parsers.py`：`_today`、`parse_sina`、`parse_tencent`、`parse_sina_intraday`——每个解析器注明"解析 xxx 接口返回文本，失败抛 ValueError"。
- `market/service.py`：`_normalize`（注释 600519→sh600519 逻辑）、`_split_codes`、`__init__`、`fetch_quotes`、`_parse_all`、`fetch_intraday`。
- `news/parsers.py`：`_ts`、`parse_eastmoney`、`parse_cls`。
- `news/service.py`：`__init__`、`fetch_individual`、`fetch_global`、`dedupe`。
- `vault/store.py`：`_keyring_get`、`_keyring_set`、`_get_or_create_key`（注明 IB_TEST_KEYCHAIN 测试分支）、`__init__`、`save_session`、`load_session`、`clear`、`is_logged_in`（注明 AES-256-GCM + v1 头格式）。

- [ ] **Step 2: 类型注解补强（mypy 驱动）**

```bash
backend/.venv/bin/mypy backend/app
```

逐个修复报错：补函数返回类型、参数类型、局部变量注解、`Optional[...]` 显式化。**不改任何运行逻辑**。

- [ ] **Step 3: import 分组与排序检查**

```bash
backend/.venv/bin/ruff check backend/app --select I
```

Expected: 无错误（Task 2 已 --fix，此处复核）。若 yapf 格式化后 import 顺序被重排导致 I 报错，用 `--fix` 修正。

- [ ] **Step 4: 字符串/容器泛型核对**

通读上述文件：所有 `%` 格式化或 `+` 拼接改为 f-string；所有裸 `list`/`dict` 类型标注改为 `list[...]`/`dict[...]`。

- [ ] **Step 5: 验证**

```bash
backend/.venv/bin/ruff check backend/app backend/tests --statistics   # 非 D 规则零错误；D10x 应大幅减少，剩余交给 Task 4
backend/.venv/bin/yapf -d backend/app backend/tests
backend/.venv/bin/mypy backend/app
backend/.venv/bin/pytest -q    # 29 passed
python3 scripts/check_no_trade.py    # 合规 OK（新增注释/ docstring 中不得含交易词，或含时须是"禁止交易"类说明）
```

- [ ] **Step 6: 提交**

```bash
git add backend/app
git commit -m "refactor: 后端模块 A 补齐 Google 风格 docstring 与类型注解"
```

---

### Task 4: 后端深度重构 B（ths_client / core / api / main / config）

**Files:**
- Modify: `backend/app/ths_client/base.py`
- Modify: `backend/app/ths_client/parsers.py`
- Modify: `backend/app/ths_client/web_client.py`
- Modify: `backend/app/core/events.py`
- Modify: `backend/app/core/portfolio.py`
- Modify: `backend/app/core/scheduler.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/api/ws.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: Task 2 工具链；现有 `ThsAdapter`/`EventBus`/`Scheduler`/`compute_positions`/`app.state` 契约（**签名与行为不变**）
- Produces: 上述文件符合 Google 规范；`main.py` 有 `main()` 入口；API/WS 契约不变

- [ ] **Step 1: 逐文件补充 Google 风格 docstring**

- `ths_client/base.py`：模块 docstring（注明"抽象基类，禁止添加交易类方法"）+ 每个抽象方法 docstring + `ThsAdapter` 类 docstring。
- `ths_client/parsers.py`：`parse_watchlist`、`parse_positions`。
- `ths_client/web_client.py`：保留顶部只读合规 docstring；为 `_json_text`、`__init__`、`is_logged_in`、`_get_json`、`login_qrcode`、`poll_login`、`query_watchlist`、`query_positions`、`refresh_session`、`logout` 补齐。
- `core/events.py`：`EventBus` 类 docstring + `__init__`/`subscribe`/`unsubscribe`/`publish`。
- `core/portfolio.py`：`compute_positions`（Args/Returns：说明"绑定行情后计算市值/盈亏/当日涨跌"）。
- `core/scheduler.py`：`Scheduler` 类 docstring（注明注入式 fetcher + 限频） + `__init__`/`_spawn`/`start`/`stop`/`_collect_codes`/`_quotes_loop`/`_positions_loop`/`_apply_quotes`/`_news_loop`。
- `api/routes.py`：8 个路由 handler 各补 docstring（注明 REST 语义 + 503 场景）。
- `api/ws.py`：`ConnectionManager` + `connect`/`disconnect` + `websocket_endpoint`（注明每连接自推送、订阅清理）。
- `config.py`：`Settings` 类 + 字段。
- `main.py`：`lifespan`、`positions_fetcher`、`news_fetcher`。

- [ ] **Step 2: main.py 增加 `main()` 入口（Google 强制）**

在 `backend/app/main.py` 末尾追加（若已存在则检查格式）：

```python
def main() -> None:
    """启动 uvicorn 开发服务器（仅监听本机）。"""
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
```

确认 `settings.host` / `settings.port` 已定义于 `config.py`（如缺失则确认现有字段名并对应使用，不改字段名）。

- [ ] **Step 3: 异常与类型注解修复**

```bash
backend/.venv/bin/mypy backend/app
backend/.venv/bin/ruff check backend/app
```

逐项修复：异常捕获用具体类型（`scheduler.py` 中 `except Exception` 保留并说明原因——网络抖动兜底，docstring 注明）；`routes.py` 的 `HTTPException` 分支保留；ws.py 的连接清理逻辑不动。**`web_client.py` 不得新增任何以 buy/sell/trade/order 为前缀的标识符**（合规扫描）。

- [ ] **Step 4: 验证（D 规则在此清零，作为后端 docstring 最后门禁）**

```bash
backend/.venv/bin/ruff check backend/app backend/tests   # 期望零错误（含 D，Task 3 遗留的 D10x 在此补齐清零）
backend/.venv/bin/yapf -d backend/app backend/tests
backend/.venv/bin/mypy backend/app
backend/.venv/bin/pytest -q    # 29 passed
python3 scripts/check_no_trade.py    # OK
```

- [ ] **Step 5: 冒烟启动**

```bash
cd backend && (./run.sh &) && sleep 4 && curl -s http://127.0.0.1:8210/api/status && kill %1 2>/dev/null
```

Expected: 返回 `{"logged_in":false,...}` 200；启动无 ImportError。若 8210 端口占用则用 `pkill -f "uvicorn app.main"` 清理后重试。

- [ ] **Step 6: 提交**

```bash
git add backend/app
git commit -m "refactor: 后端模块 B 补齐 docstring、main 入口与类型注解"
```

---

### Task 5: 前端工具链配置 + 全量格式化

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/.prettierrc`
- Create: `frontend/.prettierignore`
- Modify: `frontend/src/**`（prettier 全量格式化结果）

**Interfaces:**
- Consumes: `frontend/package.json`（React 18 / TS 5.4 / Vite 5 现有依赖）
- Produces: eslint/prettier 配置 + scripts（Task 6 重构的验证基础）

- [ ] **Step 1: 安装依赖**

```bash
cd frontend && npm install --save-dev eslint@^9 eslint-config-ali@^16 prettier prettier-config-ali @commitlint/cli commitlint-config-ali
```

- [ ] **Step 2: 创建 `eslint.config.mjs`**

```js
import { react } from 'eslint-config-ali';

export default [
  ...react,
  {
    ignores: ['dist', 'node_modules', '*.tsbuildinfo'],
  },
];
```

- [ ] **Step 3: 创建 `.prettierrc` 与 `.prettierignore`**

```json
"prettier-config-ali"
```

```text
dist
node_modules
package-lock.json
```

- [ ] **Step 4: 扩展 `frontend/package.json` scripts**

```json
"lint": "eslint .",
"lint:fix": "eslint . --fix",
"format": "prettier --write .",
"format:check": "prettier --check ."
```

- [ ] **Step 5: 全量格式化 + lint 基线**

```bash
cd frontend && npm run format
npx eslint . 2>&1 | tail -20
```

Expected: 格式统一；eslint 报出风格问题清单（如 import 排序、react-hooks 依赖）。**记录清单**供 Step 6 修复。

- [ ] **Step 6: 修复 eslint 报错**

逐个修复（优先 `npx eslint . --fix` 自动项，剩余手工）。**不改组件功能与页面行为**。

- [ ] **Step 7: 验证与提交**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
cd .. && git add frontend/ && git commit -m "chore: 前端配置 eslint-config-ali/prettier 并全量格式化"
```

Expected: lint 零错误、format:check 无 diff、build 成功（仅 chunk>500kB 提示可忽略）。

---

### Task 6: 前端深度重构（f2e-spec 手工核对）

**Files:**
- Modify: `frontend/src/store.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Positions.tsx`
- Modify: `frontend/src/pages/News.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/components/PriceCard.tsx`
- Modify: `frontend/src/components/Sparkline.tsx`
- Modify: `frontend/src/components/PositionsSummary.tsx`
- Modify: `frontend/src/components/NewsCard.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`、`frontend/src/api/ws.ts`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Consumes: Task 5 eslint/prettier 配置；现有 `useApp()` store、`connectWS`、`client.ts` API 函数（**签名与行为不变**）
- Produces: 完全符合 f2e-spec 的前端代码；页面/交互不变

> 不新增测试（前端无测试套件；验证 = eslint + tsc + build 全绿 + 手动页面冒烟）。

- [ ] **Step 1: hooks 规范核对（exhaustive-deps）**

逐文件检查 `useEffect`/`useMemo`/`useCallback` 依赖数组（Settings.tsx 的轮询定时器、Dashboard/News 等挂载逻辑）：依赖补全、清理函数用 `clearInterval`、`init()` 幂等。**若 eslint 已强制修复则确认无警告**。

- [ ] **Step 2: 命名与 props 规范**

- 组件文件导出名与文件名一致（`PriceCard.tsx` 导出 `PriceCard` 等）。
- props 用 `interface` 显式定义，回调 props 以 `on` 前缀（如 `onRead`）。
- 内部私有组件/辅助函数以小写 `_` 前缀或抽离到文件底部。
- 消除 `any`：`ws.ts` 的 `onEvent` 回调参数用 `WsEvent` 联合类型精确化（`ev.data` 按 type 收窄为 `Quote`/`Position[]`/`NewsItem[]`）。

- [ ] **Step 3: 导入规范**

- 外部包（react/zustand/echarts）在前，内部相对导入在后，组内字母序（eslint import 规则核对）。
- 纯类型导入用 `import type { ... }`（`types.ts` 的 `Quote`/`Position`/`NewsItem`/`Status`/`WsEvent` 等）。
- `store.tsx`：`import type` 分离已存在的类型导入。

- [ ] **Step 4: React 组件实践**

- 列表渲染 `key` 唯一（News/Positions 列表）。
- 事件绑定不内联过重逻辑；状态更新用函数式 `set`（zustand 已符合）。
- `Sparkline.tsx` 的 ECharts 实例：组件卸载时 `dispose()` 释放（用 `useEffect` 清理函数）。

- [ ] **Step 5: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
cd .. && python3 scripts/check_no_trade.py   # 前端不参与扫描，仅确认后端未受影响
```

Expected: lint 零错误、build 成功。

- [ ] **Step 6: 提交**

```bash
git add frontend/src && git commit -m "refactor: 前端按 f2e-spec 深度整理（hooks/命名/类型/导入）"
```

---

### Task 7: Git 提交规范 + CI + Makefile 扩展

**Files:**
- Create: `commitlint.config.mjs`（项目根）
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Task 2/5 配置好的双端工具链；现有 `scripts/check_no_trade.py`、`ci.yml`、`Makefile`
- Produces: 全项目可持续执行的规范闸门（commitlint + CI lint/typecheck + Makefile 目标）

- [ ] **Step 1: 创建 `commitlint.config.cjs`**

> `commitlint-config-ali` 是 CommonJS 包（`module.exports`），用 `.cjs` 最稳妥：

```js
module.exports = require('commitlint-config-ali');
```

验证现有提交符合（供参考）：

```bash
git log -5 --pretty=%s | while read -r m; do echo "$m" | grep -qE '^(feat|fix|docs|style|test|refactor|chore|revert)(\(.+\))?: ' && echo "OK: $m" || echo "FAIL: $m"; done
```

Expected: 全部 OK（现有提交已符合）。

- [ ] **Step 2: 扩展 `Makefile`**

保留现有 `install/test/build/check/dev-backend/dev-frontend`，新增：

```make
# 代码规范闸门
lint:  ## 双端 lint + 格式检查
	@echo "== backend: ruff =="
	@cd backend && .venv/bin/ruff check app tests
	@echo "== backend: yapf =="
	@cd backend && .venv/bin/yapf -d app tests
	@echo "== frontend: eslint =="
	@cd frontend && npm run lint
	@echo "== frontend: prettier =="
	@cd frontend && npm run format:check

typecheck:  ## 双端类型检查
	@cd backend && .venv/bin/mypy app
	@cd frontend && npx tsc -b

format:  ## 全量格式化（后端 yapf + 前端 prettier）
	@cd backend && .venv/bin/yapf -ri app tests
	@cd frontend && npm run format
```

注意：Makefile 中 `@` 前缀与 Tab 缩进必须正确（Makefile 语法要求命令前是 Tab）。

- [ ] **Step 3: 扩展 `.github/workflows/ci.yml`**

保留现有双 job 结构（backend：check+pytest；frontend：build），在 backend job 增加：

```yaml
      - name: Lint (ruff)
        run: cd backend && .venv/bin/ruff check app tests
      - name: Format check (yapf)
        run: cd backend && .venv/bin/yapf -d app tests
      - name: Type check (mypy)
        run: cd backend && .venv/bin/mypy app
      - name: Commitlint
        run: npx --yes @commitlint/cli --from origin/main..HEAD
        env:
          NODE_OPTIONS: ''
```

frontend job 增加：

```yaml
      - name: Lint (eslint)
        run: cd frontend && npm run lint
      - name: Format check (prettier)
        run: cd frontend && npm run format:check
```

并确保 frontend job 先 `npm ci`（或 npm install）再 lint。若 CI 的 Python 版本不含 venv，沿用现有 backend job 的依赖安装步骤（pip install -e ".[dev]" + yapf + mypy）。

- [ ] **Step 4: 本地验证**

```bash
make lint && make typecheck && make test && make build && make check
```

Expected: 全绿。若有 yapf/mypy/eslint 报错，说明 Task 3-6 有遗漏，修复后回到对应任务验收，不要在本任务掩盖。

- [ ] **Step 5: 提交**

```bash
git add commitlint.config.cjs Makefile .github/workflows/ci.yml
git commit -m "ci: 接入 lint/typecheck/commitlint 闸门并扩展 Makefile"
```

---

### Task 8: 最终验收 + 执行记录 + 推送

**Files:**
- Modify: `docs/superpowers/plans/2026-08-18-coding-standards-plan.md`（追加执行记录）
- 可能 Modify: 任何验收中发现的遗漏文件

**Interfaces:**
- Consumes: 全部前序任务的产物
- Produces: 可交付状态（全绿 + 已推送）

- [ ] **Step 1: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全部通过（合规 OK / lint 零错 / typecheck 零错 / 29 passed / build 成功）。

- [ ] **Step 2: 端到端冒烟**

```bash
cd backend && (./run.sh &) && sleep 4 && curl -s http://127.0.0.1:8210/api/status && pkill -f "uvicorn app.main"
```

Expected: 200 + `{"logged_in":false,...}`。前端 `cd frontend && npm run dev` 页面可访问（title Investment Board、无 console 报错）。

- [ ] **Step 3: 追加执行记录到计划末尾**

记录：每个任务 commit hash、遇到的偏差（如 eslint 某规则需在 eslint.config.mjs 里按 f2e-spec 白名单调整、yapf 与某 ruff 规则冲突的处理）、遗留事项。格式仿照 MVP 计划执行记录表。

- [ ] **Step 4: 提交并推送**

```bash
git add docs/superpowers/plans/2026-08-18-coding-standards-plan.md
git commit -m "docs: 规范落地计划追加执行记录（as-built）"
git push
```

- [ ] **Step 5: 向用户汇报**

汇报要点：规范文档路径、双端工具链配置、深度整理结果（docstring 覆盖率、类型注解、lint 清零）、验收结果、commit 列表、遗留事项（如有）。

---

## 执行记录（As-Built）

> 全部 8 任务已完成，最终验收 `make check && make lint && make typecheck && make test && make build` 全绿；后端/前端端到端冒烟通过。本计划已整体落地并推送。

| 任务 | commit | 结果 | 偏差/说明 |
| --- | --- | --- | --- |
| Task 1 规范文档 + .editorconfig | `a64ecd0` | ✅ | 四份文档 + 根 `.editorconfig` 按计划落地，无偏差。 |
| Task 2 后端工具链配置 + 基线 + 格式化 | `7d9cbb3` | ✅ | ① yapf 对目录做 diff 校验需加 `-r`（Makefile/CI 中 `yapf -dr`）；② 基线非 D 错误仅 2 个（比计划预期的 16 个少，多为 D10x）；③ ruff D400/D415 强制 docstring 句末用 ASCII `.`，故全项目 docstring 结尾统一用英文句号而非中文 `。`。 |
| Task 3 后端深度重构 A（models/market/news/vault） | `ba5d4e9` | ✅ | ① `parse_tencent` 增加 `ValueError` guard（修复 mypy union-attr 报错，`re.search` 可能返回 None）；② `web_client.py` 在此任务仅加 1 行类型注解（`_json_text` 返回类型）；③ `logging %` 格式化保留不改（惰性求值，避免无谓 f-string 开销）。 |
| Task 4 后端深度重构 B（ths_client/core/api/main/config） | `ad49df7` | ✅ | ① 本任务被中断一次，由新 worker 接续完成：ths_client 3 文件先改未提交，接续 worker 保留原样继续；② 为 8 个包级 `__init__.py`（`backend/app/**/__init__.py` + `backend/tests/__init__.py`）补模块 docstring 清零 D104；③ `scheduler.py` 的 `except Exception` 保留（网络抖动兜底，docstring 已注明）。 |
| Task 5 前端工具链配置 + 全量格式化 | `fbc9333` | ✅ | vite.config.ts 被 tsc 解析报错（allowDefaultProject 方式不稳），改为在 `tsconfig.json` 的 `include` 中追加 `vite.config.ts`（更稳，tsc -b 一次通过）。 |
| Task 6 前端深度重构（f2e-spec 手工核对） | `91b9d69` | ✅ | ① Settings/Positions/main.tsx/client.ts/ws.ts 5 个文件核对后已符合规范、无需改动；② `WsEvent` 必须用 `type` 声明（可辨识联合，interface 无法实现 discriminated union）。 |
| Task 7 Git 提交规范 + CI + Makefile | `7c10609` | ✅ | ① 根目录新增 `package.json`（commitlint 解析用，`commitlint-config-ali` 是 CJS 包）；② commitlint v21 的 `--from` 语义与文档不同，实际用 `--from origin/main --to HEAD`；③ CI backend job 需显式 `python -m venv .venv` 再装依赖；④ commit message 用 `chore:`（阿里 type-enum 无 `ci` 类型）；⑤ mypy 暴露 `store.py` 中 `json.loads` 返回 `Any`，已修复（`isinstance dict` guard）。 |
| 主 agent 额外修复 | `35207cd` | ✅ | CI commitlint 步骤补 `git fetch origin main --depth=1`（checkout 默认 depth=1，无 origin/main 引用导致 `--from` 对比失败）。 |
| Task 8 最终验收 + 执行记录 + 推送 | 本提交 | ✅ | `make check && make lint && make typecheck && make test && make build` 全绿（合规 OK / lint 零错 / mypy 23 文件零错 / 29 passed / build 成功，仅 chunk>500kB 提示）；后端冒烟 `GET /api/status` → 200 `{"logged_in":false,"sources":{"market":"ok","news":"ok"},"ths":{"status":"not_logged_in"}}`；前端 `npm run dev` → 200，title 为 Investment Board。 |

**遗留事项**：
- 前端 bundle 1.19MB（gzip 394KB），build 有 chunk>500kB 警告，属已知、不影响交付；如需可后续做代码分割（动态 import / manualChunks）。
- 无其他功能/契约层面的遗留。

