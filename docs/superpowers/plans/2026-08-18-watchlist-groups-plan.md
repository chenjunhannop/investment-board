# 自选文件夹分类实施计划（同花顺式）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把扁平自选列表升级为同花顺式文件夹分类（新建/重命名/删除/展开折叠/按文件夹增删股票），并预置 16 个文件夹（持仓 6 只 + 15 领域 × 7 龙头 = 111 只），全部代码经行情接口验证有效。

**Architecture:** 后端 `watchlist.py` 重构为分组结构（`{version:2, groups:[{name, stocks}]}`，v1 自动迁移），新增文件夹/股票按组 CRUD；`scheduler._collect_codes` 改为遍历所有文件夹；前端自选页改为文件夹区块布局（顶部统一添加栏 + 下拉选文件夹 + 新建/重命名/删除/折叠）；一次性脚本预置数据并逐只验证代码。

**Tech Stack:** Python 3.11 / FastAPI / pytest、React 18 + TS + Vite + zustand、ruff/yapf/mypy、eslint/prettier

## Global Constraints

- 只改：`backend/app/core/watchlist.py`、`backend/app/api/routes.py`、`backend/app/core/scheduler.py`、`backend/tests/test_watchlist.py`、`backend/tests/test_api.py`、`backend/tests/test_core.py`、`frontend/src/{types,api/client,store,pages/Watchlist,theme.css,App}.tsx|ts`、`scripts/seed_watchlist.py`、`README.md`、`docs/superpowers/plans/...`
- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK
- **测试**：既有测试全绿 + 新增分组存储/API 用例（当前 23 passed，重构后 ≥23）
- `make check`（合规）OK；`make lint`（ruff/yapf/eslint/prettier）零错；`make typecheck`（mypy+tsc）通过；`make build` 成功
- 命令一律 `backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- 新代码 Google docstring（句末 ASCII `.`，ruff D 规则零错误）；commit 用 `feat:`（功能）/ `chore:`（数据预置）/ `docs:`
- 文件夹名唯一/非空；股票代码 6 位数字；删除文件夹连带删除其股票
- 数据文件 `~/.investment-board/watchlist.json`（`settings.data_dir`）；v1 迁移不丢数据
- 预置代码验证用新浪行情接口 `https://hq.sinajs.cn/list=sh600519`（需 `Referer: https://finance.sina.com.cn`）；无效代码剔除并报告

---

### Task 1: 后端 watchlist.py 重构为分组结构

**Files:**
- Modify: `backend/app/core/watchlist.py`（完全重写为 v2 分组）
- Modify: `backend/tests/test_watchlist.py`（重写为分组用例）

**Interfaces:**
- Consumes: `settings.data_dir`
- Produces: `load_watchlist(data_dir) -> dict`（`{version, groups:[{name,stocks}]}`）、`add_group/rename_group/remove_group(data_dir, ...) -> dict`、`add_stock/remove_stock(data_dir, group, code) -> dict`、`collect_codes(data_dir) -> list[str]`

- [ ] **Step 1: 重写 watchlist.py（v2 分组结构）**

```python
"""本地自选股列表（文件夹分组）的加载/增删（JSON 持久化，含并发锁与原子写）.

v2 结构: {"version": 2, "groups": [{"name": str, "stocks": [{"code","name"}]}]}
"""
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


def _empty() -> dict:
    """返回空分组结构.

    Returns:
        {"version": 2, "groups": []}.
    """
    return {"version": 2, "groups": []}


def _read(data_dir: Path) -> dict:
    """读取文件并做 v1→v2 迁移；损坏或不存在时返回空结构."""
    p = _path(data_dir)
    if not p.exists():
        return _empty()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # v1 扁平 [{code,name}] → v2，迁移到"未分组"文件夹
            stocks = [i for i in data if isinstance(i, dict) and i.get("code")]
            migrated = {"version": 2, "groups": [{"name": "未分组", "stocks": stocks}]}
            _write(data_dir, migrated)
            return migrated
        if isinstance(data, dict) and isinstance(data.get("groups"), list):
            return data
        return _empty()
    except (json.JSONDecodeError, OSError):
        try:
            p.rename(p.with_suffix(".json.bak"))
        except OSError:
            pass
        return _empty()


def _write(data_dir: Path, data: dict) -> None:
    """原子写入自选列表（先写临时文件再替换，避免半写损坏）.

    Args:
        data_dir: 数据目录.
        data: v2 分组结构字典.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    p = _path(data_dir)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load_watchlist(data_dir: Path) -> dict:
    """读取本地自选列表.

    Args:
        data_dir: 数据目录.

    Returns:
        v2 分组结构 {"version": 2, "groups": [...]}.
    """
    with _lock:
        return _read(data_dir)


def add_group(data_dir: Path, name: str) -> dict:
    """新建空文件夹.

    Args:
        data_dir: 数据目录.
        name: 文件夹名（非空）.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 名称为空或与已有文件夹重名.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("文件夹名不能为空")
    with _lock:
        data = _read(data_dir)
        if any(g["name"] == name for g in data["groups"]):
            raise ValueError("文件夹已存在")
        data["groups"].append({"name": name, "stocks": []})
        _write(data_dir, data)
        return data


def rename_group(data_dir: Path, name: str, new_name: str) -> dict:
    """重命名文件夹.

    Args:
        data_dir: 数据目录.
        name: 当前文件夹名.
        new_name: 新文件夹名（非空）.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹不存在或新名称与其它文件夹重名.
    """
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValueError("文件夹名不能为空")
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == name), None)
        if target is None:
            raise ValueError("文件夹不存在")
        if any(g["name"] == new_name and g is not target for g in groups):
            raise ValueError("文件夹已存在")
        target["name"] = new_name
        _write(data_dir, data)
        return data


def remove_group(data_dir: Path, name: str) -> dict:
    """删除文件夹（连带删除其中全部股票）.

    Args:
        data_dir: 数据目录.
        name: 文件夹名.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹不存在.
    """
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        if not any(g["name"] == name for g in groups):
            raise ValueError("文件夹不存在")
        data["groups"] = [g for g in groups if g["name"] != name]
        _write(data_dir, data)
        return data


def add_stock(data_dir: Path, group: str, code: str) -> dict:
    """向指定文件夹添加股票（按代码去重）.

    Args:
        data_dir: 数据目录.
        group: 目标文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 代码非法或文件夹不存在.
    """
    code = (code or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("代码须为 6 位数字")
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == group), None)
        if target is None:
            raise ValueError("文件夹不存在")
        if not any(s["code"] == code for s in target["stocks"]):
            target["stocks"].append({"code": code, "name": ""})
        _write(data_dir, data)
        return data


def remove_stock(data_dir: Path, group: str, code: str) -> dict:
    """从指定文件夹删除股票.

    Args:
        data_dir: 数据目录.
        group: 文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹或股票不存在.
    """
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == group), None)
        if target is None:
            raise ValueError("文件夹不存在")
        before = len(target["stocks"])
        target["stocks"] = [s for s in target["stocks"] if s["code"] != code]
        if len(target["stocks"]) == before:
            raise ValueError("股票不存在")
        _write(data_dir, data)
        return data


def collect_codes(data_dir: Path) -> list[str]:
    """遍历所有文件夹收集股票代码并排序返回.

    Args:
        data_dir: 数据目录.

    Returns:
        全部文件夹内代码的排序去重列表.
    """
    codes = set()
    for g in _read(data_dir)["groups"]:
        for s in g["stocks"]:
            codes.add(s["code"])
    return sorted(codes)
```

- [ ] **Step 2: 重写 test_watchlist.py**

```python
"""本地自选列表（分组结构）存储的单元测试."""
from pathlib import Path

import pytest

from app.core import watchlist


def test_empty(tmp_path: Path):
    """目录无文件时返回空分组结构."""
    assert watchlist.load_watchlist(tmp_path) == {"version": 2, "groups": []}


def test_group_crud(tmp_path: Path):
    """文件夹新建/重命名/删除."""
    watchlist.add_group(tmp_path, "银行")
    watchlist.add_group(tmp_path, "白酒")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["银行", "白酒"]
    with pytest.raises(ValueError):
        watchlist.add_group(tmp_path, "银行")  # 重名
    watchlist.rename_group(tmp_path, "银行", "银行股")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["银行股", "白酒"]
    watchlist.remove_group(tmp_path, "银行股")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["白酒"]


def test_stock_crud(tmp_path: Path):
    """向文件夹添加/删除股票，去重."""
    watchlist.add_group(tmp_path, "白酒")
    watchlist.add_stock(tmp_path, "白酒", "600519")
    watchlist.add_stock(tmp_path, "白酒", "000858")
    watchlist.add_stock(tmp_path, "白酒", "600519")  # 去重
    stocks = watchlist.load_watchlist(tmp_path)["groups"][0]["stocks"]
    assert [s["code"] for s in stocks] == ["600519", "000858"]
    watchlist.remove_stock(tmp_path, "白酒", "600519")
    assert [s["code"] for s in watchlist.load_watchlist(tmp_path)["groups"][0]["stocks"]] == ["000858"]


def test_stock_validation(tmp_path: Path):
    """非法代码与不存在的文件夹/股票抛 ValueError."""
    watchlist.add_group(tmp_path, "A")
    with pytest.raises(ValueError):
        watchlist.add_stock(tmp_path, "A", "abc")
    with pytest.raises(ValueError):
        watchlist.add_stock(tmp_path, "不存在", "600519")
    watchlist.add_stock(tmp_path, "A", "600519")
    with pytest.raises(ValueError):
        watchlist.remove_stock(tmp_path, "A", "000000")


def test_v1_migration(tmp_path: Path):
    """v1 扁平数组自动迁移到未分组文件夹."""
    (tmp_path / "watchlist.json").write_text(
        '[{"code": "600519", "name": ""}]', encoding="utf-8")
    data = watchlist.load_watchlist(tmp_path)
    assert data["version"] == 2
    assert data["groups"][0]["name"] == "未分组"
    assert data["groups"][0]["stocks"][0]["code"] == "600519"


def test_collect_codes(tmp_path: Path):
    """collect_codes 遍历所有文件夹."""
    watchlist.add_group(tmp_path, "A")
    watchlist.add_group(tmp_path, "B")
    watchlist.add_stock(tmp_path, "A", "600519")
    watchlist.add_stock(tmp_path, "B", "000001")
    watchlist.add_stock(tmp_path, "B", "600519")
    assert watchlist.collect_codes(tmp_path) == ["000001", "600519"]


def test_corrupt_file(tmp_path: Path):
    """损坏文件降级为空结构并备份."""
    (tmp_path / "watchlist.json").write_text("{bad", encoding="utf-8")
    assert watchlist.load_watchlist(tmp_path) == {"version": 2, "groups": []}
    assert (tmp_path / "watchlist.json.bak").exists()
```

- [ ] **Step 3: 验证**

```bash
backend/.venv/bin/pytest -q backend/tests/test_watchlist.py -v
backend/.venv/bin/ruff check backend/app/core/watchlist.py
backend/.venv/bin/mypy backend/app
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/core/watchlist.py backend/tests/test_watchlist.py
git commit -m "feat: 自选列表升级为文件夹分组结构（v2 迁移）"
```

---

### Task 2: API 重构 + scheduler 遍历文件夹

**Files:**
- Modify: `backend/app/api/routes.py`（6 个分组路由替换原 3 路由）
- Modify: `backend/app/core/scheduler.py`（`_collect_codes` 用 `collect_codes`）
- Modify: `backend/tests/test_api.py`、`backend/tests/test_core.py`

**Interfaces:**
- Consumes: Task 1 的 `watchlist` 函数集
- Produces: REST：`GET /watchlist`、`POST/PUT/DELETE /watchlist/groups...`、`POST/DELETE /watchlist/stocks...`；`Scheduler._collect_codes()` 含全部文件夹代码

- [ ] **Step 1: routes.py 替换为分组路由**

删除原 `/watchlist`、`POST /watchlist`、`DELETE /watchlist/{code}` 三路由，替换为：

```python
@router.get("/watchlist")
async def get_watchlist():
    """返回本地自选列表（文件夹分组结构）.

    Returns:
        {"version": 2, "groups": [{"name", "stocks"}]}.
    """
    return watchlist.load_watchlist(settings.data_dir)


@router.post("/watchlist/groups")
async def add_group(body: dict):
    """新建自选文件夹.

    Args:
        body: {"name": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当名称为空或重名.
    """
    try:
        return watchlist.add_group(settings.data_dir, (body or {}).get("name", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/watchlist/groups/{name}")
async def rename_group(name: str, body: dict):
    """重命名自选文件夹.

    Args:
        name: 当前文件夹名.
        body: {"new_name": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹不存在或新名非法.
    """
    try:
        return watchlist.rename_group(settings.data_dir, name,
                                      (body or {}).get("new_name", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/groups/{name}")
async def remove_group(name: str):
    """删除自选文件夹（连带其股票）.

    Args:
        name: 文件夹名.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹不存在.
    """
    try:
        return watchlist.remove_group(settings.data_dir, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/watchlist/stocks")
async def add_stock(body: dict):
    """向指定文件夹添加股票.

    Args:
        body: {"group": str, "code": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当代码非法或文件夹不存在.
    """
    body = body or {}
    try:
        return watchlist.add_stock(settings.data_dir, body.get("group", ""),
                                   body.get("code", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/stocks/{group}/{code}")
async def remove_stock(group: str, code: str):
    """从指定文件夹删除股票.

    Args:
        group: 文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹或股票不存在.
    """
    try:
        return watchlist.remove_stock(settings.data_dir, group, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
```

- [ ] **Step 2: scheduler._collect_codes 改为 collect_codes**

```python
    def _collect_codes(self) -> list[str]:
        """汇总本地自选（全部文件夹）代码与已有行情 key 的并集并排序返回."""
        from app.config import settings
        from app.core import watchlist

        codes = set(self.quotes.keys())
        codes.update(watchlist.collect_codes(settings.data_dir))
        return sorted(codes)
```

- [ ] **Step 3: 适配 test_api.py 与 test_core.py**

- `test_api.py`：watchlist API 用例改为分组结构（GET 返回 `{groups}`、POST groups 建组、POST stocks 加股、DELETE 删）
- `test_core.py`：`test_scheduler_collect_codes_includes_watchlist` 改为写 v2 分组文件（`{"version":2,"groups":[{"name":"A","stocks":[{"code":"000001","name":""}]}]}`），断言 `_collect_codes` 含该代码

- [ ] **Step 4: 验证**

```bash
backend/.venv/bin/pytest -q
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/routes.py backend/app/core/scheduler.py backend/tests/test_api.py backend/tests/test_core.py
git commit -m "feat: 自选文件夹分组 REST API 并接入行情/新闻采集"
```

---

### Task 3: 前端文件夹 UI

**Files:**
- Modify: `frontend/src/types.ts`、`frontend/src/api/client.ts`、`frontend/src/store.tsx`、`frontend/src/pages/Watchlist.tsx`、`frontend/src/theme.css`

**Interfaces:**
- Consumes: Task 2 的 6 个分组 REST
- Produces: `WatchGroup` 类型、store 的 `groups` 状态与 5 个操作、文件夹区块 UI

- [ ] **Step 1: types.ts 新增分组类型**

```ts
export interface WatchItem {
  code: string;
  name: string;
}
export interface WatchGroup {
  name: string;
  stocks: WatchItem[];
}
export interface WatchlistData {
  version: number;
  groups: WatchGroup[];
}
```

（保留 Quote/NewsItem/Status/WsEvent，删除原扁平 `WatchItem` 若只在 watchlist 用则保留为 WatchGroup.stocks 元素。）

- [ ] **Step 2: client.ts 分组 API**

```ts
export const getWatchlist = () => json<WatchlistData>('/api/watchlist');
export const addGroup = (name: string) =>
  json<WatchlistData>('/api/watchlist/groups', { method: 'POST', body: JSON.stringify({ name }) });
export const renameGroup = (name: string, newName: string) =>
  json<WatchlistData>(`/api/watchlist/groups/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify({ new_name: newName }),
  });
export const removeGroup = (name: string) =>
  json<WatchlistData>(`/api/watchlist/groups/${encodeURIComponent(name)}`, { method: 'DELETE' });
export const addStock = (group: string, code: string) =>
  json<WatchlistData>('/api/watchlist/stocks', { method: 'POST', body: JSON.stringify({ group, code }) });
export const removeStock = (group: string, code: string) =>
  json<WatchlistData>(`/api/watchlist/stocks/${encodeURIComponent(group)}/${code}`, { method: 'DELETE' });
```

（删除原 `addWatchlist/removeWatchlist`。）

- [ ] **Step 3: store.tsx 分组状态**

- `watchlist: WatchlistData`（初始 `{version:2, groups:[]}`）
- `addGroup/renameGroup/removeGroup/addToWatchlist(group,code)/removeFromWatchlist(group,code)` —— 调 API 后 `set({ watchlist: res })`
- `refresh()` 中 `getWatchlist()` 结果直接 set

- [ ] **Step 4: 重写 Watchlist.tsx（文件夹区块 UI）**

```tsx
import { useState } from 'react';
import PriceCard from '../components/PriceCard';
import { useApp } from '../store';

export default function Watchlist() {
  const quotes = useApp((s) => s.quotes);
  const watchlist = useApp((s) => s.watchlist);
  const addGroup = useApp((s) => s.addGroup);
  const renameGroup = useApp((s) => s.renameGroup);
  const removeGroup = useApp((s) => s.removeGroup);
  const addToWatchlist = useApp((s) => s.addToWatchlist);
  const removeFromWatchlist = useApp((s) => s.removeFromWatchlist);
  const [code, setCode] = useState('');
  const [group, setGroup] = useState('');
  const [newGroup, setNewGroup] = useState('');
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const submit = async () => {
    if (!/^\d{6}$/.test(code.trim()) || !group) return;
    await addToWatchlist(group, code.trim());
    setCode('');
  };

  return (
    <div className="page">
      <h2>自选</h2>
      <div className="watchlist-toolbar">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="输入 6 位股票代码"
          maxLength={6}
        />
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">选择文件夹</option>
          {watchlist.groups.map((g) => (
            <option key={g.name} value={g.name}>
              {g.name}
            </option>
          ))}
        </select>
        <button onClick={submit}>添加</button>
        <input
          value={newGroup}
          onChange={(e) => setNewGroup(e.target.value)}
          placeholder="新建文件夹名"
        />
        <button onClick={async () => { await addGroup(newGroup.trim()); setNewGroup(''); }}>
          新建文件夹
        </button>
      </div>
      {watchlist.groups.map((g) => (
        <section key={g.name} className="group">
          <div className="group-header" onClick={() => setCollapsed((c) => ({ ...c, [g.name]: !c[g.name] }))}>
            <span className="group-arrow">{collapsed[g.name] ? '▸' : '▾'}</span>
            <span className="group-name">{g.name}</span>
            <span className="group-count">({g.stocks.length})</span>
          </div>
          {!collapsed[g.name] && (
            <div className="grid">
              {g.stocks.map((w) => {
                const q = quotes[w.code];
                if (!q) return null;
                return (
                  <div key={w.code} className="cell">
                    <PriceCard q={q} />
                    <button
                      className="remove"
                      onClick={() => removeFromWatchlist(g.name, w.code)}
                    >
                      删除
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ))}
      {watchlist.groups.length === 0 && <div className="muted">暂无自选文件夹</div>}
    </div>
  );
}
```

> 重命名/删除文件夹按钮：在 `group-header` 内追加两个小按钮（`onClick` 用 `e.stopPropagation()` 防止触发折叠），重命名用 `window.prompt` 获取新名（简单实现）；删除用 `window.confirm` 确认。

- [ ] **Step 5: theme.css 追加分组样式**

在文件末尾追加（沿用现有 token）：

```css
.watchlist-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.watchlist-toolbar input,
.watchlist-toolbar select {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 6px 10px;
  font-size: 13px;
  font-family: var(--font-data);
}
.watchlist-toolbar button {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 6px 14px;
  cursor: pointer;
  font-size: 13px;
}
.watchlist-toolbar button:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.group {
  margin-bottom: 14px;
}
.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  user-select: none;
}
.group-arrow {
  color: var(--muted);
  font-size: 12px;
}
.group-name {
  font-weight: 600;
  font-size: 14px;
}
.group-count {
  color: var(--muted);
  font-size: 12px;
}
.group-header .group-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}
.group-header .group-actions button {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--muted);
  font-size: 12px;
  padding: 2px 8px;
  cursor: pointer;
}
.group-header .group-actions button:hover {
  color: var(--accent);
  border-color: var(--accent);
}
```

- [ ] **Step 6: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/store.tsx frontend/src/pages/Watchlist.tsx frontend/src/theme.css
git commit -m "feat: 自选页文件夹分类 UI（新建/重命名/删除/折叠）"
```

---

### Task 4: 数据预置（16 文件夹 111 股 + 代码验证）

**Files:**
- Create: `scripts/seed_watchlist.py`
- 运行后生成 `~/.investment-board/watchlist.json`（不入库）

**Interfaces:**
- Consumes: `watchlist` 模块 + 新浪行情接口
- Produces: 预置 watchlist.json（持仓 6 + 15 领域 × 7）

- [ ] **Step 1: 创建 seed_watchlist.py**

```python
"""一次性预置自选数据：持仓 + 15 领域龙头（每领域 7 只），逐只验证代码有效性.

用法: backend/.venv/bin/python scripts/seed_watchlist.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.core import watchlist  # noqa: E402
from app.config import settings  # noqa: E402

DEFAULT_GROUPS = [
    {"name": "持仓", "codes": ["600900", "601318", "000333", "002714", "600519", "002027"]},
    {"name": "银行", "codes": ["600036", "601398", "601939", "601288", "601166", "000001", "002142"]},
    {"name": "保险", "codes": ["601318", "601628", "601601", "601336", "601319", "000627", "600291"]},
    {"name": "白酒", "codes": ["600519", "000858", "000568", "600809", "002304", "000596", "603369"]},
    {"name": "家电", "codes": ["000333", "000651", "600690", "000921", "002508", "002032", "000100"]},
    {"name": "电力", "codes": ["600900", "600011", "600795", "601985", "600905", "600886", "600027"]},
    {"name": "养殖", "codes": ["002714", "300498", "000876", "002157", "002124", "002567", "300761"]},
    {"name": "传媒", "codes": ["002027", "300413", "300251", "300133", "600373", "601928", "601900"]},
    {"name": "医药", "codes": ["600276", "603259", "300760", "300015", "600436", "000538", "300122"]},
    {"name": "新能源", "codes": ["300750", "601012", "300274", "600438", "300014", "688599", "002460"]},
    {"name": "半导体", "codes": ["688981", "603501", "002371", "688012", "603986", "688008", "300661"]},
    {"name": "消费电子", "codes": ["002475", "002241", "300433", "000725", "601138", "600745", "688036"]},
    {"name": "券商", "codes": ["600030", "300059", "601688", "601211", "600999", "000776", "601995"]},
    {"name": "汽车", "codes": ["002594", "601633", "000625", "601127", "601238", "600104", "600660"]},
    {"name": "有色", "codes": ["601899", "603993", "600111", "600547", "603799", "000807", "601600"]},
    {"name": "石油石化", "codes": ["601857", "600028", "600938", "002493", "600346", "600309", "002648"]},
]


def verify_code(client: httpx.Client, code: str) -> bool:
    """用新浪行情接口验证股票代码是否有效.

    Args:
        client: httpx 客户端.
        code: 6 位股票代码.

    Returns:
        接口返回有效行情（股票名非空）返回 True.
    """
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    r = client.get(f"https://hq.sinajs.cn/list={prefix}{code}",
                   headers={"Referer": "https://finance.sina.com.cn"}, timeout=8)
    body = r.text
    # 新浪返回 var hq_str_sh600519="贵州茅台,..."；无效代码返回空引号
    return '"' in body and body.split('"')[1].strip() != ""


def main() -> None:
    """验证代码有效性并写入预置自选（跳过无效代码）."""
    client = httpx.Client()
    removed = []
    try:
        for g in DEFAULT_GROUPS:
            watchlist.add_group(settings.data_dir, g["name"])
            for code in g["codes"]:
                if verify_code(client, code):
                    watchlist.add_stock(settings.data_dir, g["name"], code)
                else:
                    removed.append(f"{g['name']}:{code}")
                    print(f"[跳过无效] {g['name']}:{code}")
    finally:
        client.close()
    data = watchlist.load_watchlist(settings.data_dir)
    total = sum(len(g["stocks"]) for g in data["groups"])
    print(f"完成：{len(data['groups'])} 个文件夹，{total} 只股票；无效剔除 {len(removed)} 只")
    if removed:
        print("剔除清单:", removed)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行预置脚本**

```bash
backend/.venv/bin/pip install httpx -q 2>/dev/null || true
backend/.venv/bin/python scripts/seed_watchlist.py
```

Expected: 打印 16 个文件夹与股票数（若个别代码无效会被剔除并列出，若某文件夹剔除后不足 7 只，核对代码并修正脚本后重跑——重跑前先删除现有 watchlist.json 避免重复）。

- [ ] **Step 3: 验证预置结果**

```bash
backend/.venv/bin/python - <<'PY'
from app.config import settings
from app.core import watchlist
data = watchlist.load_watchlist(settings.data_dir)
print("文件夹数:", len(data["groups"]))
for g in data["groups"]:
    print(f"  {g['name']}: {len(g['stocks'])} 只")
PY
```

Expected: 16 个文件夹，持仓 6 只 + 各领域 7 只（除非无效剔除）。

- [ ] **Step 4: 提交脚本**

```bash
git add scripts/seed_watchlist.py
git commit -m "chore: 自选数据预置脚本（持仓 + 15 领域龙头）"
```

---

### Task 5: 全量验收、冒烟、As-Built 与推送

**Files:**
- Modify: `README.md`（自选文件夹功能说明）、`docs/superpowers/plans/2026-08-18-watchlist-groups-plan.md`（As-Built）

- [ ] **Step 1: README 更新**

功能说明补充：自选支持文件夹分类（同花顺式，新建/重命名/删除/折叠），预置持仓 + 15 领域龙头；环境变量不变。

- [ ] **Step 2: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（test ≥23）。

- [ ] **Step 3: 手动冒烟**

1. 清理残留进程；`cd backend && (./run.sh &)` + `cd frontend && (npm run dev &)`，sleep 6
2. `curl -s http://127.0.0.1:8210/api/watchlist` → `{"version":2,"groups":[{"name":"持仓",...},...16 组]}`
3. `curl -s http://127.0.0.1:8210/api/quotes` → 含预置代码的行情（股票名已补齐）
4. 浏览器打开自选页：16 个文件夹、每文件夹行情卡、折叠/展开、新建/重命名/删除文件夹、添加/删除股票
5. `pkill -f "uvicorn app.main"; pkill -f vite`

- [ ] **Step 4: As-Built + 推送**

计划文档末尾追加 As-Built 表（Task 1-4 commit hash、验证结果、偏差——含：预置脚本剔除的无效代码清单、前端重命名用 prompt 的简化、持仓股在领域文件夹重复出现的说明、v1 迁移行为）。然后：

```bash
git add README.md docs/superpowers/plans/2026-08-18-watchlist-groups-plan.md
git commit -m "docs: 自选文件夹分类计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 5: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。

---

### As-Built（执行记录）

| 任务 | Commit | 验证结果 | 偏差 / 备注 |
|---|---|---|---|
| Task 1 后端 watchlist.py 重构为分组结构 | `8089bfd8d59739331e6cd837dcb818c722e754bd`（feat: 自选列表升级为文件夹分组结构（v2 迁移）） | `test_watchlist.py` 8 用例绿；ruff / mypy 通过 | 预期红 2 个：重写后旧 `test_api.py`（扁平 watchlist 用例）与 `test_core.py`（旧 flat 文件 collect_codes 用例）失败，属计划内过渡，Task 2 同步修复 |
| Task 2 分组 REST API + scheduler 遍历 | `e6b9d2884c16aad79a1f35d3d4d44d457ce33b39`（feat: 自选文件夹分组 REST API 并接入行情/新闻采集） | 全量 pytest 26 通过（23→26）；ruff / mypy / check_no_trade 通过 | 新增 `test_watchlist_group_api` 使测试 23→26；`routes.py` 等文件在 Task 5 收尾时经 yapf 重排通过 lint（yapf 格式偏差） |
| Task 3 前端文件夹 UI | `d5ce8945537c1db9037c4b23f3583078af9d5ad3`（feat: 自选页文件夹分类 UI（新建/重命名/删除/折叠）） | eslint / prettier / tsc / build 全绿；check_no_trade 通过 | Watchlist.tsx 新增 2 处 `// eslint-disable-next-line no-alert`（重命名/删除确认用 `window.prompt` / `window.confirm` 的简化实现） |
| Task 4 数据预置 16 组 111 股 | `7c24c91de057f3e250eb8bb6c91958b4098b7ca9`（chore: 自选数据预置脚本（持仓 + 15 领域龙头）） | 16 文件夹、持仓 6 + 15×7 = 111 只全部通过新浪接口验证 | 保险组 `000627`（西水）/`600291`（*ST西水）无效被替换为 `002423`（中粮资本）/`000987`（越秀资本）；`600745` *ST闻泰 保留（接口验证有效）；seed 脚本经 ruff auto-fix 移除计划中的 `# noqa: E402` 注释；持仓 6 只在对应领域文件夹重复出现（唯一代码 105 只） |
| Task 5 全量验收 / 冒烟 / As-Built / 推送 | 本次 docs 提交（见 Git 日志：`docs: 自选文件夹分类计划追加执行记录（as-built）`），前置 `fe1112f` chore: yapf 重排后端文件 | 全量验收全绿：check / lint（含 yapf 重排修复 4 个后端文件）/ typecheck / test 26 passed / build 成功；冒烟：16 组 watchlist、105 唯一代码行情（贵州茅台在列、股票名全补齐）、分组 CRUD + 去重 + 400 校验通过、headless 浏览器确认自选页 16 文件夹 + 111 行情卡 + 折叠交互；README 功能说明补充文件夹分类与预置数据 | Task 5 修复 Task 2 遗留的 yapf 格式问题（`routes.py`、`test_api.py`、`test_core.py`、`test_watchlist.py` 重排）；v1 扁平列表自动迁移到「未分组」文件夹（原有 v1 迁移行为保留，本次无真实 v1 数据迁移发生） |
