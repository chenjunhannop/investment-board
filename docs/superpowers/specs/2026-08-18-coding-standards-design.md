# 项目代码规范落地设计（阿里 f2e-spec + Google Python Style）

> 日期：2026-08-18
> 状态：已确认（brainstorming 完成，待实施）
> 关联：`2026-08-18-investment-board-design.md`（产品设计）、`2026-08-18-investment-board-mvp.md`（MVP 实施计划）

## 1. 背景与目标

investment-board MVP 已交付（后端 29 测试、前端构建成功、合规扫描通过）。本项目将引入权威代码规范并**深度整理现有代码**，使规范成为可执行的工程约束，而非停留在文档层面。

**规范选型（用户已确认）**：
- **前端/工程**：阿里巴巴官方前端开发规范 `alibaba/f2e-spec`（编码规范：TS/React/CSS/HTML/通用；工程规范：Git 提交/http-json-api/写作；配套 npm 工具链）
- **后端**：Google Python Style Guide（官方权威 Python 规范，用 yapf/ruff/mypy 工具化落地）
- **Git 提交规范**：阿里 f2e-spec 的约定式提交，全项目统一（git 全局共享，不分前后端）

**整理深度（用户已确认）**：深度整理 = 工具链落地 + 手工重构让代码真正符合规范，测试保持全绿、不做破坏性改动。

## 2. 规范体系与文档落地

### 2.1 规范来源

| 范围 | 规范 | 权威出处 |
|---|---|---|
| 前端编码（TS/React/CSS/HTML） | 阿里巴巴前端开发规范 | github.com/alibaba/f2e-spec |
| 前端工程（Git/API/写作） | 同上 | 同上 |
| 后端（Python） | Google Python Style Guide | google.github.io/styleguide/pyguide.html |
| 全项目提交信息 | 约定式提交（阿里 git.md 映射） | 同上 f2e-spec |

### 2.2 项目内规范文档（新增 `docs/coding-standards/`）

| 文件 | 内容 |
|---|---|
| `README.md` | 规范总览：哪些引用阿里、哪些引用 Google；工具链矩阵；如何让规范持续生效 |
| `backend.md` | Google Style 关键规则映射到本项目（命名/类型注解/docstring/异常/import/行宽）+ yapf/ruff/mypy 配置说明 |
| `frontend.md` | f2e-spec 关键规则摘录（TS 命名、React hooks、组件、导入、Prettier 选项） |
| `git-commit.md` | 阿里 git.md 约定式提交（type 枚举/scope/描述），全项目统一 |

> 文档从权威来源**摘录+映射**本项目实际规则，不整篇照搬（f2e-spec 全文数千行，只保留适用于本项目的部分）。

### 2.3 根目录 `.editorconfig`（阿里通用规范落地）

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

要点：前端 2 空格（阿里通用规约强制）、Python 4 空格（PEP8/Google）、全文件 UTF-8/LF。

## 3. 后端 Google Python Style 落地

### 3.1 工具链（写入 `backend/pyproject.toml`）

| 工具 | 作用 | 配置要点 |
|---|---|---|
| **yapf** | 格式化（**唯一 formatter**，Google 风格） | `[tool.yapf]` `based_on_style = "google"`，`column_limit = 100`（与 ruff 行宽对齐） |
| **ruff** | lint（**不用 ruff format**，避免与 yapf 冲突） | `[tool.ruff.lint]` 规则集 E/W/F/I/UP/B/D/N/ASYNC；`[tool.ruff.lint.pydocstyle] convention = "google"`；E501 交给 yapf 管 |
| **mypy** | 类型检查（Google 强类型落地） | `[tool.mypy]` 全文件检查，报错逐个修复 |

关键决策：
- **yapf 而非 ruff format**：ruff format 是 Black 风格，与 Google 风格有实质差异（换行/括号/操作符策略）。Google Style Guide 官方配套工具是 yapf（Google 自研），唯一内置 `google` 风格。
- **ruff 只做 lint**：格式化归 yapf，避免两个 formatter 互相覆盖。行宽统一 100（yapf `column_limit` 与 ruff `line-length` 对齐）。

### 3.2 深度重构要点（逐条核对现有代码）

1. **命名**：`module_name`/`ClassName`/`method_name`/`CONSTANT`/`_private` 扫描（ruff N 规则自动查 + 人工核对）
2. **类型注解**：公开 API/函数参数/返回值补齐（mypy 驱动）
3. **docstring**：改 Google 风格（`Args:`/`Returns:`/`Raises:`），由 ruff D（google convention）检查
4. **`main()` 入口**：`backend/app/main.py` 用 `def main() -> None` + `if __name__ == "__main__":`（Google 强制）
5. **异常**：捕获尽量具体类型、显式 `raise`（避免裸 `except:`）
6. **import**：分组排序（stdlib/第三方/本地，ruff I）
7. **容器泛型标注**：`list[str]`/`dict[str, X]` 而非裸 `list`/`dict`；无 `def f(x=[])` 可变默认参数
8. **字符串**：统一 f-string（Python 3.11）
9. **yapf 格式化**：全量重排（对齐 google 风格）

### 3.3 说明：与既有 ruff 配置的关系

现有 `pyproject.toml` 已有 `[tool.ruff] line-length = 100, target-version = "py311"`。本次扩展 `[tool.ruff.lint]` 规则集与 pydocstyle convention，并新增 `[tool.yapf]`/`[tool.mypy]`，不破坏现有 pytest 配置。

## 4. 前端 f2e-spec 落地

### 4.1 工具链（写入 `frontend/package.json` devDependencies）

| 工具 | 作用 | 配置 |
|---|---|---|
| `eslint@^9` + `eslint-config-ali@^16` | lint（阿里官方规则） | `eslint.config.mjs`（flat config）：`import { react } from 'eslint-config-ali'`，覆盖 `src` + 配置文件 |
| `prettier` + `prettier-config-ali` | 格式化 | `.prettierrc`：`"prettier-config-ali"`（printWidth 100 / singleQuote / semi / trailingComma all / LF）|
| `@commitlint/cli` + `commitlint-config-ali` | 提交信息校验 | `commitlint.config.mjs` |

**不使用 `tsconfig-ali`**：经验证其包内容为空壳（index.js 为空），价值有限；现有 `tsconfig.json` 已 strict，按 f2e-spec 文档手动微调即可。

### 4.2 scripts 扩展（`frontend/package.json`）

```json
"lint": "eslint .",
"lint:fix": "eslint . --fix",
"format": "prettier --write .",
"format:check": "prettier --check ."
```

### 4.3 深度重构要点（f2e-spec 逐条核对）

1. **React hooks 规范**：`exhaustive-deps`（useEffect 依赖补全）、不在循环/条件中调 hook、自定义 hook 命名 `useXxx`
2. **命名**：组件 PascalCase、文件与组件名一致、props 类型显式定义、回调 props 前缀 `on`
3. **类型**：TS strict 补强、避免 `any`、props 用 interface、纯类型导入用 `import type`
4. **导入**：排序与分组（eslint import 规则）
5. **React 组件实践**：key 唯一、事件处理绑定、状态更新函数式
6. **Prettier 重排**：全量格式化（分号/单引号/尾逗号/换行统一为阿里配置）

## 5. Git 提交规范（阿里 git.md，全项目统一）

- 现有提交已是 "feat: ..." 约定式格式，**不改写已推送历史**
- 新增 `commitlint.config.mjs`（`commitlint-config-ali`）校验**本次推送的提交**
- 落地方式：**CI 检查**（`npx commitlint --from origin/main..HEAD`），不强制本地 hook（不侵入开发流程）

type 枚举（阿里映射）：feat/fix/docs/style/test/refactor/chore/revert。

## 6. CI 集成与 Makefile

### 6.1 `.github/workflows/ci.yml` 扩展（双 job）

- **backend job**（顺序）：
  1. `make check`（合规静态扫描，现有）
  2. `ruff check`（lint，新增）
  3. `yapf --diff`（格式检查，新增）
  4. `mypy`（类型检查，新增）
  5. `pytest`（29 测试，现有）
- **frontend job**（顺序）：
  1. `eslint .`（新增）
  2. `prettier --check .`（新增）
  3. `tsc -b`（现有 build 的一部分）
  4. `npm run build`（现有）

### 6.2 Makefile 扩展

```make
lint:      # ruff check + yapf 检查（后端）；eslint + prettier 检查（前端）
format:    # yapf 全量（后端）+ prettier 全量（前端）
typecheck: # mypy（后端）+ tsc（前端）
```

`make check` 保持合规扫描职责不变。

## 7. 测试保障与验收标准（硬性约束）

重构期间**逐步提交**（每模块一提交），保证中间态可回滚。最终验收全绿：

| 命令 | 预期 |
|---|---|
| `make check` | 合规扫描 OK |
| `make lint` | ruff + eslint + prettier 检查零错误 |
| `make typecheck` | mypy + tsc 零错误 |
| `make test` | 29 passed |
| `make build` | 前端构建成功 |
| 端到端冒烟 | 后端启动 + `/api/status` 正常返回 |

## 8. 非目标（不做）

- 不改写已推送的 git 历史（现有提交已符合约定式格式）
- 不引入本地 git hook（commitlint 只在 CI 校验）
- 不重写/重构产品功能、不改变 API 契约、不迁移架构
- 不引入 `tsconfig-ali`（空壳无价值）
- 不对后端使用 ruff format（统一由 yapf 承担 Google 风格格式化）
- 不做超过"深度整理"的重写式重构（不拆组件、不改目录结构、不重写测试）

## 9. 待实施清单（写入实施计划）

1. 规范文档 `docs/coding-standards/`（4 个 md）+ 根 `.editorconfig`
2. 后端：pyproject 配置（yapf/ruff lint 集/mypy）+ 全量 yapf 格式化 + 深度重构（docstring/类型/命名/异常/import）+ mypy 修复
3. 前端：eslint/prettier/commitlint 安装与配置 + 全量格式化 + 深度重构（hooks/命名/类型/导入）
4. Git：commitlint.config.mjs + CI 校验
5. CI/Makefile 扩展
6. 最终验收：`make check && make lint && make typecheck && make test && make build` + 端到端冒烟
