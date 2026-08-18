# 前端视觉重设计设计文档（frontend-design skill 主导）

- 日期：2026-08-18
- 状态：已获用户认可（方向方案）
- 驱动 skill：`frontend-design`（anthropics/skills，788K installs，Anthropic 官方）

## 1. 背景与目标

Investment Board（本地自托管 A股投资看板，只读、隐私优先）MVP 已完成、代码已符合阿里 f2e-spec 规范。当前视觉为功能优先的"深色基础金融风"（近黑蓝底 + 系统默认字体 + 模板蓝 accent），缺乏设计观点。

目标：用 `frontend-design` skill 的方法论，为看板打造**有差异化、基于"A股投资看板"主题**的深色视觉身份——配色、字体、排版、动效全面重做，让界面专业、好读、有记忆点，且不落入 AI 生成模板。

## 2. 非目标（明确不做）

- 不改任何功能逻辑、API 契约、页面结构（tabs/Dashboard/Positions/News/Settings 不变）
- 不改组件拆分与目录结构；尽量不改 TSX 逻辑，仅在需要处加极少量结构性元素（如竖色条，优先用 CSS 伪元素实现）
- 不触碰后端（不改任何 Python）；`make check`（合规扫描）与 `make test`（29 passed）不受影响
- 不引入 Tailwind 或 UI 组件库；继续用原生 CSS（theme.css 单文件 token 化）
- 不做滚动触发、页面转场等营销页级动效（看板是工具）
- 不引入中文字体（体积大、系统字体已足够）；不重构 API/数据层

## 3. 设计系统（Design Token）

### 3.1 Color（6 个核心 token + 涨跌 + 衍生态）

| Token | 值 | 角色 |
|---|---|---|
| `--bg` | `#0B0F14` | 页面底色（墨蓝黑，比原 `#0f1419` 更沉稳有层次） |
| `--panel` | `#131A23` | 面板/卡片底（带蓝调深灰） |
| `--border` | `#1F2A36` | 分隔线/描边 |
| `--text` | `#E8EDF2` | 主文字（冷白） |
| `--muted` | `#7C8B9C` | 次级文字 |
| `--accent` | `#D4A948` | 琥珀金：选中态/品牌/交互 focus |

涨跌（A股惯例红涨绿跌，精确化）：

| Token | 值 | 角色 |
|---|---|---|
| `--up` | `#E5484D` | 上涨（红） |
| `--down` | `#2E9E6B` | 下跌（绿） |

衍生态 token：

| Token | 值 | 角色 |
|---|---|---|
| `--up-bg` | `rgba(229,72,77,0.10)` | 涨卡整卡微染底 |
| `--down-bg` | `rgba(46,158,107,0.10)` | 跌卡整卡微染底 |
| `--panel-hover` | `#182230` | 卡片 hover 抬升底 |

设计依据：避开"近黑+模板蓝" AI 默认；琥珀金呼应财富/投资主题并与红涨绿跌区分（中国券商视觉有金色语境）；红涨绿跌是 A 股识别色。

### 3.2 Type（3 roles + 中文策略）

- **数据 face（灵魂，克制使用）**：`IBM Plex Mono`（经 npm `@fontsource/ibm-plex-mono` 引入 latin 子集 400/500/700，离线可用），fallback `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`。仅用于：行情价格、涨跌幅、持仓金额、时间戳、代码。统一 `font-variant-numeric: tabular-nums`（等宽数字对齐）。
- **正文 face**：拉丁 `Inter` 类系统栈 + 中文 `PingFang SC, Microsoft YaHei`。保持系统栈，不引字体文件。
- **标签/数据 label face**：正文同族，`12px + letter-spacing: 0.04em`，用于 tab、表头、code、日期、连接状态。

字号阶梯：`11/12/13/14/16/20/26/34px`；行情价格用最大号（26–34），卡标题 14，标签 12。

### 3.3 Layout（结构概念）

保持看板 grid 本质，强化"终端状态带 + 数字节奏"：

- **终端状态带**：顶部状态条升级为全宽状态带（连接状态点 + 数据源 + 时间戳），一眼可见系统健康度。主导航 tabs **集合与功能不变**（仍为自选/持仓/新闻/设置 4 项），仅视觉上从独立一行与顶栏合并为一条状态带区域——属视觉重组，非结构变更。
- **行情卡**：`--panel` 底 + 1px `--border` + 整卡涨跌微染（`--up-bg`/`--down-bg`）+ 左侧 3px 竖色条（`::before`，色=涨跌）+ 大号等宽价格 + 涨跌标签（▲/▼ + 百分比，红涨绿跌）。
- **持仓明细**：表格化，金额/盈亏列用等宽数字右对齐，盈亏按红涨绿跌着色。
- **新闻**：列表式，标题 + 来源/时间 muted，卡片 hover 抬升。
- **页面间距**：保持现有呼吸节奏（16px 页面 padding、12px 卡片 gap），微调层级。

ASCII wireframe（方向已确认，实施时按此）：

```
┌──────────────────────────────────────────────────────┐
│ ● 实时连接中  源:新浪·腾讯  12:34:56   [自选|持仓|新闻|设置] │  ← 状态带
├──────────────────────────────────────────────────────┤
│ 自选实时行情                                          │
│ ┌───红─────┐ ┌───绿─────┐ ┌───红─────┐              │
│ │ 贵州茅台  │ │ 宁德时代  │ │ 中概互联  │  ← 整卡微染+左竖条 │
│ │ 600519   │ │ 300750   │ │ 513050   │              │
│ │ 1708.00  │ │ 186.40   │ │ 0.902    │  ← IBM Plex Mono │
│ │ ▲ +2.3%  │ │ ▼ -1.1%  │ │ ▲ +0.4%  │              │
│ └──────────┘ └──────────┘ └──────────┘              │
│ 持仓明细 · 新闻 …                                     │
└──────────────────────────────────────────────────────┘
```

### 3.4 Signature（唯一记忆点）

**A股色彩语言直接入界面**：行情卡整卡红涨绿跌微染 + 左侧竖色条 + 大号等宽数字。打开看板即用 A 股自己的色彩语言读懂全局。

### 3.5 Motion（克制动效）

- 价格/涨跌数值变化：`color/opacity` 200ms 过渡（数值跳动微反馈）
- 卡片 hover：`--panel-hover` 抬升 + 1px 提位
- 状态带连接点：`opacity` 呼吸动画（2.4s 循环）
- 全部包裹 `@media (prefers-reduced-motion: reduce)` 关闭
- 无滚动触发/页面转场

### 3.6 Spacing / Radius / 其他

- Radius：卡片 8px、按钮 6px（保持现风格）
- 行高：正文 1.6，数字 1.2
- 可访问性：焦点环用 `--accent` 琥珀金 outline；红绿之外均配 ▲/▼ 与文字；对比度满足 WCAG AA

## 4. 页面级应用

| 页面/组件 | 主要变化 |
|---|---|
| theme.css | 全部 token 化重写：配色/字体栈/状态带/卡片微染/动效/焦点态 |
| Dashboard | 状态带升级、行情卡微染+竖条+等宽数字 |
| PriceCard | 价格 IBM Plex Mono 大号、涨跌 ▲▼+百分比、微染底、竖色条 |
| PositionsSummary | 表格等宽数字右对齐、盈亏红涨绿跌 |
| NewsCard | hover 抬升、标题/来源层级 |
| Positions / News / Settings | tabs 琥珀金选中、面板层级、按钮态、QR 块视觉微调 |
| Sparkline | 颜色随涨跌（`--up`/`--down`） |

组件 TSX 尽量不动：竖色条用 `::before`，微染用背景色；仅当伪元素无法实现时允许加 1 个结构性元素（需在计划中说明）。

## 5. 实施约束

- 只改 `frontend/src/` 下 CSS 与必要 TSX 微调；不碰 `backend/`、`scripts/`、`docs/`（除本 spec/计划）
- 引入 `@fontsource/ibm-plex-mono`（latin 400/500/700）
- 遵循 f2e-spec/eslint/prettier（现有工具链全绿保持）
- 中文文案按 frontend-design 写作原则微调（主动语态、界面语言一致；不改业务语义）

## 6. 验收标准

1. `cd frontend && npm run lint && npm run format:check && npm run build` 全绿
2. `make check`（合规 OK）、`make test`（29 passed）不受影响
3. 手动冒烟：dev server 打开 4 个页面，深色新视觉生效；涨跌微染、等宽数字、状态带、hover、焦点环、reduced-motion 均正确
4. 视觉对比截图：与改造前对比，确认"整卡红涨绿跌 + 等宽数字 + 琥珀金 accent"三个 signature 元素清晰可见
5. 响应式：窄屏（grid 塌缩）正常

## 7. 参考

- `frontend-design` skill（`~/.pi/agent/skills/frontend-design/SKILL.md`）：设计原则/两遍法/token 系统/克制与自我批评/文案原则
- 现有 `frontend/src/theme.css` 为 token 化重写基线
