# 前端视觉重设计实施计划（frontend-design skill 主导）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec（`docs/superpowers/specs/2026-08-18-frontend-visual-redesign-design.md`）为 Investment Board 打造深色金融终端风的差异化视觉身份——A股红涨绿跌整卡微染 + 左侧竖色条 + 等宽数字 + 琥珀金 accent。

**Architecture:** 以 `frontend/src/theme.css` 单文件设计 token 化为核心（CSS custom properties），配合 3 处极少量 TSX 微调（PriceCard 涨跌类名、Sparkline canvas 颜色读取、Dashboard 状态带），其余组件全部通过 CSS 换肤。引入 `@fontsource/ibm-plex-mono`（latin 子集，离线可用）做数据数字字体。分 4 个样式任务 + 1 个验收任务逐步交付。

**Tech Stack:** React 18 + TS 5.4 + Vite 5、原生 CSS（theme.css 单文件）、ECharts（Sparkline）、@fontsource/ibm-plex-mono、eslint-config-ali + prettier-config-ali

## Global Constraints

- 只改 `frontend/src/`；不碰 `backend/`、`scripts/`、`.github/`、`docs/`（除本计划与执行记录）
- 引入依赖：`@fontsource/ibm-plex-mono`（npm，仅此一个新增运行时依赖）
- 遵循阿里 f2e-spec 工具链：`cd frontend && npm run lint && npm run format:check` 每任务后全绿（prettier printWidth 100 / 2 空格）
- 保持组件功能、页面行为、API 契约不变；TSX 改动仅限本计划明确列出的 3 处（PriceCard/Sparkline/Dashboard）
- 合规红线：不得引入以 buy/sell/trade/order 为前缀的标识符或中文"买入/卖出"类业务词；`python3 scripts/check_no_trade.py` 必须 OK
- 后端不受影响：`make test` 保持 29 passed
- 视觉签名三要素必须全部呈现：①整卡红涨绿跌微染 ②左侧竖色条 ③大号等宽数字
- 动效包裹在 `@media (prefers-reduced-motion: reduce)` 内关闭
- commit message 用 `style:` 类型（阿里 commitlint type-enum 含 style，勿用 `ci:`/`ui:`）
- 涨跌配色 A股惯例：`--up: #E5484D` 红涨、`--down: #2E9E6B` 绿跌；accent 用琥珀金 `#D4A948`（不占用红绿语义）
- ECharts 是 canvas 渲染，**不支持 CSS var**——Sparkline 颜色必须用 `getComputedStyle` 读取
- 构建产物 `dist/`、`*.tsbuildinfo` 已在 .gitignore，不入库

---

### Task 1: 设计 token 与全局框架换肤（含状态带）

**Files:**
- Modify: `frontend/src/theme.css`（`:root` token + 全局重置 + body + `.app`/`.topbar`/`.tabs`/`.page`/`.status-bar` 区块重写）
- Modify: `frontend/src/main.tsx`（引入字体）
- Modify: `frontend/src/pages/Dashboard.tsx`（status-bar 升级为状态带：连接点 + 时间戳）
- Modify: `frontend/package.json` / `package-lock.json`（新增 @fontsource/ibm-plex-mono）

**Interfaces:**
- Consumes: 现有 className（`.topbar`/`.tabs`/`.status-bar`/`.page`，均已在 TSX 中）
- Produces: `--font-data`、`--font-body`、全部色板 token、`.status-bar .dot` 连接点样式（Task 4 加呼吸动画）、`:focus-visible` 焦点环

- [ ] **Step 1: 安装字体**

```bash
cd frontend && npm install @fontsource/ibm-plex-mono
```

- [ ] **Step 2: main.tsx 引入字体（latin 400/500/600）**

在 `frontend/src/main.tsx` 顶部 import 区追加（紧跟现有 import 之后、字母序内）：

```tsx
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import '@fontsource/ibm-plex-mono/600.css';
```

（保持现有 React 导入在前，CSS 导入按 prettier 重排后的现有顺序插入。）

- [ ] **Step 3: 重写 theme.css 的 token 层 + 全局 + 框架区块**

把 `frontend/src/theme.css` 中从文件头 `:root { ... }` 到 `.page` 区块结束（含 `.page h2`）整段替换为：

```css
:root {
  --bg: #0b0f14;
  --panel: #131a23;
  --border: #1f2a36;
  --text: #e8edf2;
  --muted: #7c8b9c;
  --accent: #d4a948;
  --up: #e5484d;
  --down: #2e9e6b;
  --up-bg: rgba(229, 72, 77, 0.1);
  --down-bg: rgba(46, 158, 107, 0.1);
  --panel-hover: #182230;
  --font-data: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --radius: 8px;
  --radius-sm: 6px;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}

.app {
  max-width: 1080px;
  margin: 0 auto;
  padding: 16px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.topbar h1 {
  font-size: 20px;
  font-weight: 650;
  letter-spacing: 0.01em;
  margin: 0;
}

.tabs {
  display: flex;
  gap: 6px;
}
.tabs button {
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: color 160ms ease, border-color 160ms ease, background 160ms ease;
}
.tabs button:hover {
  color: var(--text);
}
.tabs button.active {
  color: var(--accent);
  background: var(--panel);
  border-color: rgba(212, 169, 72, 0.35);
}

.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.page h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 4px 0;
}
```

- [ ] **Step 4: 替换 `.status-bar` 区块为终端状态带**

把 theme.css 中原 `.status-bar` 区块替换为：

```css
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius);
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--muted);
}
.status-bar .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.4;
}
.status-bar .dot.on {
  opacity: 1;
}
.status-bar .conn {
  color: var(--text);
}
.status-bar .stamp {
  margin-left: auto;
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}
```

- [ ] **Step 5: Dashboard 状态带 TSX 微调（连接点 + 时间戳）**

`frontend/src/pages/Dashboard.tsx`：顶部 import 增加 `useEffect, useState`（若尚未引入），组件内加时间 state，status-bar 改为：

```tsx
import { useEffect, useState } from 'react';
// ... 其余 import 保持

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const connected = useApp((s) => s.wsStatus === 'connected');
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);
  const stamp = now.toLocaleTimeString('zh-CN', { hour12: false });
  // ...
  return (
    <div className="page">
      <div className="status-bar">
        <span className={`dot ${connected ? 'on' : ''}`} />
        <span className="conn">{connected ? '实时连接中' : '连接断开，重连中…'}</span>
        <span className="stamp">源: 新浪·腾讯 · {stamp}</span>
      </div>
      {/* ... 其余不变 */}
    </div>
  );
}
```

> 先读原 Dashboard.tsx 的完整 import 与组件头，保留原有 `quotes`/`connected` 取值方式（`wsStatus` 若字段名不同以原文件为准），仅替换 status-bar 那行与新增时间逻辑。

- [ ] **Step 6: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
```

Expected: lint 零错误零警告；format:check 全匹配；build 成功（chunk>500kB 提示可忽略）。

- [ ] **Step 7: 提交**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/theme.css frontend/src/main.tsx frontend/src/pages/Dashboard.tsx
git commit -m "style: 前端设计 token 化与全局换肤（深色金融终端风）"
```

---

### Task 2: 行情卡视觉（涨跌微染 + 竖色条 + 等宽数字）与 Sparkline 涨跌色

**Files:**
- Modify: `frontend/src/theme.css`（`.grid`/`.cell`/`.price-card` 区块重写）
- Modify: `frontend/src/components/PriceCard.tsx`（加涨跌类名）
- Modify: `frontend/src/components/Sparkline.tsx`（canvas 颜色随涨跌）

**Interfaces:**
- Consumes: Task 1 的 `--up/--down/--up-bg/--down-bg/--font-data/--radius` token；PriceCard 现有 `up` 布尔
- Produces: `.price-card.up`/`.price-card.down` 微染类（Task 3 的持仓/新闻不依赖，纯视觉）

- [ ] **Step 1: PriceCard 加涨跌类名**

`frontend/src/components/PriceCard.tsx` 第 10 行改为：

```tsx
    <div className={`price-card ${up ? 'up' : 'down'}`}>
```

（其余不变；`up` 已存在。）

- [ ] **Step 2: 重写 theme.css 的 grid/cell/price-card 区块**

把 theme.css 中 `.grid`、`.cell`、`.price-card` 相关区块（从 `.grid {` 到 `.price-card .muted` 结束）替换为：

```css
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.cell {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  transition: transform 160ms ease, background 160ms ease, border-color 160ms ease;
}
.cell:hover {
  background: var(--panel-hover);
  transform: translateY(-1px);
}

.price-card {
  position: relative;
  border: 1px solid var(--border);
  border-left: 3px solid transparent;
  border-radius: var(--radius);
  background: var(--panel);
  padding: 14px;
  overflow: hidden;
}
.price-card.up {
  border-left-color: var(--up);
  background: linear-gradient(180deg, var(--up-bg), transparent 55%), var(--panel);
}
.price-card.down {
  border-left-color: var(--down);
  background: linear-gradient(180deg, var(--down-bg), transparent 55%), var(--panel);
}
.price-card .name {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
}
.price-card .code {
  color: var(--muted);
  font-family: var(--font-data);
  font-weight: 400;
  font-size: 11px;
  letter-spacing: 0.04em;
}
.price-card .price {
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
  font-size: 26px;
  font-weight: 600;
  margin: 6px 0 2px;
  transition: color 200ms ease;
}
.price-card .change {
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}
.price-card .muted {
  margin-top: 8px;
  font-size: 11px;
  color: var(--muted);
}
```

- [ ] **Step 3: Sparkline 颜色随涨跌（canvas 不支持 CSS var）**

`frontend/src/components/Sparkline.tsx` 的 `useEffect` 内、`echarts.init` 前插入涨跌推断与颜色读取，并把 `lineStyle` 的 color 替换：

```tsx
  useEffect(() => {
    if (!ref.current) return;
    const up = data.length >= 2 ? data[data.length - 1] >= data[0] : true;
    const cssVar = up ? '--up' : '--down';
    const color =
      getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim() || '#e5484d';
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [
        {
          type: 'line',
          data,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.5, color },
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);
```

- [ ] **Step 4: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
```

Expected: 全绿（lint 零错误、format 全匹配、build 成功）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/theme.css frontend/src/components/PriceCard.tsx frontend/src/components/Sparkline.tsx
git commit -m "style: 行情卡涨跌微染与等宽数字（Sparkline 随涨跌）"
```

---

### Task 3: 持仓表格与新闻列表视觉升级

**Files:**
- Modify: `frontend/src/theme.css`（`.summary-card`、`.tbl`、`.news-*` 区块）

**Interfaces:**
- Consumes: Task 1 token；Positions.tsx 的 `.tbl` 表格（10 列，第 1 列代码/第 2 列名称）；NewsCard 的 `.news-card`/`.news-title`/`.news-meta`/`.read`；PositionsSummary 的 `.summary-card`
- Produces: 无（纯视觉，无下游依赖）

- [ ] **Step 1: 重写 theme.css 的 summary-card + tbl + news 区块**

把 theme.css 中 `.summary-card` 区块替换为：

```css
.summary-card {
  display: flex;
  gap: 32px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--muted);
}
.summary-card b {
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
  font-size: 18px;
  margin-left: 6px;
  color: var(--text);
}
```

新增 `.tbl` 区块（置于 `.summary-card` 之后）：

```css
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.tbl th,
.tbl td {
  text-align: right;
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}
.tbl th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.04em;
}
.tbl th:first-child,
.tbl td:first-child {
  text-align: left;
  font-family: var(--font-data);
  font-size: 12px;
}
.tbl tbody tr:hover {
  background: var(--panel-hover);
}
.tbl tr:last-child td {
  border-bottom: none;
}
```

把 theme.css 中 `.panel h3` 之后的 `.panel p`/`.panel ul` 保留，新增 `.news-list`/`.news-card` 区块（置于 `.tbl` 之后）：

```css
.news-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.news-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, transform 160ms ease;
}
.news-card:hover {
  background: var(--panel-hover);
  transform: translateY(-1px);
}
.news-card .news-title {
  font-size: 14px;
  line-height: 1.5;
}
.news-card .news-meta {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
}
.news-card.read {
  opacity: 0.6;
}
```

> 先读 theme.css 确认现有 `.panel p`/`.panel ul`/`.news-*` 现状，避免重复定义；若原文件已有 `.news-*` 则整体替换。

- [ ] **Step 2: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
```

Expected: 全绿。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/theme.css
git commit -m "style: 持仓表格与新闻列表视觉升级"
```

---

### Task 4: 设置面板、动效与可访问性收尾

**Files:**
- Modify: `frontend/src/theme.css`（`.panel`/按钮/`.qr-*`/动效/reduced-motion/`:focus-visible`）

**Interfaces:**
- Consumes: Task 1 的 `--accent`/`--radius-sm`；Settings.tsx 的 `.panel`/`.panel h3`/`.panel button`/`.danger`/`.qr-box`/`.qr-code`
- Produces: 全站焦点环、连接点呼吸、reduced-motion 兜底（最终验收依赖）

- [ ] **Step 1: 重写 panel/按钮区块并加动效**

把 theme.css 中 `.panel` 区块到 `.qr-code` 结束的部分整体替换为：

```css
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  font-size: 14px;
}
.panel h3 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
}
.panel p {
  margin: 6px 0;
}
.panel ul {
  margin: 8px 0;
  padding-left: 18px;
  line-height: 1.9;
}
.panel button {
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  cursor: pointer;
  font-size: 14px;
  font-family: inherit;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
}
.panel button:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.panel button.danger {
  color: #ff6b6b;
  border-color: #ff6b6b;
}
.panel button.danger:hover {
  background: rgba(255, 107, 107, 0.1);
  color: #ff6b6b;
}

.qr-box {
  margin-top: 12px;
}
.qr-code {
  white-space: pre-wrap;
  word-break: break-all;
  user-select: all;
  background: #0b0f14;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
  font-family: var(--font-data);
}

.muted {
  color: var(--muted);
}
```

- [ ] **Step 2: 追加动效、连接点呼吸、焦点环、reduced-motion 区块（theme.css 末尾）**

```css
/* 状态带连接点呼吸 */
.status-bar .dot {
  transition: opacity 200ms ease;
}
.status-bar .dot.on {
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* 键盘焦点可见 */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* 尊重减少动效偏好 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

> 注：`.status-bar .dot` 已在 Task 1 定义基础样式，此处仅追加 transition + on 呼吸；两段 `.dot` 规则不冲突（后者追加）。`:focus-visible` 与 `.tabs button.active` 同屏不冲突。

- [ ] **Step 3: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py   # 确认合规 OK
```

Expected: 全绿；合规 OK。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/theme.css
git commit -m "style: 设置面板、动效与可访问性收尾"
```

---

### Task 5: 最终验收、执行记录与推送

**Files:**
- Modify: `docs/superpowers/plans/2026-08-18-frontend-visual-redesign-plan.md`（追加执行记录 As-Built）
- 不动其他文件

- [ ] **Step 1: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全部通过（check OK / lint 零错 / typecheck Success / test 29 passed / build 成功）。

- [ ] **Step 2: 视觉冒烟 + 截图对比**

1. 启动后端：`cd backend && (./run.sh &)` 并 `sleep 4`
2. 启动前端：`cd frontend && (npm run dev &)` 并 `sleep 4`
3. 用 browser-use 或 curl 冒烟：访问 `http://localhost:5173`，确认 4 个页面（看板/持仓/新闻/设置）可切换、无控制台报错
4. 截图确认视觉签名三要素：①行情卡整卡红涨绿跌微染 ②左侧竖色条 ③大号等宽数字；以及状态带（琥珀连接点 + 时间戳）、琥珀金选中 tab、hover 抬升、reduced-motion（可用浏览器 devtools 模拟）
5. 收尾：`pkill -f "uvicorn app.main"; pkill -f vite`

- [ ] **Step 3: 执行记录（As-Built）**

在计划文档末尾追加 As-Built 表，记录 4 个任务的 commit hash、验证结果，以及以下已知偏差/事实：
- ECharts canvas 不支持 CSS var，Sparkline 用 getComputedStyle 读取 `--up`/`--down`
- Dashboard 状态带新增时间戳（60s 轮询），数据源静态文案"源: 新浪·腾讯"（项目固定双源）
- 涨跌类名通过 PriceCard `up` 布尔 → `price-card up/down` 类驱动微染（CSS 伪元素仅能实现竖条，微染底色需类名，故允许这一处 TSX 类名改动）
- 字体经 @fontsource latin 子集引入，离线可用
- 若构建出现 chunk 体积提示，属既有问题（MVP 遗留），不影响交付

- [ ] **Step 4: 提交并推送**

```bash
git add docs/superpowers/plans/2026-08-18-frontend-visual-redesign-plan.md
git commit -m "docs: 视觉重设计计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 5: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。
