# 去同花顺化 + 本地自选列表实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底移除同花顺集成（登录/自选/持仓查询/会话存储），新增本地自选列表（`~/.investment-board/watchlist.json` + API + 前端管理页），项目回归纯公开数据源（行情=新浪/腾讯、新闻=东财/财联社）。

**Architecture:** 后端删除 `ths_client`/`vault`/`portfolio` 模块与登录/持仓路由/事件/采集，新增独立 `core/watchlist.py`（JSON 持久化 + 并发锁 + 原子写）与 `/api/watchlist` REST；行情服务从本地自选列表拉代码。前端删除持仓页/登录区/positions 状态，新增 Watchlist 自选管理页（增删 + 行情联动）。

**Tech Stack:** Python 3.11 / FastAPI / pytest / respx、React 18 + TS + Vite + zustand、ruff/yapf/mypy、eslint/prettier

## Global Constraints

- 只改：`backend/app/{api,core,main,models,config,market,news}.py|*`、`backend/tests/*`、`frontend/src/*`、`README.md`、`docs/ths-reverse-engineering.md`（删除或修改）；不新增依赖
- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK（`watchlist` 不含交易前缀，安全）
- **测试**：删除 `test_ths_client.py`、`test_vault.py` 后，**剩余既有测试全部通过 + 新增 `test_watchlist.py`**（不再要求 29 这个具体数）
- `make check`（合规）必须 OK；`make lint`（ruff/yapf/eslint/prettier）零错；`make typecheck`（mypy + tsc）通过；`make build` 成功
- 命令一律 `backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- 新代码 Google docstring（句末 ASCII `.`，ruff D 规则零错误）
- 删除性提交用 `refactor:`，新增本地自选用 `feat:`（阿里 commitlint type-enum 含两者）
- `settings.data_dir`（默认 `~/.investment-board/`）为自选文件所在目录；`watchlist.json` 不可见时按空列表处理（不崩溃）
- 所有外部请求保留超时与异常兜底；`/api/quotes`、`/api/news`、`/api/status` 契约保留（status 中去掉 `logged_in`/`ths` 字段）

---

### Task 1: 后端移除同花顺/持仓/登录（删除性改动）

**Files:**
- Delete: `backend/app/ths_client/`（base/parsers/web_client/README/__init__）、`backend/app/vault/`（store/__init__）、`backend/app/core/portfolio.py`
- Modify: `backend/app/api/routes.py`（删登录/登出/持仓路由、status 精简）
- Modify: `backend/app/config.py`（删 ths 配置）
- Modify: `backend/app/core/events.py`（删 POSITIONS/THS_STATUS 事件类型）
- Modify: `backend/app/core/scheduler.py`（删持仓循环）
- Modify: `backend/app/main.py`（删 ths/vault/positions 装配）
- Modify: `backend/app/models.py`（删 Position、保留 Stock）
- Modify: `backend/app/api/ws.py`（删 positions/ths_status 推送分支）
- Delete: `backend/tests/test_ths_client.py`、`backend/tests/test_vault.py`

**Interfaces:**
- Consumes: 现有模块依赖
- Produces: 无 ths/vault/positions 的干净后端；`scheduler.positions` 字段移除；`_collect_codes()` 暂返回行情 key 并集（Task 3 改本地自选）

- [ ] **Step 1: 删除模块与文件**

```bash
rm -rf backend/app/ths_client backend/app/vault backend/app/core/portfolio.py
rm backend/tests/test_ths_client.py backend/tests/test_vault.py
```

- [ ] **Step 2: config.py 移除 ths 配置**

删除 `ths_endpoint_prefix`/`ths_watchlist_url`/`ths_positions_url` 字段及对应 3 行环境变量读取。保留其余（host/port/data_dir/quotes_interval/news_interval 等）。

- [ ] **Step 3: events.py 移除持仓/同花顺事件**

`EventType` 中删除 `POSITIONS`、`THS_STATUS` 两行；docstring 同步（"行情/新闻事件"）。

- [ ] **Step 4: models.py 删除 Position**

删除 `Position` dataclass（保留 Stock/Quote/IntradayPoint/NewsItem）；模块 docstring 同步为"自选股、实时行情、日内分时与新闻条目"。

- [ ] **Step 5: scheduler.py 移除持仓循环**

- 删除 `positions_fetcher`/`positions_interval`/`_ths`/`self.positions` 相关参数与字段
- 删除 `_positions_loop` 方法与 `start()` 中对应 task
- 删除 `_apply_quotes` 方法（portfolio 依赖）
- `_collect_codes()` 改为仅返回 `sorted(self.quotes.keys())`（暂态，Task 3 接本地自选）
- `__init__` 签名变为 `(bus, quotes_fetcher, news_fetcher=None, quotes_interval=3.0, news_interval=60.0)`
- 模块 docstring 同步"行情/新闻两个后台循环"

- [ ] **Step 6: main.py 移除装配**

- 删 `Vault`/`ThsWebClient` 导入与创建
- 删 `positions_fetcher` 定义
- `news_fetcher` 简化：不再判断 `ths.is_logged_in`，`ind = await news.fetch_individual(codes); glb = await news.fetch_global(); return ind + glb`
- `Scheduler(...)` 调用删 `positions_fetcher`/`positions_interval`/`ths_adapter`
- 删 `app.state.vault`/`app.state.ths`；保留 `app.state.bus`/`app.state.scheduler`

- [ ] **Step 7: routes.py 移除登录/登出/持仓，status 精简**

- 删除 `/login/qrcode`、`/login/poll`、`/logout`、`/positions` 路由
- `status` 改为：
```python
@router.get("/status")
async def status():
    """返回各数据源状态，供前端展示顶部状态栏.

    Returns:
        含各数据源状态的字典（market/news 当前均为 ok）.
    """
    return {"sources": {"market": "ok", "news": "ok"}}
```
- 删除 `from app.core.portfolio import compute_positions` 与 `from app.api import Request`（若不再用）

- [ ] **Step 8: ws.py 移除 positions/ths_status 推送**

读 `backend/app/api/ws.py`，删除 `positions`/`ths_status` 事件的发送分支（保留 quotes/news/source_status）。

- [ ] **Step 9: 修复引用并验证**

```bash
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
backend/.venv/bin/pytest -q   # 删除 ths/vault 测试后剩余测试应通过（可能需修复 test_core/test_api 中引用）
backend/.venv/bin/yapf -dr backend/app backend/tests
```

> 若 `test_core.py`/`test_api.py`/`test_main.py` 引用了 ths/vault/positions，按"仅移除对应断言/参数，不改变非 ths 断言"原则修正（保留行情/新闻/API 测试）。修完需全绿。

- [ ] **Step 10: 提交**

```bash
git add -A backend
git commit -m "refactor: 移除同花顺/持仓/登录与会话存储（回归纯公开数据源）"
```

---

### Task 2: 本地自选存储 + API

**Files:**
- Create: `backend/app/core/watchlist.py`
- Modify: `backend/app/api/routes.py`（新增 `/api/watchlist` 三路由）
- Modify: `backend/app/config.py`（确认 data_dir 存在，无需新增）
- Create: `backend/tests/test_watchlist.py`

**Interfaces:**
- Consumes: `settings.data_dir`
- Produces: `watchlist.load_watchlist(data_dir) -> list[dict]`、`watchlist.add_watchlist(data_dir, code, name="") -> list[dict]`、`watchlist.remove_watchlist(data_dir, code) -> list[dict]`；REST `GET/POST /api/watchlist`、`DELETE /api/watchlist/{code}`

- [ ] **Step 1: 创建 watchlist.py**

```python
"""本地自选股列表的加载/添加/删除（JSON 文件持久化，含并发锁与原子写）."""
import json
import re
import threading
from pathlib import Path

_FILENAME = "watchlist.json"
_lock = threading.Lock()


def _path(data_dir: Path) -> Path:
    """返回自选列表文件路径.

    Args:
        data_dir: 数据目录.

    Returns:
        data_dir 下的 watchlist.json 路径.
    """
    return data_dir / _FILENAME


def load_watchlist(data_dir: Path) -> list[dict]:
    """读取本地自选列表.

    Args:
        data_dir: 数据目录.

    Returns:
        自选列表 [{code, name}, ...]；文件不存在返回空列表.
    """
    p = _path(data_dir)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [i for i in data if isinstance(i, dict) and i.get("code")]
        return []
    except (json.JSONDecodeError, OSError):
        # 损坏时备份原文件并返回空列表，避免服务不可用
        try:
            p.rename(p.with_suffix(".json.bak"))
        except OSError:
            pass
        return []


def add_watchlist(data_dir: Path, code: str, name: str = "") -> list[dict]:
    """添加股票到自选列表（按代码去重）.

    Args:
        data_dir: 数据目录.
        code: 6 位股票代码.
        name: 股票名称，可为空串（显示层用行情数据补齐）.

    Returns:
        更新后的完整自选列表.

    Raises:
        ValueError: code 不是 6 位数字.
    """
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("代码须为 6 位数字")
    with _lock:
        items = load_watchlist(data_dir)
        if not any(i.get("code") == code for i in items):
            items.append({"code": code, "name": name})
        _write(data_dir, items)
        return items


def remove_watchlist(data_dir: Path, code: str) -> list[dict]:
    """从自选列表删除股票.

    Args:
        data_dir: 数据目录.
        code: 6 位股票代码.

    Returns:
        更新后的完整自选列表.
    """
    with _lock:
        items = [i for i in load_watchlist(data_dir) if i.get("code") != code]
        _write(data_dir, items)
        return items


def _write(data_dir: Path, items: list[dict]) -> None:
    """原子写入自选列表（先写临时文件再替换，避免半写损坏）.

    Args:
        data_dir: 数据目录.
        items: 待写入的列表.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    p = _path(data_dir)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
```

- [ ] **Step 2: routes.py 新增自选三路由**

在 `router` 下新增（保持现有 imports，追加 `from app.core import watchlist` 与 `from app.config import settings`）：

```python
@router.get("/watchlist")
async def get_watchlist():
    """返回本地自选列表.

    Returns:
        自选列表 [{code, name}, ...].
    """
    return watchlist.load_watchlist(settings.data_dir)


@router.post("/watchlist")
async def add_watchlist_item(body: dict):
    """添加股票到自选列表.

    Args:
        body: 请求体，{"code": str}；name 可省略（显示层用行情补齐）.

    Returns:
        更新后的自选列表.

    Raises:
        HTTPException: 400 当代码格式非法.
    """
    code = (body or {}).get("code", "")
    try:
        return watchlist.add_watchlist(settings.data_dir, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/{code}")
async def remove_watchlist_item(code: str):
    """从自选列表删除股票.

    Args:
        code: 6 位股票代码.

    Returns:
        更新后的自选列表.
    """
    return watchlist.remove_watchlist(settings.data_dir, code)
```

> 名称补齐采用简化方案：POST 仅存 code（name 空），显示层用行情 `Quote.name` 补齐——避免 routes 依赖市场服务（比 spec 原文"添加时补名"更简单，As-Built 记录此简化）。

- [ ] **Step 3: 创建 test_watchlist.py**

```python
"""本地自选列表存储/API 的单元测试."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import watchlist


def test_watchlist_empty(tmp_path: Path):
    """目录无文件时返回空列表."""
    assert watchlist.load_watchlist(tmp_path) == []


def test_watchlist_add_and_remove(tmp_path: Path):
    """添加去重与删除."""
    watchlist.add_watchlist(tmp_path, "600519", "贵州茅台")
    watchlist.add_watchlist(tmp_path, "000001", "平安银行")
    assert len(watchlist.load_watchlist(tmp_path)) == 2
    # 去重
    watchlist.add_watchlist(tmp_path, "600519")
    assert len(watchlist.load_watchlist(tmp_path)) == 2
    watchlist.remove_watchlist(tmp_path, "600519")
    assert [i["code"] for i in watchlist.load_watchlist(tmp_path)] == ["000001"]


def test_watchlist_bad_code(tmp_path: Path):
    """非法代码抛 ValueError."""
    with pytest.raises(ValueError):
        watchlist.add_watchlist(tmp_path, "abc")


def test_watchlist_corrupt_file(tmp_path: Path):
    """损坏文件降级为空列表并备份."""
    (tmp_path / "watchlist.json").write_text("{not json", encoding="utf-8")
    assert watchlist.load_watchlist(tmp_path) == []
    assert (tmp_path / "watchlist.json.bak").exists()


def test_watchlist_api(tmp_path: Path, monkeypatch):
    """/api/watchlist 增删查."""
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    from app.main import app
    # 直接调用（不进 context manager），避免触发 lifespan 启动调度器连真实网络
    client = TestClient(app)
    assert client.get("/api/watchlist").json() == []
    r = client.post("/api/watchlist", json={"code": "600519"})
    assert r.status_code == 200
    assert [i["code"] for i in r.json()] == ["600519"]
    r = client.post("/api/watchlist", json={"code": "bad"})
    assert r.status_code == 400
    r = client.delete("/api/watchlist/600519")
    assert r.json() == []
```

- [ ] **Step 4: 验证**

```bash
backend/.venv/bin/pytest -q backend/tests/test_watchlist.py -v
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/watchlist.py backend/app/api/routes.py backend/tests/test_watchlist.py
git commit -m "feat: 本地自选列表存储与 REST API"
```

---

### Task 3: 行情/新闻服务接本地自选

**Files:**
- Modify: `backend/app/core/scheduler.py`（`_collect_codes` 从 watchlist 拉代码）
- Modify: `backend/tests/test_core.py`（适配无持仓/ths 的 Scheduler 签名）

**Interfaces:**
- Consumes: `watchlist.load_watchlist(settings.data_dir)`
- Produces: `Scheduler` 不含 positions；行情/新闻按本地自选代码抓取

- [ ] **Step 1: scheduler._collect_codes 接本地自选**

```python
    def _collect_codes(self) -> list[str]:
        """汇总本地自选代码与已有行情 key 的并集并排序返回."""
        from app.core import watchlist
        from app.config import settings

        codes = set(self.quotes.keys())
        for item in watchlist.load_watchlist(settings.data_dir):
            codes.add(item["code"])
        return sorted(codes)
```

（放在方法内 import 以避免模块级循环依赖；`_quotes_loop`/`_news_loop` 不变。）

- [ ] **Step 2: 适配 test_core.py**

读 `backend/tests/test_core.py`：删除/替换引用 `positions_fetcher`/`ths_adapter`/`positions` 的用例与断言（保留行情/新闻/调度生命周期断言）。若 Scheduler 构造仍传旧参数，改为新签名。

- [ ] **Step 3: 验证**

```bash
backend/.venv/bin/pytest -q
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/core/scheduler.py backend/tests/test_core.py
git commit -m "refactor: 行情/新闻按本地自选列表拉取（不再依赖同花顺）"
```

---

### Task 4: 前端移除同花顺 + 新增自选管理页

**Files:**
- Delete: `frontend/src/pages/Positions.tsx`、`frontend/src/components/PositionsSummary.tsx`
- Modify: `frontend/src/api/client.ts`、`frontend/src/store.tsx`、`frontend/src/types.ts`、`frontend/src/api/ws.ts`、`frontend/src/App.tsx`、`frontend/src/pages/Dashboard.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/src/components/PriceCard.tsx`（如依赖 Position 类型则不动）
- Create: `frontend/src/pages/Watchlist.tsx`

**Interfaces:**
- Consumes: 后端 `/api/watchlist`、`/api/quotes`、`/api/news`、`/api/status`
- Produces: 导航=看板/自选/新闻/设置；store 新增 `watchlist` 状态与 `loadWatchlist/addWatchlist/removeWatchlist`

- [ ] **Step 1: client.ts 移除登录/持仓，新增自选 API**

删除 `startLogin`/`pollLogin`/`logout`/`getPositions` 及 `LoginQrcode`/`LoginPoll` 接口；新增：

```ts
export interface WatchItem {
  code: string;
  name: string;
}
export const getWatchlist = () => json<WatchItem[]>('/api/watchlist');
export const addWatchlist = (code: string) =>
  json<WatchItem[]>('/api/watchlist', { method: 'POST', body: JSON.stringify({ code }) });
export const removeWatchlist = (code: string) =>
  json<WatchItem[]>(`/api/watchlist/${code}`, { method: 'DELETE' });
```

- [ ] **Step 2: types.ts 精简**

删除 `Position` 接口；`Status` 改为 `{ sources: Record<string, string> }`；`WsEvent` 删除 `positions`/`ths_status` 变体（保留 quotes/news/source_status）。

- [ ] **Step 3: store.tsx 移除 positions，新增 watchlist**

- 删 `positions` 状态、`setPositions`、`getPositions` 引用
- 新增：
```ts
watchlist: WatchItem[];
loadWatchlist: () => Promise<void>;
addToWatchlist: (code: string) => Promise<void>;
removeFromWatchlist: (code: string) => Promise<void>;
```
- `refresh()` 改为 `Promise.all([getQuotes(), getNews('all'), getStatus(), getWatchlist()])`，`set({ quotes, news, status, watchlist, connected: true })`
- `init()` 的 WS 分发删 positions 分支；`addToWatchlist`/`removeFromWatchlist` 调 API 后 `set({ watchlist: res })`（res 即更新后列表）

- [ ] **Step 4: 新增 Watchlist.tsx 自选管理页**

```tsx
import { useState } from 'react';
import PriceCard from '../components/PriceCard';
import { useApp } from '../store';

export default function Watchlist() {
  const quotes = useApp((s) => s.quotes);
  const watchlist = useApp((s) => s.watchlist);
  const addToWatchlist = useApp((s) => s.addToWatchlist);
  const removeFromWatchlist = useApp((s) => s.removeFromWatchlist);
  const [code, setCode] = useState('');

  const submit = async () => {
    if (!/^\d{6}$/.test(code.trim())) return;
    await addToWatchlist(code.trim());
    setCode('');
  };

  return (
    <div className="page">
      <h2>自选</h2>
      <div className="watchlist-add">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="输入 6 位股票代码，如 600519"
          maxLength={6}
        />
        <button onClick={submit}>添加</button>
      </div>
      <div className="grid">
        {watchlist.map((w) => {
          const q = quotes[w.code];
          if (!q) return null;
          return (
            <div key={w.code} className="cell">
              <PriceCard q={q} />
              <button className="remove" onClick={() => removeFromWatchlist(w.code)}>
                删除
              </button>
            </div>
          );
        })}
      </div>
      {watchlist.length === 0 && <div className="muted">暂无自选，输入代码添加</div>}
    </div>
  );
}
```

（样式：在 theme.css 追加 `.watchlist-add` 与 `.remove` 少量规则——先读 theme.css 现状再追加；`PriceCard` 已随 quotes 实时更新。）

- [ ] **Step 5: App.tsx 导航去掉持仓、加自选**

`tabs` 数组改为 `[['dashboard','看板'],['watchlist','自选'],['news','新闻'],['settings','设置']]`；`Page` 类型加 `'watchlist'`；条件渲染加 `{page === 'watchlist' && <Watchlist />}`，删 Positions。

- [ ] **Step 6: Dashboard/Settings 适配**

- `Dashboard.tsx`：状态条去掉"源: 新浪·腾讯"（保留 dot/conn/stamp）；`connected`/`quotes` 逻辑不变
- `Settings.tsx`：删除同花顺登录区（beginLogin/doLogout/qr/scanning/error/statusText 全部移除），保留"数据源健康"面板（去掉 `logged_in` 相关行，显示 market/news 源）

- [ ] **Step 7: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py
```

- [ ] **Step 8: 提交**

```bash
git add -A frontend/src
git commit -m "feat: 新增自选管理页并移除持仓/登录 UI"
```

---

### Task 5: 文档更新、全量验收与推送

**Files:**
- Modify: `README.md`（移除同花顺/持仓说明，更新功能与 FAQ）
- Modify: `docs/ths-reverse-engineering.md`（标记废弃，或删除并更新引用）
- Modify: `docs/superpowers/plans/2026-08-18-remove-ths-local-watchlist-plan.md`（追加 As-Built）

- [ ] **Step 1: README 更新**

- 项目简介/功能列表：移除"同花顺登录/持仓"，改为"本地自选列表（增删）+ 行情 + 新闻，纯公开数据源"
- FAQ：移除同花顺相关条目，保留行情/新闻第三方变动说明；环境变量段移除 `IB_THS_*`
- 若 README 引用 `docs/ths-reverse-engineering.md`，改为不再引用（该文档标记废弃）

- [ ] **Step 2: 逆向文档标记废弃**

`docs/ths-reverse-engineering.md` 顶部加"⚠️ 已废弃（2026-08-18）：项目已移除同花顺集成，本文件仅作历史记录"。

- [ ] **Step 3: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（test 为删除 ths/vault 后的剩余既有 + 新增 watchlist 用例）。

- [ ] **Step 4: 手动冒烟**

1. `cd backend && (./run.sh &)` + `cd frontend && (npm run dev &)`，sleep 6
2. `curl -s http://127.0.0.1:8210/api/status` → `{"sources":{...}}`（无 logged_in/ths）
3. `curl -X POST /api/watchlist -d '{"code":"600519"}'` → 返回含 600519 列表；`curl /api/watchlist` 确认持久化；`curl -X DELETE /api/watchlist/600519`
4. 浏览器打开：导航无持仓、有自选；自选页添加 600519 → 行情卡出现（新浪/腾讯行情）
5. `pkill -f "uvicorn app.main"; pkill -f vite`

- [ ] **Step 5: As-Built + 推送**

计划文档末尾追加 As-Built 表（Task 1-4 commit hash、验证结果、偏差——含"POST 仅存 code 名称由显示层补齐"的简化、删除的测试文件清单）。然后：

```bash
git add README.md docs/ths-reverse-engineering.md docs/superpowers/plans/2026-08-18-remove-ths-local-watchlist-plan.md
git commit -m "docs: 去同花顺化计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 6: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。

---

## As-Built（执行记录，2026-08-18）

### 提交清单

| Task | Commit | 内容 | 验证结果 |
| --- | --- | --- | --- |
| 1 | `4799e38` | `refactor: 移除同花顺/持仓/登录与会话存储（回归纯公开数据源）` | 删除 `test_ths_client.py`/`test_vault.py` 后剩余测试 17 passed；ruff/mypy/yapf 通过 |
| 2 | `9f2243d` | `feat: 本地自选列表存储与 REST API` | 新增 `test_watchlist.py` 5 用例 → 22 passed；ruff/mypy/check_no_trade 通过 |
| 3 | `9d37ac7` | `refactor: 行情/新闻按本地自选列表拉取（不再依赖同花顺）` | 适配 `test_core.py` 新增 1 用例 → 23 passed；ruff/mypy/check_no_trade 通过 |
| 4 | `5a34b8e` | `feat: 新增自选管理页并移除持仓/登录 UI` | 前端 eslint/prettier/tsc/build 全绿；check_no_trade 通过 |
| 5 | 本次提交 | `docs: 去同花顺化计划追加执行记录（as-built）` | `make check && make lint && make typecheck && make test && make build` 全绿；手动冒烟通过 |

### Task 5 验收输出

- `make check`：`OK: 未发现交易语义代码。`
- `make lint`：ruff 零错；yapf 零 diff；eslint 零错；prettier 全匹配。
- `make typecheck`：mypy `Success: no issues found in 17 source files`；tsc 通过。
- `make test`：`23 passed`（1 个 starlette deprecation warning，非失败）。
- `make build`：Vite 构建成功（chunk 大小提示为既有非阻塞警告）。
- 手动冒烟（后端 8210 + 前端 5173）：
  - `GET /api/status` → `{"sources":{"market":"ok","news":"ok"}}`（无 `logged_in`/`ths`）。
  - `POST /api/watchlist {"code":"600519"}` → `[{"code":"600519","name":""}]`；`GET /api/watchlist` 确认持久化；等待 ~12s 后 `GET /api/quotes` 返回实时行情（`贵州茅台` 名称由行情补齐）；`DELETE /api/watchlist/600519` → `[]`。
  - 前端 `localhost:5173` 正常返回页面，经 Vite 代理 `/api/status` 正常；导航为 看板/自选/新闻/设置（无持仓）。
  - 冒烟期间财联社 `telegraphList` 返回 404，后端优雅降级（记录告警、返回空列表），属第三方接口变动、非回归。

### 偏差 / 遗留清单

1. **POST 仅存 code（简化）**：按计划 Task 2 备注，添加自选时仅存 code（name 空串），显示层用行情 `Quote.name` 补齐，`/api/watchlist` 路由不依赖市场服务。As-Built 记录此简化。
2. **Task 5 清理死字段**：`backend/app/config.py` 残留 `positions_interval` 死字段（仅旧文档引用），本次提交一并删除；ruff/mypy/pytest 复验通过。
3. **Task 5 修复 yapf 格式**：Task 3 提交的 `backend/tests/test_core.py` 存在 yapf 格式不达标（`make lint` 此前未全量覆盖），本次以 `yapf -i` 修复，使 `make lint` 全绿。
4. **删除的测试文件清单**：`backend/tests/test_ths_client.py`（114 行）、`backend/tests/test_vault.py`（43 行）。
5. **遗留（超出本计划范围未动）**：`docs/architecture.md` 与 `docs/compliance.md` 仍含同花顺/持仓/会话描述，因 Global Constraints 限定仅改 `README.md` + `docs/ths-reverse-engineering.md`，未一并更新，建议后续独立跟进。
6. **遗留（外部源）**：财联社全局快讯接口 404，新闻 `individual` 为空属外部源变动，非本项目缺陷。
