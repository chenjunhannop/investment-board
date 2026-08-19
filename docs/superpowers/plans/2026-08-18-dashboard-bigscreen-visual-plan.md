# 看板大屏视觉重做实施计划（DataV 规范）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按数据大屏（DataV）设计规范重做 Dashboard 视觉层：深色渐变背景、模块发光边框 + 四角角标、顶部大标题区、超大等宽数字、数字跳动/轮播动效、对称三分区布局。后端与数据层零改动。

**Architecture:** 纯前端重做。新增 `BigScreenPanel` 组件（发光边框 + 四角角标 + 标题栏，所有大屏模块统一容器）与 `useCountUp` hook（数字跳动）；`theme.css` 重构大屏视觉体系（背景渐变/网格/光晕/边框角标/标题/超大数字/动效/reduced-motion）；`Dashboard.tsx` 重构为对称三分区布局并接入动效与轮播。

**Tech Stack:** React 18 + TS + ECharts（已有图表组件复用）、CSS（theme.css 单文件）、zustand

## Global Constraints

- 只改：`frontend/src/pages/Dashboard.tsx`、`frontend/src/theme.css`、新增 `frontend/src/components/BigScreenPanel.tsx`、新增 `frontend/src/hooks/useCountUp.ts`（后端零改动）
- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK
- **工具链**：`cd frontend && npm run lint && npm run format:check && npm run build` 全绿；后端 `make test` 30 passed 保持；`make check` OK
- 命令：前端 `cd frontend && npm run ...`；后端验证用 `make test`
- 新代码 Google docstring（如 hook）；commit 用 `style:`（视觉）/ `feat:`（hook/组件）
- 动效全部尊重 `@media (prefers-reduced-motion: reduce)`（用 CSS 的在此关闭；JS 的用 `matchMedia` 判断）
- ECharts 组件（SectorKlineChart/FundFlowChart/IndexMiniChart）**不改**，仅被新容器包裹
- `useCountUp` 仅浏览器环境（`requestAnimationFrame`），无 SSR 需求
- 布局一屏展示（16:9 宽屏优先，响应式降级保留）

---

### Task 1: 基础组件 BigScreenPanel + useCountUp hook

**Files:**
- Create: `frontend/src/components/BigScreenPanel.tsx`
- Create: `frontend/src/hooks/useCountUp.ts`

**Interfaces:**
- Produces: `BigScreenPanel({title, children, className?})`（发光边框 + 四角角标 + 标题栏容器）；`useCountUp(value, duration=300) -> number`

- [ ] **Step 1: 创建 BigScreenPanel.tsx**

```tsx
import type { ReactNode } from 'react';

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function BigScreenPanel({ title, children, className = '' }: Props) {
  return (
    <section className={`bs-panel ${className}`}>
      <span className="bs-corner tl" />
      <span className="bs-corner tr" />
      <span className="bs-corner bl" />
      <span className="bs-corner br" />
      <h3 className="bs-panel-title">{title}</h3>
      <div className="bs-panel-body">{children}</div>
    </section>
  );
}
```

- [ ] **Step 2: 创建 useCountUp.ts**

```ts
import { useEffect, useRef, useState } from 'react';

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

export function useCountUp(value: number, duration = 300): number {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(value);
      prevRef.current = value;
      return;
    }
    const from = prevRef.current;
    if (from === value) {
      return;
    }
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min((t - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setDisplay(from + (value - from) * eased);
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        prevRef.current = value;
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return display;
}
```

- [ ] **Step 3: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/BigScreenPanel.tsx frontend/src/hooks/useCountUp.ts
git commit -m "feat: 大屏面板容器与数字跳动 hook"
```

---

### Task 2: theme.css 大屏视觉体系

**Files:**
- Modify: `frontend/src/theme.css`（重构/新增大屏视觉区块）

**Interfaces:**
- Consumes: 现有 `--bg/--panel/--border/--text/--muted/--accent/--up/--down/--font-data/--font-body/--radius`
- Produces: 大屏背景/边框角标/标题区/超大数字/动效 CSS

- [ ] **Step 1: 追加/替换大屏视觉 CSS（theme.css 末尾）**

将现有 `.bigscreen-*` 区块替换为以下完整大屏体系（保留 `.news-feed`/`.self-strip .grid` 等已有效样式，其余替换）：

```css
/* ==== 大屏（DataV 风格）视觉体系 ==== */
.bigscreen {
  /* 深色渐变大屏背景 + 顶部光晕 + 网格纹理 */
  background:
    radial-gradient(ellipse at 50% -10%, rgba(212, 169, 72, 0.1), transparent 60%),
    linear-gradient(180deg, #0a1128 0%, #0d1520 60%, #0b1220 100%);
  min-height: 100vh;
  margin: -16px;
  padding: 16px 20px;
}
/* 网格纹理叠加 */
.bigscreen::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 44px 44px;
}

/* 顶部大标题区 */
.bs-header {
  position: relative;
  text-align: center;
  margin-bottom: 14px;
}
.bs-header h1 {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.2em;
  margin: 0;
  color: var(--text);
}
.bs-header h1::after {
  content: '';
  display: block;
  margin: 8px auto 0;
  width: 260px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
}
.bs-header-time {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  font-family: var(--font-data);
  font-size: 14px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.bs-header-conn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  color: var(--down);
  font-variant-numeric: tabular-nums;
}
.bs-header-conn.on {
  color: var(--up);
  animation: pulse 2.4s ease-in-out infinite;
}

/* 大屏面板：发光边框 + 四角角标 */
.bs-panel {
  position: relative;
  background: rgba(19, 26, 35, 0.6);
  border: 1px solid rgba(76, 120, 255, 0.18);
  border-radius: 4px;
  padding: 12px 14px;
  box-shadow: inset 0 0 24px rgba(76, 120, 255, 0.05);
}
.bs-corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(212, 169, 72, 0.7);
}
.bs-corner.tl {
  top: -1px;
  left: -1px;
  border-right: none;
  border-bottom: none;
  border-top-left-radius: 4px;
}
.bs-corner.tr {
  top: -1px;
  right: -1px;
  border-left: none;
  border-bottom: none;
  border-top-right-radius: 4px;
}
.bs-corner.bl {
  bottom: -1px;
  left: -1px;
  border-right: none;
  border-top: none;
  border-bottom-left-radius: 4px;
}
.bs-corner.br {
  bottom: -1px;
  right: -1px;
  border-left: none;
  border-top: none;
  border-bottom-right-radius: 4px;
}
.bs-panel-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  padding-left: 10px;
  border-left: 3px solid var(--accent);
  position: relative;
}
.bs-panel-title::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -4px;
  width: 60%;
  height: 1px;
  background: linear-gradient(90deg, rgba(212, 169, 72, 0.6), transparent);
}
.bs-panel-body {
  position: relative;
}

/* 指数超大数字 */
.index-card {
  background: rgba(19, 26, 35, 0.6);
  border: 1px solid rgba(76, 120, 255, 0.18);
  border-radius: 4px;
  padding: 12px 14px;
}
.index-card .index-name {
  font-size: 13px;
  color: var(--muted);
}
.index-card .index-price {
  font-family: var(--font-data);
  font-size: 40px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin: 4px 0;
  line-height: 1.1;
}
.index-card .index-change {
  font-family: var(--font-data);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

/* 市场温度条 */
.market-temp {
  background: rgba(19, 26, 35, 0.6);
  border: 1px solid rgba(76, 120, 255, 0.18);
  border-radius: 4px;
  padding: 12px 14px;
}
.temp-title {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 8px;
}
.temp-bar {
  height: 12px;
  border-radius: 6px;
  background: var(--border);
  overflow: hidden;
}
.temp-up {
  height: 100%;
  background: var(--up);
  transition: width 400ms ease;
}
.temp-nums {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-family: var(--font-data);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

/* 顶部指标带 + 对称三分区 + 底部 */
.bs-indices {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.bs-main {
  display: grid;
  grid-template-columns: 1.1fr 2fr 1.1fr;
  gap: 12px;
  margin-bottom: 12px;
}
.bs-left,
.bs-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.kline-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.kline-card {
  background: rgba(10, 15, 22, 0.7);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px;
}
.kline-title {
  font-family: var(--font-data);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}
.sector-rank {
  font-size: 12px;
}
.bs-bottom {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 12px;
}
.self-strip .grid {
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
}
.news-feed {
  max-height: 320px;
  overflow-y: auto;
}
.news-line {
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  line-height: 1.5;
}
.news-line:last-child {
  border-bottom: none;
}

/* 状态点脉冲 */
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

/* 底部自选/新闻滚动（marquee） */
.marquee {
  overflow: hidden;
  white-space: nowrap;
}
.marquee-inner {
  display: inline-block;
  animation: marquee 30s linear infinite;
}
@keyframes marquee {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

/* 响应式 + reduced-motion */
@media (max-width: 1100px) {
  .bs-indices {
    grid-template-columns: repeat(2, 1fr);
  }
  .bs-main {
    grid-template-columns: 1fr;
  }
  .bs-bottom {
    grid-template-columns: 1fr;
  }
  .kline-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .marquee-inner {
    animation: none;
  }
}
```

> 说明：`.bigscreen` 容器 `margin: -16px` 抵消 `.app` 的 padding，使大屏背景铺满；保留 `status-bar` 原样式（大屏内嵌）。

- [ ] **Step 2: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/theme.css
git commit -m "style: 大屏视觉体系（渐变背景/发光边框/角标/超大数字/动效）"
```

---

### Task 3: Dashboard.tsx 大屏重构（对称三分区 + 动效 + 轮播）

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

**Interfaces:**
- Consumes: `BigScreenPanel`、`useCountUp`、现有 3 个 ECharts 组件、`getDashboard`、store（quotes/news）
- Produces: 大屏 7 模块 + 大标题区 + 动效 + 轮播

- [ ] **Step 1: 重写 Dashboard.tsx**

```tsx
import { useEffect, useState } from 'react';
import { getDashboard } from '../api/client';
import type { DashboardData } from '../api/client';
import BigScreenPanel from '../components/BigScreenPanel';
import FundFlowChart from '../components/FundFlowChart';
import IndexMiniChart from '../components/IndexMiniChart';
import PriceCard from '../components/PriceCard';
import SectorKlineChart from '../components/SectorKlineChart';
import { useCountUp } from '../hooks/useCountUp';
import { useApp } from '../store';

const DASHBOARD_REFRESH_MS = 30000;

function IndexCard({ index }: { index: DashboardData['indices'][number] }) {
  const price = useCountUp(index.price);
  const up = index.change_pct >= 0;
  const color = up ? 'var(--up)' : 'var(--down)';
  return (
    <div className="index-card">
      <div className="index-name">{index.name}</div>
      <div className="index-price" style={{ color }}>
        {price.toFixed(2)}
      </div>
      <div className="index-change" style={{ color }}>
        {up ? '+' : ''}
        {index.change_pct.toFixed(2)}%
      </div>
      <IndexMiniChart
        points={[index.prev_close, index.open, index.price]}
        color={up ? '#e5484d' : '#2e9e6b'}
      />
    </div>
  );
}

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const news = useApp((s) => s.news);
  const connected = useApp((s) => s.connected);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await getDashboard();
        if (alive) setDash(d);
      } catch {
        /* 保留上次快照 */
      }
    };
    load();
    const t = setInterval(load, DASHBOARD_REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);
  const stamp = now.toLocaleString('zh-CN', { hour12: false });
  const upCount = useCountUp(dash?.market.up ?? 0);
  const downCount = useCountUp(dash?.market.down ?? 0);
  const total = upCount + downCount || 1;
  return (
    <div className="page bigscreen">
      {/* 顶部大标题区 */}
      <div className="bs-header">
        <span className={`bs-header-conn ${connected ? 'on' : ''}`}>
          ● {connected ? '实时连接' : '连接断开'}
        </span>
        <h1>市场数据中心</h1>
        <span className="bs-header-time">{stamp}</span>
      </div>
      {/* A + G：指数带 + 市场温度 */}
      <div className="bs-indices">
        {dash?.indices.map((ix) => <IndexCard key={ix.code} index={ix} />)}
        <div className="market-temp">
          <div className="temp-title">市场温度</div>
          <div className="temp-bar">
            <div className="temp-up" style={{ width: `${(upCount / total) * 100}%` }} />
          </div>
          <div className="temp-nums">
            <span style={{ color: 'var(--up)' }}>↑ {Math.round(upCount)}</span>
            <span style={{ color: 'var(--down)' }}>↓ {Math.round(downCount)}</span>
          </div>
        </div>
      </div>
      {/* 对称三分区：左排行 / 中K线主视觉 / 右资金 */}
      <div className="bs-main">
        <div className="bs-left">
          <BigScreenPanel title="板块涨幅榜">
            <table className="tbl sector-rank">
              <tbody>
                {dash?.sectors.top_gainers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--up)' }}>+{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </BigScreenPanel>
          <BigScreenPanel title="板块跌幅榜">
            <table className="tbl sector-rank">
              <tbody>
                {dash?.sectors.top_losers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--down)' }}>{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </BigScreenPanel>
        </div>
        <BigScreenPanel title="重点板块走势（涨幅前三 / 跌幅前三）">
          <div className="kline-grid">
            {dash?.kline.top3_gainers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--up)' }}>
                  {k.name} +{k.change_pct.toFixed(2)}%
                </div>
                <SectorKlineChart name={k.name} klines={k.klines} up />
              </div>
            ))}
            {dash?.kline.top3_losers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--down)' }}>
                  {k.name} {k.change_pct.toFixed(2)}%
                </div>
                <SectorKlineChart name={k.name} klines={k.klines} up={false} />
              </div>
            ))}
          </div>
        </BigScreenPanel>
        <div className="bs-right">
          <BigScreenPanel title="板块资金流向（主力净流入 TOP）">
            <FundFlowChart data={dash?.sectors.fund_flow ?? []} />
          </BigScreenPanel>
        </div>
      </div>
      {/* 底部：E 自选滚动 + F 新闻 */}
      <div className="bs-bottom">
        <BigScreenPanel title="自选实时行情" className="self-strip">
          <div className="marquee">
            <div className="marquee-inner">
              {Object.values(quotes).map((q) => (
                <div key={q.code} className="cell" style={{ display: 'inline-block', marginRight: 10 }}>
                  <PriceCard q={q} />
                </div>
              ))}
            </div>
          </div>
        </BigScreenPanel>
        <BigScreenPanel title="新闻快讯">
          <div className="news-feed">
            {news.slice(0, 12).map((n) => (
              <div key={n.id} className="news-line">
                <span className="muted">{n.source}</span> {n.title}
              </div>
            ))}
          </div>
        </BigScreenPanel>
      </div>
    </div>
  );
}
```

- 注：`connected` 移入 `bs-header-conn`（左上连接状态点，A股红涨绿跌配色：连接正常用 `--up` 红、断开用 `--down` 绿）；`bs-header-time` 秒级更新（1s interval）

- [ ] **Step 2: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "style: 看板大屏对称三分区布局（大标题/动效/轮播）"
```

---

### Task 4: 全量验收、视觉冒烟、As-Built 与推送

**Files:**
- Modify: `README.md`（大屏视觉说明）、`docs/superpowers/plans/2026-08-18-dashboard-bigscreen-visual-plan.md`（As-Built）

- [ ] **Step 1: README 更新**

看板功能说明补充：数据大屏视觉（深色渐变/发光边框/四角角标/超大数字/数字跳动/数据轮播），DataV 风格。

- [ ] **Step 2: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（test 30 passed，后端零改动）。

- [ ] **Step 3: 视觉冒烟（headless Chrome 验证大屏视觉要素）**

1. 清理残留进程；`cd backend && (./run.sh &)` + `cd frontend && (npm run dev &)`，sleep 6
2. headless Chrome 加载 `localhost:5173`，用 CDP 断言：
   - `.bigscreen` 背景含 `linear-gradient`（深色渐变）与 `radial-gradient`（光晕）
   - `.bs-header h1` 存在且文本"市场数据中心"；`.bs-header-time` 秒级时间
   - `.bs-panel` 存在（≥5 个）且 `.bs-corner` 四角角标渲染（`bs-corner tl/tr/bl/br` 各存在）
   - `.index-price` 计算样式 `font-size: 40px` + IBM Plex Mono + tabular-nums
   - `.temp-up`/`.temp-nums` 渲染（涨跌家数）
   - `.marquee-inner` animation 存在
   - 截图保存供用户查看
3. `pkill -f "uvicorn app.main"; pkill -f vite`

- [ ] **Step 4: As-Built + 推送**

计划文档末尾追加 As-Built 表（Task 1-3 commit hash、验证结果、偏差——含：状态条移入大标题区、角标实现用 4 个 span、`margin:-16px` 铺满背景、reduced-motion 处理、if 删除 status-bar 的取舍）。然后：

```bash
git add README.md docs/superpowers/plans/2026-08-18-dashboard-bigscreen-visual-plan.md
git commit -m "docs: 大屏视觉重做计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 5: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。

---

## As-Built 执行记录（Task 4 收尾）

> 执行日期：2026-08-19 · 分支：main · 范围：Task 1-3 实现 + Task 4 全量验收/视觉冒烟/推送

### Task 1-3 Commit

| Task | Commit | Message | 状态 |
|------|--------|---------|------|
| 1 | `47f957a` | feat: 大屏面板容器与数字跳动 hook | ✅ |
| 2 | `a597ac0` | style: 大屏视觉体系（渐变背景/发光边框/角标/超大数字/动效） | ✅ |
| 3 | `e2f21f4` | style: 看板大屏对称三分区布局（大标题/动效/轮播） | ✅ |

### Task 4 验证结果

| 检查 | 命令 | 结果 |
|------|------|------|
| 合规静态检查 | `make check` | ✅ OK（未发现交易语义代码） |
| 双端 lint + 格式 | `make lint` | ✅ ruff / yapf / eslint / prettier 全绿 |
| 双端类型检查 | `make typecheck` | ✅ mypy / tsc 通过 |
| 后端测试 | `make test` | ✅ 30 passed（后端零改动） |
| 前端构建 | `make build` | ✅ Vite 构建成功（chunk>500kB 提示，非阻塞） |
| 视觉冒烟 | headless Chrome + CDP | ✅ 20/20 断言通过，截图 `/tmp/bs_final.png`（1920×937） |

### 视觉冒烟断言明细（20/20）

- **a** `.bigscreen` 背景含 `linear-gradient`（深色渐变）与 `radial-gradient`（顶部光晕）✅
- **b** `.bs-header h1` = “市场数据中心”；`.bs-header-time`（秒级时钟）与 `.bs-header-conn`（连接状态）存在 ✅
- **c** `.bs-panel` = 6 个（≥5）；`.bs-corner.tl/tr/bl/br` 各 6 个（共 24 角标）✅
- **d** `.index-price` 计算样式 `font-size: 40px` + font-family 含 IBM Plex Mono + `font-variant-numeric: tabular-nums`，渲染数值（如 3912.17）✅
- **e** `.temp-up`（宽度 89.47px）与 `.temp-nums`（↑664 ↓976）渲染；`.marquee-inner` `animation-name: marquee`（30s linear infinite），轮播卡 105 条 ✅

> 注：冒烟时后端外部数据源存在热身期抖动（首帧快照可能 indices 空或 market 0/0），脚本预热后端缓存并轮询等待 `.index-card` 出现（最长 35s）后断言；实测单次 run 即 20/20 通过。

### 偏差清单（与计划对照）

| # | 计划 | 实际实现 | 说明 |
|---|------|----------|------|
| 1 | 独立 `status-bar` 条 | 连接状态移入 `bs-header-conn`（左上，连接正常 `--up` 红/断开 `--down` 绿 + pulse），秒级时间移入 `bs-header-time`（右上，1s interval） | 状态条并入大标题区，大屏顶部更简洁 |
| 2 | 角标（未限定实现方式） | `BigScreenPanel` 用 4 个 `<span className="bs-corner tl/tr/bl/br">`（非伪元素） | 单元素伪元素仅能覆盖 2 个角，4 span 直白可控；与 Task 1 代码一致 |
| 3 | 大屏背景铺满 | `.bigscreen { margin: -16px; padding: 16px 20px }` 抵消 `.app` 的 `padding: 16px` | 深色渐变背景铺满视口（全屏大屏感） |
| 4 | 动效尊重 reduced-motion | CSS：全局 `@media (prefers-reduced-motion: reduce)` 收敛动画/过渡并禁用 `.marquee-inner`；JS：`useCountUp` 用 `matchMedia('(prefers-reduced-motion: reduce)')` 命中时直跳目标值 | 双端都处理 |
| 5 | status-bar 保留与否的取舍 | **保留** `.status-bar` 原始 CSS（90-114 行）及大屏块内 `.status-bar .dot.on` 脉冲规则，未删除 | 该 class 已无任何 TSX 使用（纯保留死代码）；CSS 无副作用，删除风险 > 收益，故按保留处理 |

### 遗留事项

- 后端 `DashboardService.get_snapshot()` 中 `fetch_indices` 与 `fetch_sector_board` 独立抓取外部数据源，数据源热身/抖动期可能出现部分空快照（indices 空或 market 0/0），前端指数卡/市场温度会延迟到下一次 30s 刷新才完整。非本次前端重做引入，属外部数据源预期行为（后端已优雅降级，不崩溃）。
