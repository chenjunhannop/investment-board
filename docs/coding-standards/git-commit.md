# Git 提交规范：约定式提交（Conventional Commits）

> 适用范围：全项目（前后端与文档统一）。
> 权威来源：阿里 f2e-spec 工程规范 [docs/engineering/git.zh.md](https://github.com/alibaba/f2e-spec/blob/master/docs/engineering/git.zh.md) 与 [约定式提交 v1.0.0](https://www.conventionalcommits.org/zh-hans/)。
> 落地方式：CI 中用 `commitlint`（`commitlint-config-ali`）校验，不引入本地 git hook。

## 1. 格式

```
<type>[scope]: <description>
```

例如：`feat: 前端持仓页`、`fix(api): 修复 WebSocket 重连抖动`。

## 2. type 枚举

type 描述本次提交的改动类型：

| type | 含义 |
| --- | --- |
| `feat` | 新增功能 |
| `fix` | 修复 bug |
| `docs` | 文档相关的改动 |
| `style` | 对代码的格式化改动，代码逻辑并未产生任何变化（如缩进、分号的移除和添加） |
| `test` | 新增或修改测试用例 |
| `refactor` | 重构代码或其他优化举措 |
| `chore` | 项目工程方面的改动，代码逻辑并未产生任何变化 |
| `revert` | 恢复之前的提交 |

> 注意：CSS 样式文件的修改一般属于 `feat` 或 `fix`，并不是 `style`。

## 3. scope（可选）

scope 描述本次提交涉及的改动范围（模块 / 功能 / 包），视项目而定：

```
chore(backend): 配置 yapf/ruff/mypy
fix(api): 修复 WS 事件订阅防泄漏
```

## 4. description 书写要求

- **语言**：项目现有提交用中文，保持一致；中文或英文皆可，但不要混用拼音或他人无法理解的缩写。
- **动词开头、一般现在时、祈使句**（不写主语）：
  - good：`docs: 添加代码规范文档`
  - bad：`docs: 添加了代码规范文档`（过去时）
- **句首不大写、句尾不加标点**（description 不是完整句子）。
- **尽量不超 50 字符**，一句话概括核心改动；详细内容写正文（body）。

## 5. 示例

含本项目真实提交：

```
feat: 行情服务（新浪/腾讯，去重合并，源切换）
feat: 新闻服务（东财公告+财联社，去重与代码匹配）
feat: THS 只读客户端（扫码登录+自选/持仓查询）
docs: 股票看板 MVP 实施计划（15 任务，TDD + 合规静态检查）
ci: 合规静态检查 + 测试 + 前端构建流水线
fix: AST 重写合规静态检查，堵住组合标识符漏报（buy_stock 等）
docs: 代码规范落地设计（阿里 f2e-spec + Google Python Style）
```

## 6. commitlint 校验

CI（`.github/workflows/ci.yml`）对**本次推送的提交**执行校验：

```bash
npx --yes @commitlint/cli --from origin/main..HEAD
```

- 规则来自 `commitlint-config-ali`（根目录 `commitlint.config.mjs`）。
- 本地不安装 git hook，不强制在提交时阻塞，避免侵入开发流程。
