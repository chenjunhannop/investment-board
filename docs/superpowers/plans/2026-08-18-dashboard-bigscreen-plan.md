# 看板大屏化实施计划（多维数据大屏）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Dashboard 从卡片网格改造为多维数据大屏（7 模块：指数/涨跌排行/资金流/重点板块K线/自选/新闻/涨跌家数），后端新增东财板块服务 + `/api/dashboard` 聚合快照（30s TTL），前端新增 ECharts 图表组件。

**Architecture:** 后端新增 `market/sector.py`（东财指数/板块列表/板块K线 + 解析器 + 冷门过滤）与 `market/dashboard.py`（DashboardService 30s TTL 缓存聚合快照），`GET /api/dashboard` 返回全部大屏数据；前端 Dashboard 大屏重构 + 3 个 ECharts 组件（K线/资金流条形/指数迷你线），30s 轮询快照。

**Tech Stack:** Python 3.11 / FastAPI / httpx / pytest / respx、React 18 + TS + ECharts、ruff/yapf/mypy、eslint/prettier

## Global Constraints

- 只改：`backend/app/market/{sector,dashboard}.py`、`backend/app/api/routes.py`、`backend/app/main.py`、`backend/app/config.py`（如需）、`backend/tests/{test_sector,test_dashboard}.py`、`frontend/src/{pages/Dashboard,components/SectorKlineChart,components/FundFlowChart,components/IndexMiniChart,api/client,theme.css}.tsx|ts|css`、`README.md`、`docs/superpowers/plans/...`
- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK
- **测试**：既有 26 + 新增 sector/dashboard 用例全绿（≥26）
- `make check`（合规）OK；`make lint`（ruff/yapf/eslint/prettier）零错；`make typecheck`（mypy+tsc）通过；`make build` 成功
- 命令一律 `backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- 新代码 Google docstring（句末 ASCII `.`，ruff D 规则零错误）；commit 用 `feat:`（大屏）/ `chore:`
- 东财接口均公开，异常兜底（网络失败返回空 + 保留上次缓存，绝不 500）
- 东财报价为 ×100 整数，解析时 `/100` 转浮点；字段缺失用默认值
- **冷门过滤**：板块排行仅纳入 `f104 + f105 >= 10`（排除氨纶 1 股等超冷门）；板块名去除 `Ⅱ/Ⅲ` 后缀去重（保留首个，避免父子层级重复占位）
- ECharts 组件遵循现有 Sparkline 模式（`echarts.init` + `useEffect` 清理 `dispose` + 尊重 `prefers-reduced-motion`）

---

### Task 1: 后端东财板块服务（sector.py）

**Files:**
- Create: `backend/app/market/sector.py`
- Create: `backend/tests/test_sector.py`

**Interfaces:**
- Consumes: httpx.AsyncClient；`settings`
- Produces: `fetch_indices(client) -> list[dict]`、`fetch_sector_board(client) -> dict`（含 top_gainers/top_losers/fund_flow/market）、`fetch_sector_kline(client, secid) -> list[list]`

- [ ] **Step 1: 创建 sector.py**

```python
"""东财板块/指数数据服务（公开接口，含冷门过滤与异常兜底）.

数据来源为东方财富公开接口：大盘指数 stock/get、行业板块 clist/get、
板块日K kline/get。所有接口为只读公开数据，不涉及任何交易操作.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

INDEX_SECIDS = ["1.000001", "0.399001", "0.399006"]  # 上证/深证/创业板
SECTOR_LIST_URL = ("https://push2.eastmoney.com/api/qt/clist/get"
                   "?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3"
                   "&fs=m:90+t:2&fields=f2,f3,f12,f14,f62,f104,f105,f128,f140")
KLINE_URL = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
             "?fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
             "&klt=101&fqt=1&lmt=60&end=20500101")
MIN_STOCKS = 10  # 冷门过滤：板块含股数下限


def _num(value, scale=1.0, default=0.0) -> float:
    """把东财 ×100 整数或数值转为浮点，缺失用默认值.

    Args:
        value: 东财接口返回的数值（可能为 None）.
        scale: 缩放系数，默认 1.0（如指数报价需 /100）.
        default: 缺失时的默认值.

    Returns:
        缩放后的浮点值.
    """
    if value is None:
        return default
    try:
        return float(value) / scale
    except (TypeError, ValueError):
        return default


def _clean_name(name: str) -> str:
    """去除板块名 Ⅱ/Ⅲ 后缀用于去重.

    Args:
        name: 东财板块名，如 "股份制银行Ⅲ".

    Returns:
        去后缀后的名字，如 "股份制银行".
    """
    for suffix in ("Ⅲ", "Ⅱ"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def parse_indices(data: dict) -> list[dict]:
    """解析东财指数 stock/get 响应为指数快照列表.

    Args:
        data: 单只指数接口返回的 {"data": {...}} 字典.

    Returns:
        指数字典列表（code/name/price/high/low/open/prev_close/change/change_pct）.
    """
    d = data.get("data") or {}
    price = _num(d.get("f43"), 100.0)
    prev_close = _num(d.get("f60"), 100.0)
    return [{
        "code": d.get("f57", ""),
        "name": d.get("f58", ""),
        "price": price,
        "high": _num(d.get("f44"), 100.0),
        "low": _num(d.get("f45"), 100.0),
        "open": _num(d.get("f46"), 100.0),
        "prev_close": prev_close,
        "change": _num(d.get("f169"), 100.0),
        "change_pct": _num(d.get("f170"), 100.0),
    }]


def parse_sector_board(data: dict) -> dict:
    """解析东财板块列表响应，过滤冷门并去重父子层级.

    Args:
        data: clist/get 响应（{"data": {"diff": [...]}}）.

    Returns:
        {"top_gainers": [...], "top_losers": [...], "fund_flow": [...],
         "market": {"up": int, "down": int}}.
    """
    diff = (data.get("data") or {}).get("diff") or []
    seen: dict[str, dict] = {}
    market_up = market_down = 0
    for it in diff:
        up = int(it.get("f104") or 0)
        down = int(it.get("f105") or 0)
        market_up += up
        market_down += down
        if up + down < MIN_STOCKS:
            continue  # 冷门板块过滤
        raw_name = it.get("f14", "")
        name = _clean_name(raw_name)
        if name in seen:
            continue  # 父子层级去重
        seen[name] = {
            "secid": f"90.{it.get('f12', '')}",
            "name": raw_name,
            "change_pct": _num(it.get("f3"), 100.0),
            "fund_flow": _num(it.get("f62")),
            "leader": it.get("f128", ""),
            "leader_code": it.get("f140", ""),
            "stocks": up + down,
        }
    rows = list(seen.values())
    top_gainers = sorted(rows, key=lambda r: r["change_pct"], reverse=True)[:5]
    top_losers = sorted(rows, key=lambda r: r["change_pct"])[:5]
    fund_flow = sorted(rows, key=lambda r: r["fund_flow"], reverse=True)[:10]
    return {
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "fund_flow": fund_flow,
        "market": {"up": market_up, "down": market_down},
    }


def parse_sector_kline(data: dict) -> list[list]:
    """解析东财板块日K响应为 klines 列表.

    Args:
        data: kline/get 响应.

    Returns:
        [[date, open, close, high, low, volume, amount], ...] 近 60 日.
    """
    klines = (data.get("data") or {}).get("klines") or []
    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append([
                parts[0],
                float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]),
                float(parts[5]), float(parts[6]),
            ])
    return rows


async def fetch_indices(client: httpx.AsyncClient) -> list[dict]:
    """抓取上证/深证/创业板指数快照.

    Args:
        client: 共享 httpx 客户端.

    Returns:
        指数字典列表；任一失败时跳过该指数.
    """
    out = []
    for secid in INDEX_SECIDS:
        try:
            r = await client.get(
                f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}"
                "&fields=f43,f44,f45,f46,f57,f58,f60,f169,f170",
                headers={"Referer": "https://quote.eastmoney.com/"}, timeout=8)
            r.raise_for_status()
            parsed = parse_indices(r.json())
            if parsed:
                out.append(parsed[0])
        except Exception as e:
            logger.warning("抓取指数 %s 失败: %s", secid, e)
    return out


async def fetch_sector_board(client: httpx.AsyncClient) -> dict:
    """抓取行业板块排行（含资金/家数/领涨股，冷门过滤）.

    Args:
        client: 共享 httpx 客户端.

    Returns:
        parse_sector_board 结果；失败时返回空结构.
    """
    try:
        r = await client.get(SECTOR_LIST_URL,
                             headers={"Referer": "https://quote.eastmoney.com/"},
                             timeout=10)
        r.raise_for_status()
        return parse_sector_board(r.json())
    except Exception as e:
        logger.warning("抓取板块排行失败: %s", e)
        return {"top_gainers": [], "top_losers": [], "fund_flow": [],
                "market": {"up": 0, "down": 0}}


async def fetch_sector_kline(client: httpx.AsyncClient, secid: str) -> list[list]:
    """抓取单个板块近 60 日K线.

    Args:
        client: 共享 httpx 客户端.
        secid: 东财板块 secid，如 "90.BK1036".

    Returns:
        日K列表；失败时返回空列表.
    """
    try:
        r = await client.get(f"{KLINE_URL}&secid={secid}",
                             headers={"Referer": "https://quote.eastmoney.com/"},
                             timeout=8)
        r.raise_for_status()
        return parse_sector_kline(r.json())
    except Exception as e:
        logger.warning("抓取板块 %s K线失败: %s", secid, e)
        return []
```

- [ ] **Step 2: 创建 test_sector.py**

```python
"""东财板块/指数解析器的单元测试."""
from app.market.sector import (parse_indices, parse_sector_board,
                               parse_sector_kline)

INDEX = {"data": {"f43": 393086, "f44": 396114, "f45": 391708, "f46": 395212,
                  "f57": "000001", "f58": "上证指数", "f60": 399030,
                  "f169": -5944, "f170": -149}}


def test_parse_indices():
    """指数 ×100 整数正确转浮点."""
    r = parse_indices(INDEX)[0]
    assert r["name"] == "上证指数"
    assert r["price"] == 3930.86
    assert r["change_pct"] == -1.49


def test_parse_sector_board_filters_cold():
    """冷门板块（含股 < 10）被过滤，父子层级去重."""
    data = {"data": {"diff": [
        {"f12": "BK1", "f14": "银行", "f3": 90, "f62": 100, "f104": 37, "f105": 0, "f128": "招商银行", "f140": "600036"},
        {"f12": "BK2", "f14": "银行Ⅱ", "f3": 90, "f62": 100, "f104": 37, "f105": 0, "f128": "招商银行", "f140": "600036"},
        {"f12": "BK3", "f14": "氨纶", "f3": 356, "f62": 5, "f104": 1, "f105": 0, "f128": "", "f140": ""},
    ]}}
    r = parse_sector_board(data)
    names = [x["name"] for x in r["top_gainers"]]
    assert names == ["银行"]  # 氨纶被过滤，银行Ⅱ去重
    assert r["fund_flow"][0]["fund_flow"] == 100.0
    assert r["market"] == {"up": 75, "down": 0}


def test_parse_sector_kline():
    """K线字符串转结构化列表."""
    data = {"data": {"klines": [
        "2026-08-18,750.55,753.50,766.55,747.98,2809112,915286883.00"]}}
    r = parse_sector_kline(data)
    assert r[0][0] == "2026-08-18"
    assert r[0][2] == 753.50
    assert len(r[0]) == 7
```

- [ ] **Step 3: 验证**

```bash
backend/.venv/bin/pytest -q backend/tests/test_sector.py -v
backend/.venv/bin/ruff check backend/app/market/sector.py backend/tests/test_sector.py
backend/.venv/bin/mypy backend/app
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/market/sector.py backend/tests/test_sector.py
git commit -m "feat: 东财板块/指数/日K数据服务（含冷门过滤）"
```

---

### Task 2: DashboardService + /api/dashboard 聚合快照

**Files:**
- Create: `backend/app/market/dashboard.py`
- Modify: `backend/app/api/routes.py`（`/api/dashboard` 路由）
- Modify: `backend/app/main.py`（装配 DashboardService 到 app.state）
- Create: `backend/tests/test_dashboard.py`

**Interfaces:**
- Consumes: Task 1 的 `fetch_indices/fetch_sector_board/fetch_sector_kline`；httpx.AsyncClient
- Produces: `DashboardService(client).get_snapshot() -> dict`（30s TTL）；`GET /api/dashboard`

- [ ] **Step 1: 创建 dashboard.py**

```python
"""看板大屏聚合快照服务：合并指数/板块/资金/K线，30 秒 TTL 缓存."""
import logging
import time

import httpx

from app.market import sector

logger = logging.getLogger(__name__)

CACHE_TTL = 30.0


class DashboardService:
    """聚合大盘指数、板块排行、资金流与重点板块K线的大屏快照服务."""

    def __init__(self, client: httpx.AsyncClient, ttl: float = CACHE_TTL):
        """初始化快照服务.

        Args:
            client: 共享 httpx 客户端.
            ttl: 快照缓存有效期（秒），默认 30.
        """
        self._client = client
        self._ttl = ttl
        self._snapshot: dict = {}
        self._fetched_at: float = 0.0

    async def get_snapshot(self) -> dict:
        """返回大屏快照；缓存有效期内复用，过期或失败时降级保留上次.

        Returns:
            {"indices": [...], "market": {...}, "sectors": {...}, "kline": {...}}.
        """
        now = time.monotonic()
        if self._snapshot and now - self._fetched_at < self._ttl:
            return self._snapshot
        try:
            indices = await sector.fetch_indices(self._client)
            board = await sector.fetch_sector_board(self._client)
            top3_gainers = []
            for item in board["top_gainers"][:3]:
                top3_gainers.append({
                    "secid": item["secid"],
                    "name": item["name"],
                    "change_pct": item["change_pct"],
                    "klines": await sector.fetch_sector_kline(self._client,
                                                              item["secid"]),
                })
            top3_losers = []
            for item in board["top_losers"][:3]:
                top3_losers.append({
                    "secid": item["secid"],
                    "name": item["name"],
                    "change_pct": item["change_pct"],
                    "klines": await sector.fetch_sector_kline(self._client,
                                                              item["secid"]),
                })
            snapshot = {
                "indices": indices,
                "market": board["market"],
                "sectors": {
                    "top_gainers": board["top_gainers"],
                    "top_losers": board["top_losers"],
                    "fund_flow": board["fund_flow"],
                },
                "kline": {"top3_gainers": top3_gainers,
                          "top3_losers": top3_losers},
            }
            self._snapshot = snapshot
            self._fetched_at = now
            return snapshot
        except Exception as e:
            # 抓取失败时降级：若已有缓存则返回缓存，否则返回空结构
            logger.warning("刷新大屏快照失败: %s", e)
            if self._snapshot:
                return self._snapshot
            return {"indices": [], "market": {"up": 0, "down": 0},
                    "sectors": {"top_gainers": [], "top_losers": [],
                                "fund_flow": []},
                    "kline": {"top3_gainers": [], "top3_losers": []}}
```

- [ ] **Step 2: routes.py 新增 /api/dashboard**

```python
@router.get("/dashboard")
async def get_dashboard(request: Request):
    """返回看板大屏聚合快照.

    Args:
        request: FastAPI 请求，携带挂载了 dashboard 的 app.state.

    Returns:
        大屏快照（指数/板块/资金/K线）.
    """
    svc = request.app.state.dashboard
    if svc is None:
        return {"indices": [], "market": {"up": 0, "down": 0},
                "sectors": {"top_gainers": [], "top_losers": [],
                            "fund_flow": []},
                "kline": {"top3_gainers": [], "top3_losers": []}}
    return await svc.get_snapshot()
```

- [ ] **Step 3: main.py 装配 DashboardService**

在 lifespan 中创建并挂载：

```python
from app.market.dashboard import DashboardService
# ...
    dashboard = DashboardService(client)
    app.state.dashboard = dashboard
```

（保留现有 market/news/scheduler 装配。）

- [ ] **Step 4: 创建 test_dashboard.py**

```python
"""看板大屏快照服务的单元测试."""
from unittest.mock import AsyncMock, patch

import pytest

from app.market.dashboard import DashboardService


@pytest.mark.asyncio
async def test_dashboard_ttl_and_degrade():
    """TTL 内复用缓存；失败时降级保留上次快照."""
    client = AsyncMock()
    svc = DashboardService(client, ttl=30.0)
    with patch("app.market.sector.fetch_indices", AsyncMock(return_value=[{"name": "上证指数"}])) as fi, \
         patch("app.market.sector.fetch_sector_board",
               AsyncMock(return_value={"top_gainers": [{"secid": "90.BK1", "name": "A", "change_pct": 1.0}],
                                       "top_losers": [], "fund_flow": [],
                                       "market": {"up": 1, "down": 0}})) as fb, \
         patch("app.market.sector.fetch_sector_kline", AsyncMock(return_value=[["2026-08-18", 1, 2, 3, 4, 5, 6]])) as fk:
        snap1 = await svc.get_snapshot()
        assert snap1["indices"][0]["name"] == "上证指数"
        assert len(snap1["kline"]["top3_gainers"]) == 1
        snap2 = await svc.get_snapshot()  # TTL 内命中缓存，不重新抓取
        assert fi.await_count == 1
        assert fb.await_count == 1
        assert snap2 == snap1
        # 模拟后续失败：清缓存后强制失败，应返回上次快照
        svc._fetched_at = 0
        svc._snapshot = snap1
        fb.side_effect = Exception("network")
        snap3 = await svc.get_snapshot()
        assert snap3 == snap1
```

- [ ] **Step 5: 验证**

```bash
backend/.venv/bin/pytest -q backend/tests/test_dashboard.py -v
backend/.venv/bin/pytest -q
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/market/dashboard.py backend/app/api/routes.py backend/app/main.py backend/tests/test_dashboard.py
git commit -m "feat: 看板大屏聚合快照 API（30s TTL 缓存）"
```

---

### Task 3: 前端图表组件 + client

**Files:**
- Create: `frontend/src/components/SectorKlineChart.tsx`、`frontend/src/components/FundFlowChart.tsx`、`frontend/src/components/IndexMiniChart.tsx`
- Modify: `frontend/src/api/client.ts`（`getDashboard` + Dashboard 类型）

**Interfaces:**
- Consumes: `/api/dashboard` 响应类型
- Produces: `SectorKlineChart({name, klines, color})`、`FundFlowChart({data})`、`IndexMiniChart({points, color})`

- [ ] **Step 1: client.ts 新增 Dashboard 类型与 API**

```ts
export interface IndexSnapshot {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  high: number;
  low: number;
  open: number;
  prev_close: number;
}
export interface SectorRow {
  secid: string;
  name: string;
  change_pct: number;
  fund_flow: number;
  leader: string;
  leader_code: string;
  stocks: number;
}
export interface SectorKline {
  secid: string;
  name: string;
  change_pct: number;
  klines: (string | number)[][];
}
export interface DashboardData {
  indices: IndexSnapshot[];
  market: { up: number; down: number };
  sectors: {
    top_gainers: SectorRow[];
    top_losers: SectorRow[];
    fund_flow: SectorRow[];
  };
  kline: { top3_gainers: SectorKline[]; top3_losers: SectorKline[] };
}
export const getDashboard = () => json<DashboardData>('/api/dashboard');
```

- [ ] **Step 2: 创建 SectorKlineChart.tsx**

```tsx
import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface Props {
  name: string;
  klines: (string | number)[][];
  up: boolean;
}

export default function SectorKlineChart({ name, klines, up }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const dates = klines.map((k) => k[0] as string);
    const values = klines.map((k) => [
      Number(k[1]),
      Number(k[2]),
      Number(k[3]),
      Number(k[4]),
    ]);
    const vols = klines.map((k) => Number(k[5]));
    const color = up ? '#e5484d' : '#2e9e6b';
    chart.setOption({
      grid: { left: 44, right: 10, top: 10, bottom: 24 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates, show: false },
      yAxis: [{ type: 'value', scale: true, show: false }, { type: 'value', show: false }],
      series: [
        {
          type: 'candlestick',
          data: values,
          itemStyle: { color, color0: color, borderColor: color, borderColor0: color },
        },
        {
          type: 'bar',
          yAxisIndex: 1,
          data: vols,
          itemStyle: { color: 'rgba(124,139,156,0.4)' },
        },
      ],
    });
    return () => chart.dispose();
  }, [klines, up, name]);
  return <div ref={ref} style={{ width: '100%', height: 220 }} />;
}
```

- [ ] **Step 3: 创建 FundFlowChart.tsx**

```tsx
import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';
import type { SectorRow } from '../api/client';

export default function FundFlowChart({ data }: { data: SectorRow[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const names = data.map((d) => d.name);
    const flows = data.map((d) => d.fund_flow / 1e8); // 亿
    chart.setOption({
      grid: { left: 60, right: 30, top: 8, bottom: 24 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v.toFixed(2)} 亿` },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: names, axisLabel: { color: '#7c8b9c', fontSize: 11 } },
      series: [{
        type: 'bar',
        data: flows,
        itemStyle: { color: (p: { value: number }) => (p.value >= 0 ? '#e5484d' : '#2e9e6b') },
        barWidth: 10,
      }],
    });
    return () => chart.dispose();
  }, [data]);
  return <div ref={ref} style={{ width: '100%', height: 260 }} />;
}
```

- [ ] **Step 4: 创建 IndexMiniChart.tsx**

```tsx
import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface Props {
  points: number[];
  color: string;
}

export default function IndexMiniChart({ points, color }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, data: points.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [{ type: 'line', data: points, smooth: true, symbol: 'none',
                 lineStyle: { width: 1.5, color }, areaStyle: { color } }],
    });
    return () => chart.dispose();
  }, [points, color]);
  return <div ref={ref} style={{ width: '100%', height: 40 }} />;
}
```

- [ ] **Step 5: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/SectorKlineChart.tsx frontend/src/components/FundFlowChart.tsx frontend/src/components/IndexMiniChart.tsx frontend/src/api/client.ts
git commit -m "feat: 大屏 ECharts 图表组件（板块K线/资金流/指数迷你线）"
```

---

### Task 4: Dashboard 大屏重构 + 样式

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`（重写为大屏布局）
- Modify: `frontend/src/theme.css`（大屏布局样式）

**Interfaces:**
- Consumes: Task 3 的 3 个图表组件 + `getDashboard` + 现有 store（自选/新闻）
- Produces: 大屏 7 模块渲染 + 30s 自动刷新

- [ ] **Step 1: 重写 Dashboard.tsx 为大屏布局**

```tsx
import { useEffect, useState } from 'react';
import { getDashboard } from '../api/client';
import type { DashboardData } from '../api/client';
import FundFlowChart from '../components/FundFlowChart';
import IndexMiniChart from '../components/IndexMiniChart';
import PriceCard from '../components/PriceCard';
import SectorKlineChart from '../components/SectorKlineChart';
import { useApp } from '../store';

const DASHBOARD_REFRESH_MS = 30000;

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const news = useApp((s) => s.news);
  const connected = useApp((s) => s.connected);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
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
  const stamp = now.toLocaleTimeString('zh-CN', { hour12: false });
  const upCount = dash?.market.up ?? 0;
  const downCount = dash?.market.down ?? 0;
  const total = upCount + downCount || 1;
  const trend = (p: number[]) => p.length >= 2 ? p : [0, 0];
  return (
    <div className="page bigscreen">
      <div className="status-bar">
        <span className={`dot ${connected ? 'on' : ''}`} />
        <span className="conn">{connected ? '实时连接中' : '连接断开，重连中…'}</span>
        <span className="stamp">{stamp}</span>
      </div>
      {/* A. 指数区 + G. 温度条 */}
      <div className="bigscreen-top">
        {dash?.indices.map((ix) => (
          <div key={ix.code} className="index-card">
            <div className="index-name">{ix.name}</div>
            <div className="index-price" style={{ color: ix.change_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
              {ix.price.toFixed(2)}
            </div>
            <div className="index-change" style={{ color: ix.change_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
              {ix.change_pct >= 0 ? '+' : ''}{ix.change_pct.toFixed(2)}%
            </div>
            <IndexMiniChart points={trend([ix.prev_close, ix.open, ix.price])}
                            color={ix.change_pct >= 0 ? '#e5484d' : '#2e9e6b'} />
          </div>
        ))}
        <div className="market-temp">
          <div className="temp-title">市场温度</div>
          <div className="temp-bar">
            <div className="temp-up" style={{ width: `${(upCount / total) * 100}%` }} />
          </div>
          <div className="temp-nums">
            <span style={{ color: 'var(--up)' }}>↑ {upCount}</span>
            <span style={{ color: 'var(--down)' }}>↓ {downCount}</span>
          </div>
        </div>
      </div>
      {/* 中部：D 走势图（主区） + 侧边 B/C */}
      <div className="bigscreen-mid">
        <div className="kline-area">
          <h3>重点板块走势（涨幅前三 / 跌幅前三）</h3>
          <div className="kline-grid">
            {dash?.kline.top3_gainers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--up)' }}>{k.name} +{k.change_pct.toFixed(2)}%</div>
                <SectorKlineChart name={k.name} klines={k.klines} up />
              </div>
            ))}
            {dash?.kline.top3_losers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--down)' }}>{k.name} {k.change_pct.toFixed(2)}%</div>
                <SectorKlineChart name={k.name} klines={k.klines} up={false} />
              </div>
            ))}
          </div>
        </div>
        <div className="side-area">
          <div className="panel">
            <h3>板块涨跌排行</h3>
            <table className="tbl sector-rank">
              <thead><tr><th>板块</th><th>涨跌幅</th><th>领涨</th></tr></thead>
              <tbody>
                {dash?.sectors.top_gainers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--up)' }}>+{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
                {dash?.sectors.top_losers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--down)' }}>{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel">
            <h3>板块资金流向（主力净流入 TOP）</h3>
            <FundFlowChart data={dash?.sectors.fund_flow ?? []} />
          </div>
        </div>
      </div>
      {/* 底部：E 自选 + F 新闻 */}
      <div className="bigscreen-bottom">
        <div className="panel self-strip">
          <h3>自选实时行情</h3>
          <div className="grid">
            {Object.values(quotes).slice(0, 12).map((q) => (
              <div key={q.code} className="cell">
                <PriceCard q={q} />
              </div>
            ))}
          </div>
        </div>
        <div className="panel news-strip">
          <h3>新闻快讯</h3>
          <div className="news-feed">
            {news.slice(0, 12).map((n) => (
              <div key={n.id} className="news-line">
                <span className="muted">{n.source}</span> {n.title}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: theme.css 追加大屏样式**

```css
.bigscreen-top {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.index-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
}
.index-name { font-size: 13px; color: var(--muted); }
.index-price { font-family: var(--font-data); font-size: 26px; font-weight: 600; margin: 4px 0; }
.index-change { font-family: var(--font-data); font-size: 13px; }
.market-temp { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; }
.temp-title { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
.temp-bar { height: 10px; border-radius: 5px; background: var(--border); overflow: hidden; }
.temp-up { height: 100%; background: var(--up); }
.temp-nums { display: flex; justify-content: space-between; margin-top: 6px; font-family: var(--font-data); font-size: 12px; }
.bigscreen-mid { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-bottom: 12px; }
.kline-area { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; }
.kline-area h3 { margin: 0 0 10px; font-size: 15px; }
.kline-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.kline-card { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px; }
.kline-title { font-family: var(--font-data); font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.side-area { display: flex; flex-direction: column; gap: 12px; }
.sector-rank { font-size: 12px; }
.bigscreen-bottom { display: grid; grid-template-columns: 3fr 2fr; gap: 12px; }
.self-strip .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
.news-feed { max-height: 320px; overflow-y: auto; }
.news-line { padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; line-height: 1.5; }
.news-line:last-child { border-bottom: none; }
@media (max-width: 1100px) {
  .bigscreen-top { grid-template-columns: repeat(2, 1fr); }
  .bigscreen-mid { grid-template-columns: 1fr; }
  .bigscreen-bottom { grid-template-columns: 1fr; }
  .kline-grid { grid-template-columns: repeat(2, 1fr); }
}
```

- [ ] **Step 3: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/theme.css
git commit -m "feat: 看板页多维大屏布局（指数/排行/资金/K线/自选/新闻）"
```

---

### Task 5: 全量验收、冒烟、As-Built 与推送

**Files:**
- Modify: `README.md`（看板大屏说明）、`docs/superpowers/plans/2026-08-18-dashboard-bigscreen-plan.md`（As-Built）

- [ ] **Step 1: README 更新**

功能说明补充：看板为多维数据大屏（大盘指数/市场温度/板块涨跌排行/资金流向/重点板块K线/自选/新闻），30s 刷新，数据源为东财公开接口 + 新浪/腾讯行情。

- [ ] **Step 2: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（test ≥26）。

- [ ] **Step 3: 手动冒烟**

1. 清理残留进程；`cd backend && (./run.sh &)` + `cd frontend && (npm run dev &)`，sleep 6
2. `curl -s http://127.0.0.1:8210/api/dashboard` → 含 indices(3)/market/sectors/kline(6 板块)，30s TTL
3. 浏览器打开看板页：3 指数卡 + 温度条 + 排行表 + 资金流图 + 6 块 K线图 + 自选横排 + 新闻流；30s 自动刷新
4. `pkill -f "uvicorn app.main"; pkill -f vite`

- [ ] **Step 4: As-Built + 推送**

计划文档末尾追加 As-Built 表（Task 1-4 commit hash、验证结果、偏差——含：冷门过滤阈值 10、父子层级去重（银行/银行Ⅱ）、东财 ×100 换算、涨幅前三/跌幅前三可能含细分板块、ECharts 红涨绿跌配色）。然后：

```bash
git add README.md docs/superpowers/plans/2026-08-18-dashboard-bigscreen-plan.md
git commit -m "docs: 看板大屏化计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 5: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。

---

## As-Built 执行记录（Task 5 收尾，2026-08-19）

### Task 1-4 提交与验证

| Task | Commit | 说明 | 验证 |
|------|--------|------|------|
| 1 后端东财板块服务 | `0381808` | `feat: 东财板块/指数/日K数据服务（含冷门过滤）` | test_sector 3 用例绿 |
| 2 DashboardService + API | `9100a60` | `feat: 看板大屏聚合快照 API（30s TTL 缓存）` | test_dashboard 1 用例绿 |
| 3 前端图表组件 + client | `c87bd2b` | `feat: 大屏 ECharts 图表组件（板块K线/资金流/指数迷你线）` | eslint/tsc/build 绿 |
| 4 Dashboard 大屏重构 | `5d8ba85` | `feat: 看板页多维大屏布局（指数/排行/资金/K线/自选/新闻）` | lint/build 绿 |

### Task 5 全量验收（commit 前本地通过）

`make check && make lint && make typecheck && make test && make build` 全绿：
- `make check`：合规静态检查 OK（无交易语义）
- `make lint`：ruff / yapf / eslint / prettier 零错
- `make typecheck`：mypy 19 文件 + tsc 通过
- `make test`：**30 passed**（≥26）
- `make build`：Vite 构建成功（仅 1.19MB chunk 体积警告，非错误）

### 冒烟结果（本机 2026-08-19）

- `GET /api/dashboard` 直接 curl：`indices` 3（上证 3924.55 / 深证 14132.86 / 创业板 3549.0）、`market {up:620, down:1019}`、`sectors`（top_gainers 5 / top_losers 5 / fund_flow 10）、`kline`（top3_gainers / top3_losers 各 3，每板块 60 行日K）✓
- 前端 headless Chrome（1600×1000，`http://[::1]:5173`）：7 模块全部渲染——指数卡（上游可用时 2-3 张）、市场温度条（↑/↓ 家数 + 温度比例条）、板块涨跌排行表（10 行含领涨股）、资金流向条形图（canvas）、6 块 K线图（canvas）、自选横排（12 格实时行情）、新闻流（12 条）✓；30s 轮询由 `DASHBOARD_REFRESH_MS=30000` 驱动
- **东财接口偶发**：浏览器 3 次抓取中 2 次命中上游 `Server disconnected`（`fetch_indices` 返回 0-2 张指数卡）；后端按设计降级（空字段 + 保留缓存，绝不 500），直接 curl 仍可拿到完整 3 指数。属上游公开接口偶发，非代码缺陷。

### 偏差清单

| # | 计划原文 | 实际实现 | 说明 |
|---|---------|---------|------|
| 1 | Task1 `import logging` / `import httpx` 相邻无空行 | stdlib 与第三方 import 分组（ruff `I` 规则） | 计划代码未满足 ruff import 排序，落地时按 `make lint` 修正 |
| 2 | Task2 `request.app.state.dashboard` 直接访问 | `getattr(request.app.state, "dashboard", None)` | 避免服务未装配时 AttributeError，更稳的兜底写法 |
| 3 | Task3 `klines: (string \| number)[][]` | `klines: Array<Array<string \| number>>` | `@typescript-eslint/array-type` 规则要求泛型写法，按 lint 落地 |
| 4 | 冷门过滤阈值 | 沿用计划 `MIN_STOCKS = 10`（`f104 + f105 >= 10` 才纳入） | 排除氨纶 1 股等超冷门板块 |
| 5 | 父子层级去重 | `_clean_name` 去除 `Ⅱ/Ⅲ` 后缀后去重，保留首个 | 避免「银行 / 银行Ⅱ」重复占位（冒烟中「城商行Ⅲ」等细分板块仍以原名保留） |
| 6 | 东财 ×100 换算 | `_num(..., scale=100.0)` 对指数报价 /100 转浮点 | 东财报价为 ×100 整数，前端显示两位小数正确 |
| 7 | 涨幅/跌幅前三 | 按 `change_pct` 排序取前 3 | 冒烟中前三含「房地产服务 / 物业管理」等细分板块，属预期 |
| 8 | **Task5 收尾新增**：Task 1-4 提交时未过 yapf 格式与 mypy | `make format` 重排后端 4 文件；`_num` 参数补类型注解 `scale: float / default: float` 消除 mypy `no-any-return` | 收尾全量验收发现，已修正并随本记录提交 |

### 收尾提交与推送

```bash
git commit -m "docs: 看板大屏化计划追加执行记录（as-built）"   # 含 README + yapf/mypy 修正
git push origin main
```
