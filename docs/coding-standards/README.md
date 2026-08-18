# 代码规范（Coding Standards）

本目录集中存放 investment-board 全项目的代码规范文档。规范采取「双轨」体系：

- **前端（TS / React / CSS / HTML）与工程规范**：阿里巴巴前端开发规范 `alibaba/f2e-spec`
- **后端（Python）**：Google Python Style Guide
- **Git 提交信息**：约定式提交（Conventional Commits，阿里 f2e-spec git.md 映射），全项目统一

## 1. 规范总览

| 范围 | 采用的规范 | 权威出处 |
| --- | --- | --- |
| 前端编码（TS / React / CSS / HTML） | 阿里巴巴前端开发规范（f2e-spec） | https://github.com/alibaba/f2e-spec |
| 前端工程（Git / HTTP API / 写作） | 同上（f2e-spec engineering） | https://github.com/alibaba/f2e-spec |
| 后端（Python） | Google Python Style Guide | https://google.github.io/styleguide/pyguide.html |
| 全项目提交信息 | 约定式提交（Conventional Commits） | https://www.conventionalcommits.org/zh-hans/ |

> 说明：文档从权威来源**摘录 + 映射**到本项目实际适用的规则，不整篇照搬（f2e-spec 全文数千行，仅保留本项目需要的部分）。

## 2. 工具链矩阵

规范不只是文档，更由工具链强制落地：

| 端 | 工具 | 作用 | 配置位置 |
| --- | --- | --- | --- |
| 前端 | `eslint` + `eslint-config-ali` | lint（阿里官方规则，含 TS / React / hooks / import） | `frontend/eslint.config.mjs` |
| 前端 | `prettier` + `prettier-config-ali` | 格式化（printWidth 100 / 单引号 / 分号 / 尾逗号） | `frontend/.prettierrc` |
| 前端 | `@commitlint/cli` + `commitlint-config-ali` | 提交信息校验（仅在 CI 执行） | 根 `commitlint.config.mjs` |
| 后端 | `yapf` | 格式化（**唯一 formatter**，Google 风格） | `backend/pyproject.toml` `[tool.yapf]` |
| 后端 | `ruff` | lint（E/W/F/I/UP/B/D/N/ASYNC；**不用 ruff format**，避免与 yapf 冲突） | `backend/pyproject.toml` `[tool.ruff]` |
| 后端 | `mypy` | 类型检查（Google 强类型落地） | `backend/pyproject.toml` `[tool.mypy]` |
| 全项目 | `.editorconfig` | 缩进 / 字符集 / 行尾 / 行宽（前端 2 空格、Python 4 空格、UTF-8 + LF） | 根 `.editorconfig` |

关键决策：

- **yapf 而非 ruff format**：ruff format 是 Black 风格，与 Google 风格有实质差异。Google Style Guide 官方配套工具是 yapf，唯一内置 `google` 风格。
- **行宽统一 100**：yapf `column_limit`、ruff `line-length`、prettier `printWidth`、`.editorconfig` `max_line_length` 对齐为 100。
- **commitlint 只在 CI 校验**（`--from origin/main..HEAD`），不引入本地 git hook，不侵入开发流程。

## 3. 如何让规范持续生效

规范依靠「工具强制 + CI 拦截 + IDE 提示」三层保障：

1. **CI 拦截**：`.github/workflows/ci.yml` 中后端跑 `ruff check` / `yapf -d` / `mypy`，前端跑 `eslint` / `prettier --check` / `tsc -b` / `build`，任一失败即阻断合并。提交信息由 commitlint 校验（`npx @commitlint/cli --from origin/main..HEAD`）。
2. **本地命令**（`Makefile`）：
   - `make lint`：后端 ruff + yapf 检查、前端 eslint + prettier 检查
   - `make format`：后端 yapf 全量、前端 prettier 全量
   - `make typecheck`：后端 mypy、前端 tsc
   - `make check`：合规静态扫描（`scripts/check_no_trade.py`）
3. **IDE 配置指引**：
   - 安装对应编辑器的 ESLint / Prettier / EditorConfig 插件，保存时自动格式化，`.editorconfig` 自动生效（缩进 / LF / 末尾换行）。
   - VS Code 可在 `settings.json` 中设置 `"editor.rulers": [100]` 与 `"editor.formatOnSave": true`。
   - Python 侧避免安装 ruff 的 formatter 作为保存动作（格式化统一走 yapf）。

## 4. 分项文档

- [backend.md](backend.md)：Google Python Style Guide 在本项目的落地规则（命名 / 类型注解 / docstring / main() 入口 / 异常 / import / 字符串 / 工具配置）
- [frontend.md](frontend.md)：阿里 f2e-spec 在本项目的落地规则（hooks / 命名 / 类型 / 导入 / Prettier / JSX）
- [git-commit.md](git-commit.md)：约定式提交规范（type 枚举 / 格式 / 示例 / commitlint 校验）
