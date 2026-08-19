# 看板大屏化设计文档（多维数据大屏）

- 日期：2026-08-18
- 状态：设计已获用户认可（Part 1-2 分节确认）
- 背景：当前看板为自选行情卡片网格（"单纯一个块"），需改为多维数据大屏

## 1. 目标

1. Dashboard（看板）页改造为**数据大屏布局**（保留导航，宽屏高密度图表矩阵）
2. 大屏包含 **7 个维度模块**：A 大盘指数、B 板块涨跌排行、C 板块资金流向、D 重点板块走势图（涨幅前三+跌幅前三）、E 自选实时行情、F 新闻快讯、G 涨跌家数/市场温度
3. 数据源统一用**东财公开接口**（已验证可行），现有行情（新浪/腾讯）/新闻（东财）保留

## 2. 非目标（明确不做）

- 不做独立全屏无导航的大屏模式（用户选 A：保留导航，看板页大屏化）
- 不做可配置板块/自定义布局（用户明确 D=涨幅前三+跌幅前三）
- 不改自选页/新闻页/设置页（仅改 Dashboard 页 + 后端新增板块服务）
- 不做移动端优化（大屏以宽屏为主，响应式降级即可）
- 不引入新的前端框架（继续 React + ECharts）
- 只读红线不变；无任何交易功能

## 3. 大屏布局

```
┌────────────────────────────────────────────────────────────────┐
│ 状态条（连接+时间）                                              │
├────────────────────────────────────────────────────────────────┤
│ A. 大盘指数区：上证 | 深证 | 创业板（点位+涨跌%+迷你走势）        │
│ G. 市场温度条：上涨 xxx 家 | 下跌 xxx 家（涨跌比例条）            │
├────────────────┬──────────────────────────┬───────────────────┤
│ B. 板块涨跌排行  │  D. 重点板块走势图（主区）  │  C. 板块资金流向    │
│  涨幅榜前5      │   涨幅前三 + 跌幅前三        │  主力净流入 TOP10   │
│  跌幅榜前5      │   每个：日K + 成交量         │  （净流入/净流出）   │
│  （含领涨/领跌股）│   （6 块大图，近 60 日）     │                  │
├────────────────┴──────────────────────────┴───────────────────┤
│ E. 自选行情（精简横排卡片，滚动）          │  F. 新闻快讯（滚动）  │
└────────────────────────────────────────────────────────────────┘
```

**布局原则**：深色金融大屏风格（沿用墨蓝黑 + 红涨绿跌 + 等宽数字）；中部 D 主图区面积最大；A/G 顶部指标带；B/C 侧边副区；E/F 底部信息流。

## 4. 数据源与后端

### 4.1 新增 `backend/app/market/sector.py`（东财公开接口）

| 函数 | 东财接口 | 返回 |
|---|---|---|
| `fetch_indices(client)` | `push2.eastmoney.com/api/qt/stock/get`（1.000001/0.399001/0.399006） | 3 个指数（code/name/price/high/low/open/prev_close/change/change_pct） |
| `fetch_sector_board(client)` | `push2.eastmoney.com/api/qt/clist/get?fs=m:90+t:2` | 板块列表（secid=90.BKxxxx、name、change_pct f3、fund_flow f62、up/down 家数 f104/105、leader 领涨股） |
| `fetch_sector_kline(client, secid)` | `push2his.eastmoney.com/api/qt/stock/kline/get?secid=90.BKxxxx&klt=101` | 日K 列表（date/open/close/high/low/volume/amount，近 60 日） |

- 解析器独立（东财 JSON → 领域模型），含异常兜底（网络失败返回空 + 上次缓存）
- 指数解析：f43 最新价/100、f44 最高、f45 最低、f46 开盘、f60 昨收、f169 涨跌额/100、f170 涨跌幅/100（东财报价为 ×100 整数，需 /100）

### 4.2 聚合快照 API `GET /api/dashboard`

```json
{
  "indices": [{"code","name","price","change","change_pct","high","low","open","prev_close"}],
  "market": {"up": 2000, "down": 1500},
  "sectors": {
    "top_gainers": [{"secid","name","change_pct","fund_flow","leader"}],
    "top_losers": [...],
    "fund_flow": [{"secid","name","fund_flow"}]   // 主力净流入 TOP10
  },
  "kline": {
    "top3_gainers": [{"secid","name","klines":[[date,open,close,high,low,volume,amount],...]}],
    "top3_losers": [...]
  }
}
```

### 4.3 DashboardService + TTL 缓存（30s）

- 新增 `backend/app/market/dashboard.py`：`DashboardService`，`get_snapshot() -> dict` 带 30s TTL 缓存；异常时返回上次成功快照（优雅降级）
- `/api/dashboard` 路由调用它
- 前端每 30s 拉取一次快照

## 5. 前端（Dashboard 大屏重构）

| 文件 | 改动 |
|---|---|
| `frontend/src/pages/Dashboard.tsx` | 重写为大屏布局（CSS grid：顶部指标带 + 中部 D + 两侧 B/C + 底部 E/F） |
| 新增 `frontend/src/components/SectorKlineChart.tsx` | ECharts 日K candlestick + 成交量柱（双轴）——D 模块 6 块大图 |
| 新增 `frontend/src/components/FundFlowChart.tsx` | ECharts 主力净流入条形图（红涨绿跌）——C 模块 |
| 新增 `frontend/src/components/IndexMiniChart.tsx` | 指数迷你走势线——A 模块 |
| `frontend/src/api/client.ts` | 新增 `getDashboard()`（`/api/dashboard`） |
| `frontend/src/theme.css` | 大屏布局样式（大屏 grid、排行表格、温度条） |

- 大屏数据每 30s `getDashboard()` 刷新（独立于自选/新闻的 store/WS 实时流）
- D 每图近 60 日K线 + 成交量；涨幅前三用红系、跌幅前三用绿系（A股红涨绿跌）
- 排行表格用等宽数字；温度条为涨跌家数比例条
- 图表组件遵循现有 Sparkline 模式（echarts.init + useEffect 清理 dispose + prefers-reduced-motion）

## 6. 约束与合规

- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`make check` 必须 OK
- **工具链**：ruff/yapf/mypy/eslint/prettier 全绿；`make test` 既有 26 + 新增 sector/dashboard 用例全绿；`make build` 成功
- **数据源**：仅东财公开接口；解析器容错（字段缺失/网络异常不崩溃）
- **命令**：一律 `backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- 新代码 Google docstring；commit 用 `feat:`（大屏）/ `chore:`（数据源）
- 板块排行动态取东财行业板块；若榜首为超冷门细分板块，按"板块含股票数 ≥ 阈值"过滤（实现时定阈值并记录）

## 7. 验收标准

1. `make check/lint/typecheck/test/build` 全绿（含新增 sector 解析器测试、`/api/dashboard` 测试）
2. `/api/dashboard` 返回完整快照（指数/家数/板块排行/资金/K线），30s TTL 生效，异常降级不 500
3. Dashboard 大屏渲染：3 指数卡 + 温度条 + 板块涨跌排行 + 资金流 TOP10 + 6 块板块K线图（涨幅前三/跌幅前三）+ 自选横排 + 新闻滚动
4. 前端每 30s 自动刷新；ECharts 图渲染正常（K线/成交量/条形/迷你线）；卸载清理无泄漏
5. 手动冒烟：启动前后端，看板页大屏显示全部 7 模块

## 8. 参考

- 现状：`frontend/src/pages/Dashboard.tsx`（卡片网格）、`market/service.py`（新浪/腾讯行情）、ECharts 已有（Sparkline）
- 东财接口实测：指数 `stock/get`、板块 `clist/get`（含资金 f62/家数 f104）、板块K线 `kline/get` 均可用
