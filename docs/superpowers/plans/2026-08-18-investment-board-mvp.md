# 股票看板 MVP 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个开源、个人自托管的本地 Web 股票看板——通过只读方式连接同花顺账号获取自选/持仓，用公开数据源提供实时行情、分时与新闻，全程严守账号隐私与合规边界。

**Architecture:** 后端 Python/FastAPI 仅监听 127.0.0.1，采集器（THS 只读客户端 + 公开行情源 + 公开新闻源）→ asyncio 调度器 → WebSocket 推送 → React 前端。THS 客户端只读且可插拔，行情/新闻走公开源以最小化账号暴露面。凭据经 AES-256-GCM 加密存入本地 SQLite，密钥存系统 Keychain。

**Tech Stack:** Python 3.11+ / FastAPI / httpx / cryptography / keyring / pytest；React 18 / TypeScript / Vite / ECharts。

## Global Constraints

- 后端仅绑定 `127.0.0.1`，默认端口 `8210`（环境变量 `IB_PORT` 可覆盖）。
- **THS 客户端只读**：代码中禁止出现 `place_order`/`buy`/`sell`/`trade` 等方法名与下单语义依赖；CI 用黑名单扫描强制。
- 凭据加密：`AES-256-GCM`，密钥存系统 Keychain（通过 `keyring` 库），密钥永不进代码/仓库/日志。
- 限频：THS 接口调用间隔 ≥10s 且带随机抖动；公开行情 3s；新闻 60s。
- 所有外部 HTTP 调用：超时 ≤10s、重试 ≤2 次（退避）。
- 所有采集解析器均为纯函数 `parse(text) -> list[...]`，测试用 fixture 文本，**不依赖真实账号与网络**。
- 前端 UI 深色主题；界面标注行情/新闻数据来源归属。
- 每个 Task 结束时提交一次 git。

---

### Task 1: 后端脚手架 + 数据模型

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/models.py`
- Test: `backend/tests/test_models.py`
- Create: `backend/tests/__init__.py`

**Interfaces:**
- Consumes: 无（项目根目录已初始化 git）
- Produces: 数据模型 `Stock`/`Position`/`Quote`/`IntradayPoint`/`NewsItem`——所有后续任务依赖这些 dataclass 的字段名。

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "investment-board-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "httpx>=0.27",
    "cryptography>=42.0",
    "keyring>=25.0",
    "pydantic>=2.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.4"]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: 创建数据模型**

```python
# backend/app/models.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Stock:
    code: str          # "600519"
    name: str          # "贵州茅台"
    market: str = "SH"  # "SH" / "SZ"


@dataclass
class Position:
    code: str
    name: str
    quantity: int           # 持股数量(股)
    cost_price: float       # 成本价
    available: int = 0      # 可用数量
    current_price: float = 0.0
    market_value: float = 0.0
    profit: float = 0.0
    profit_pct: float = 0.0
    day_change: float = 0.0
    day_change_pct: float = 0.0


@dataclass
class Quote:
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float        # 手
    amount: float        # 元
    ts: datetime


@dataclass
class IntradayPoint:
    time: str            # "09:30"
    price: float
    avg_price: float
    volume: float


@dataclass
class NewsItem:
    id: str
    source: str          # "eastmoney" / "cls"
    title: str
    url: str
    published_at: datetime
    news_type: str       # "individual" / "global"
    related_codes: list[str] = field(default_factory=list)
    read: bool = False
```

- [ ] **Step 3: 编写测试**

```python
# backend/tests/test_models.py
from datetime import datetime

from app.models import NewsItem, Position, Quote


def test_quote_construction():
    q = Quote("600519", "贵州茅台", 1750.0, 50.0, 2.94, 1700.0, 1760.0, 1690.0,
              1700.0, 30000, 5.2e8, datetime(2026, 8, 18, 10, 0))
    assert q.change_pct == 2.94
    assert q.amount == 5.2e8


def test_position_defaults():
    p = Position("000001", "平安银行", 1000, 12.0)
    assert p.market_value == 0.0
    assert p.profit == 0.0


def test_news_item_related_codes_isolated():
    a = NewsItem("1", "eastmoney", "标题", "http://x", datetime.now(), "individual")
    b = NewsItem("2", "eastmoney", "标题2", "http://y", datetime.now(), "individual")
    assert a.related_codes == []
    assert b.related_codes == []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest -q`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add backend
git commit -m "feat: 后端脚手架与数据模型"
```

---

### Task 2: 凭据保险箱（vault）

**Files:**
- Create: `backend/app/vault/__init__.py`
- Create: `backend/app/vault/store.py`
- Test: `backend/tests/test_vault.py`

**Interfaces:**
- Consumes: 无（独立模块）
- Produces:
  - `Vault(data_dir: Path) -> Vault`
  - `vault.save_session(payload: dict) -> None`
  - `vault.load_session() -> dict | None`
  - `vault.clear() -> None`
  - `vault.is_logged_in -> bool`
  - `_get_or_create_key(service: str) -> bytes`（32 字节 AES 密钥，经 keyring 存取）

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_vault.py
from pathlib import Path

from app.vault.store import Vault


def _make_vault(tmp_path: Path, monkeypatch):
    """注入固定密钥的假 keyring，避免测试触碰系统 Keychain。"""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    monkeypatch.setattr("app.vault.store._keyring_get", lambda service, user: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda service, user, pw: None)
    return Vault(tmp_path)


def test_save_load_roundtrip(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc", "user": "u1"})
    loaded = v.load_session()
    assert loaded == {"token": "abc", "user": "u1"}


def test_ciphertext_not_plaintext(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "secret-value"})
    raw = (tmp_path / "session.enc").read_text()
    assert "secret-value" not in raw


def test_clear_removes_session(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc"})
    v.clear()
    assert not v.is_logged_in
    assert v.load_session() is None


def test_load_none_when_missing(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    assert v.load_session() is None
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_vault.py -q`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 vault**

```python
# backend/app/vault/store.py
import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SERVICE = "investment-board"
_KEYCHAIN_USER = "session"


def _keyring_get(service: str, user: str) -> str | None:
    import keyring
    return keyring.get_password(service, user)


def _keyring_set(service: str, user: str, password: str) -> None:
    import keyring
    keyring.set_password(service, user, password)


def _get_or_create_key() -> bytes:
    if os.environ.get("IB_TEST_KEYCHAIN"):
        return bytes.fromhex("00" * 32)  # 测试用固定密钥
    existing = _keyring_get(_SERVICE, _KEYCHAIN_USER)
    if existing:
        return base64.b64decode(existing)
    key = os.urandom(32)
    _keyring_set(_SERVICE, _KEYCHAIN_USER, base64.b64encode(key).decode())
    return key


class Vault:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.data_dir / "session.enc"

    def save_session(self, payload: dict) -> None:
        key = _get_or_create_key()
        nonce = os.urandom(12)
        raw = json.dumps(payload, ensure_ascii=False).encode()
        ct = AESGCM(key).encrypt(nonce, raw, None)
        self._file.write_bytes(b"v1" + nonce + ct)

    def load_session(self) -> dict | None:
        if not self._file.exists():
            return None
        blob = self._file.read_bytes()
        assert blob[:2] == b"v1"
        key = _get_or_create_key()
        nonce, ct = blob[2:14], blob[14:]
        raw = AESGCM(key).decrypt(nonce, ct, None)
        return json.loads(raw.decode())

    def clear(self) -> None:
        self._file.unlink(missing_ok=True)

    @property
    def is_logged_in(self) -> bool:
        return self._file.exists()
```

```python
# backend/app/vault/__init__.py
from app.vault.store import Vault

__all__ = ["Vault"]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_vault.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/vault backend/tests/test_vault.py
git commit -m "feat: 凭据保险箱（AES-256-GCM + Keychain）"
```

---

### Task 3: 行情服务（新浪 + 腾讯，去重合并，源切换）

**Files:**
- Create: `backend/app/market/__init__.py`
- Create: `backend/app/market/parsers.py`
- Create: `backend/app/market/service.py`
- Test: `backend/tests/test_market.py`

**Interfaces:**
- Consumes: Task 1 的 `Quote` / `IntradayPoint`
- Produces:
  - `parse_sina(text: str) -> Quote`
  - `parse_tencent(text: str) -> Quote`
  - `parse_sina_intraday(text: str) -> list[IntradayPoint]`
  - `MarketService(client: httpx.AsyncClient, ...) -> MarketService`
  - `market.fetch_quotes(codes: list[str]) -> dict[str, Quote]`（键为代码；去重；主源失败自动切备源）
  - `market.fetch_intraday(code: str) -> list[IntradayPoint]`
  - `market.primary_source / market.fallback_source`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_market.py
import httpx
import pytest
from respx import MockRouter

from app.market.parsers import parse_sina, parse_sina_intraday, parse_tencent
from app.market.service import MarketService

SINA_LINE = ('var hq_str_sh600519="贵州茅台,1700.00,1700.00,1750.00,'
             '1760.00,1690.00,1750.00,1751.00,30000,520000000.00,'
             '...,2026-08-18,10:30:00,00";')
TENCENT_LINE = ('v_sh600519="1~贵州茅台~600519~1750.00~1700.00~1700.00~'
                '30000~52000~...~50.00~2.94~1760.00~1690.00~...";')


def test_parse_sina_quote():
    q = parse_sina(SINA_LINE)
    assert q.code == "600519"
    assert q.name == "贵州茅台"
    assert q.price == 1750.0
    assert q.prev_close == 1700.0
    assert q.change == 50.0
    assert round(q.change_pct, 2) == 2.94


def test_parse_tencent_quote():
    q = parse_tencent(TENCENT_LINE)
    assert q.code == "600519"
    assert q.price == 1750.0
    assert q.change_pct == 2.94


def test_parse_sina_intraday():
    text = '1 09:30,1700.00,1700.00,100\n2 09:31,1701.00,1700.50,200\n'
    pts = parse_sina_intraday(text)
    assert len(pts) == 2
    assert pts[0].time == "09:30"
    assert pts[0].price == 1700.0


@pytest.mark.asyncio
async def test_fetch_quotes_dedupes_and_merges(respx_mock: MockRouter):
    respx_mock.get("https://hq.sinajs.cn/list=sh600519,sz000001").mock(
        return_value=httpx.Response(200, text=SINA_LINE))
    svc = MarketService(httpx.AsyncClient())
    quotes = await svc.fetch_quotes(["600519", "600519", "000001", "000001"])
    assert set(quotes) == {"600519", "000001"}
    assert svc.primary_source == "sina"


@pytest.mark.asyncio
async def test_fetch_quotes_falls_back_when_sina_fails(respx_mock: MockRouter):
    respx_mock.get("https://hq.sinajs.cn/list=sh600519").mock(
        return_value=httpx.Response(500))
    respx_mock.get("https://qt.gtimg.cn/q=sh600519").mock(
        return_value=httpx.Response(200, text=TENCENT_LINE))
    svc = MarketService(httpx.AsyncClient())
    quotes = await svc.fetch_quotes(["600519"])
    assert quotes["600519"].name == "贵州茅台"
    assert svc.primary_source == "tencent"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pip install -e ".[dev]" && .venv/bin/pip install respx && .venv/bin/pytest tests/test_market.py -q`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现解析器与服务**

```python
# backend/app/market/parsers.py
import re
from datetime import datetime

from app.models import IntradayPoint, Quote


def _today() -> datetime:
    return datetime.now().replace(microsecond=0)


def parse_sina(text: str) -> Quote:
    m = re.search(r'="(.*)";', text)
    if not m:
        raise ValueError("bad sina payload")
    f = m.group(1).split(",")
    prev_close = float(f[2])
    price = float(f[3])
    return Quote(
        code=text.split("hq_str_")[1][:6],
        name=f[0], price=price,
        change=round(price - prev_close, 3),
        change_pct=round((price - prev_close) / prev_close * 100, 2),
        open=float(f[1]), high=float(f[4]), low=float(f[5]),
        prev_close=prev_close, volume=float(f[8]) / 100,
        amount=float(f[9]), ts=_today(),
    )


def parse_tencent(text: str) -> Quote:
    m = re.search(r'="(.*)";', text)
    f = m.group(1).split("~")
    prev_close = float(f[4])
    price = float(f[3])
    return Quote(
        code=f[2], name=f[1], price=price,
        change=round(price - prev_close, 3),
        change_pct=float(f[32]),
        open=float(f[5]), high=float(f[33]), low=float(f[34]),
        prev_close=prev_close, volume=float(f[6]), amount=float(f[37]) * 1e4,
        ts=_today(),
    )


def parse_sina_intraday(text: str) -> list[IntradayPoint]:
    pts = []
    for line in text.strip().splitlines():
        if "=" in line or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 4:
            continue
        pts.append(IntradayPoint(
            time=parts[1], price=float(parts[2]),
            avg_price=float(parts[3]),
            volume=float(parts[4]) if len(parts) > 4 else 0.0,
        ))
    return pts
```

```python
# backend/app/market/service.py
import logging

import httpx

from app.market.parsers import parse_sina, parse_sina_intraday, parse_tencent
from app.models import IntradayPoint, Quote

logger = logging.getLogger(__name__)

SINA_QUOTE_URL = "https://hq.sinajs.cn/list={codes}"
SINA_INTRA = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{c}.html="
              "/CN_MarketDataService.getKLineData?symbol={c}&scale=60&ma=no&datalen=1")
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={codes}"


def _normalize(code: str) -> str:
    # "600519" -> "sh600519", "000001" -> "sz000001"
    return ("sh" if code.startswith(("6", "9")) else "sz") + code


def _split_codes(codes: list[str]) -> str:
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(_normalize(c))
    return ",".join(out)


class MarketService:
    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        self._client = client
        self._timeout = timeout
        self.primary_source = "sina"
        self.fallback_source = "tencent"

    async def fetch_quotes(self, codes: list[str]) -> dict[str, Quote]:
        query = _split_codes(codes)
        if not query:
            return {}
        for source, url in ((self.primary_source, SINA_QUOTE_URL),
                            (self.fallback_source, TENCENT_QUOTE_URL)):
            try:
                r = await self._client.get(
                    url.format(codes=query), timeout=self._timeout,
                    headers={"Referer": "https://finance.sina.com.cn"})
                r.raise_for_status()
                return self._parse_all(source, r.text, codes)
            except Exception as e:
                logger.warning("行情源 %s 失败，切换: %s", source, e)
                self.primary_source, self.fallback_source = (
                    self.fallback_source, self.primary_source)
        return {}

    def _parse_all(self, source: str, text: str, codes: list[str]) -> dict[str, Quote]:
        result: dict[str, Quote] = {}
        parser = parse_sina if source == "sina" else parse_tencent
        for line in text.strip().splitlines():
            if '="' not in line:
                continue
            try:
                q = parser(line)
                result[q.code] = q
            except Exception:
                continue
        return result

    async def fetch_intraday(self, code: str) -> list[IntradayPoint]:
        try:
            r = await self._client.get(SINA_INTRA.format(c=code),
                                       timeout=self._timeout)
            r.raise_for_status()
            return parse_sina_intraday(r.text)
        except Exception as e:
            logger.warning("分时获取失败 %s: %s", code, e)
            return []
```

```python
# backend/app/market/__init__.py
from app.market.service import MarketService

__all__ = ["MarketService"]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_market.py -q`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/market backend/tests/test_market.py
git commit -m "feat: 行情服务（新浪/腾讯，去重合并，源切换）"
```

---

### Task 4: 新闻服务（东财公告 + 财联社电报，去重与代码匹配）

**Files:**
- Create: `backend/app/news/__init__.py`
- Create: `backend/app/news/parsers.py`
- Create: `backend/app/news/service.py`
- Test: `backend/tests/test_news.py`

**Interfaces:**
- Consumes: Task 1 的 `NewsItem` / `Stock`
- Produces:
  - `parse_eastmoney(text: str) -> list[NewsItem]`（个股公告，`news_type="individual"`）
  - `parse_cls(text: str) -> list[NewsItem]`（全局快讯，`news_type="global"`）
  - `NewsService(client, ...) -> NewsService`
  - `news.fetch_individual(codes: list[str]) -> list[NewsItem]`
  - `news.fetch_global() -> list[NewsItem]`
  - `news.dedupe(items: list[NewsItem], seen_ids: set[str]) -> list[NewsItem]`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_news.py
from datetime import datetime

import httpx
import pytest
from respx import MockRouter

from app.models import NewsItem
from app.news.parsers import parse_cls, parse_eastmoney
from app.news.service import NewsService

EM_FIXTURE = """{
  "data": {
    "list": [
      {"art_code": "A001", "notice_title": "贵州茅台2026年半年度报告",
       "notice_date": "2026-08-18 09:00:00",
       "column_code": "sz000001",
       "art_url": "http://static.cninfo.com.cn/xxx.pdf"}
    ]
  }
}"""

CLS_FIXTURE = """{
  "data": {
    "roll_data": [
      {"id": 1001, "title": "【快讯】两市成交额突破万亿",
       "ctime": "1723950000",
       "share_url": "https://www.cls.cn/detail/1001"}
    ]
  }
}"""


def test_parse_eastmoney():
    items = parse_eastmoney(EM_FIXTURE)
    assert items[0].news_type == "individual"
    assert items[0].related_codes == ["000001"]
    assert items[0].source == "eastmoney"


def test_parse_cls():
    items = parse_cls(CLS_FIXTURE)
    assert items[0].news_type == "global"
    assert items[0].source == "cls"


def _stub(i: str) -> NewsItem:
    return NewsItem(i, "cls", "t", "u", datetime.now(), "global")


def test_dedupe_keeps_new():
    svc = NewsService(httpx.AsyncClient())
    new = svc.dedupe([_stub("1"), _stub("2")], seen_ids={"1"})
    assert [i.id for i in new] == ["2"]
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_news.py -q`
Expected: FAIL

- [ ] **Step 3: 实现解析器与服务**

```python
# backend/app/news/parsers.py
import json
from datetime import datetime

from app.models import NewsItem


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace(" ", "T"))


def parse_eastmoney(text: str) -> list[NewsItem]:
    data = json.loads(text)
    out = []
    for item in data.get("data", {}).get("list", []):
        code = item.get("column_code", "").replace("sz", "").replace("sh", "")
        out.append(NewsItem(
            id=item.get("art_code", ""),
            source="eastmoney",
            title=item.get("notice_title", ""),
            url=item.get("art_url", ""),
            published_at=_ts(item.get("notice_date", "")),
            news_type="individual",
            related_codes=[code] if code else [],
        ))
    return out


def parse_cls(text: str) -> list[NewsItem]:
    data = json.loads(text)
    out = []
    for item in data.get("data", {}).get("roll_data", []):
        out.append(NewsItem(
            id=str(item.get("id", "")),
            source="cls",
            title=item.get("title", ""),
            url=item.get("share_url", ""),
            published_at=datetime.fromtimestamp(int(item.get("ctime", "0"))),
            news_type="global",
        ))
    return out
```

```python
# backend/app/news/service.py
import logging

import httpx

from app.models import NewsItem
from app.news.parsers import parse_cls, parse_eastmoney

logger = logging.getLogger(__name__)

EM_NOTICE_URL = ("https://np-anotice-stock.eastmoney.com/api/security/ann"
                 "?sr=-1&page_size=20&page_index=1&ann_type=A&client_source=web&"
                 "stock_list={code}")
CLS_TELEGRAPH_URL = "https://www.cls.cn/nodeapi/telegraphList?app=CailianpressWeb"


class NewsService:
    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        self._client = client
        self._timeout = timeout

    async def fetch_individual(self, codes: list[str]) -> list[NewsItem]:
        out: list[NewsItem] = []
        for code in codes:
            try:
                r = await self._client.get(
                    EM_NOTICE_URL.format(code=code), timeout=self._timeout,
                    headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                for item in parse_eastmoney(r.text):
                    if code not in item.related_codes:
                        item.related_codes = [code]
                    out.append(item)
            except Exception as e:
                logger.warning("个股公告获取失败 %s: %s", code, e)
        return out

    async def fetch_global(self) -> list[NewsItem]:
        try:
            r = await self._client.get(
                CLS_TELEGRAPH_URL, timeout=self._timeout,
                headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return parse_cls(r.text)
        except Exception as e:
            logger.warning("全局快讯获取失败: %s", e)
            return []

    def dedupe(self, items: list[NewsItem], seen_ids: set[str]) -> list[NewsItem]:
        fresh = [i for i in items if i.id not in seen_ids]
        seen_ids.update(i.id for i in items)
        return fresh
```

```python
# backend/app/news/__init__.py
from app.news.service import NewsService

__all__ = ["NewsService"]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_news.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/news backend/tests/test_news.py
git commit -m "feat: 新闻服务（东财公告+财联社，去重与代码匹配）"
```

---

### Task 5: THS 只读客户端（抽象基类 + 解析器 + 扫码登录客户端）

**Files:**
- Create: `backend/app/ths_client/__init__.py`
- Create: `backend/app/ths_client/base.py`
- Create: `backend/app/ths_client/parsers.py`
- Create: `backend/app/ths_client/web_client.py`
- Create: `backend/app/ths_client/README.md`
- Test: `backend/tests/test_ths_client.py`

**Interfaces:**
- Consumes: Task 1 的 `Stock` / `Position`；Task 2 的 `Vault`
- Produces:
  - `class ThsAdapter`（抽象基类）：
    - `async login_qrcode() -> dict`
    - `async poll_login() -> bool`
    - `async query_watchlist() -> list[Stock]`
    - `async query_positions() -> list[Position]`
    - `async refresh_session() -> bool`
    - `is_logged_in -> bool`
    - `async logout() -> None`
  - `parse_watchlist(text: str) -> list[Stock]`（纯函数）
  - `parse_positions(text: str) -> list[Position]`（纯函数）
  - `ThsWebClient(vault, client, endpoint_prefix) -> ThsWebClient`

**合规硬约束（本任务）：** 只实现查询/登录方法，**禁止**创建任何下单/撤单/委托类方法；`web_client.py` 顶部写入"只读，禁止添加交易方法"注释。

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_ths_client.py
from pathlib import Path

import httpx
import pytest
from respx import MockRouter

from app.ths_client.base import ThsAdapter
from app.ths_client.parsers import parse_positions, parse_watchlist
from app.ths_client.web_client import ThsWebClient

WATCHLIST = """[
  {"code": "600519", "name": "贵州茅台", "market": "SH"},
  {"code": "000001", "name": "平安银行", "market": "SZ"}
]"""

POSITIONS = """[
  {"code": "600519", "name": "贵州茅台", "amount": 100, "cost": 1600.0, "enable_amount": 100},
  {"code": "000001", "name": "平安银行", "amount": 2000, "cost": 11.0, "enable_amount": 2000}
]"""


def test_parse_watchlist():
    stocks = parse_watchlist(WATCHLIST)
    assert stocks[0].code == "600519"
    assert stocks[0].name == "贵州茅台"


def test_parse_positions():
    pos = parse_positions(POSITIONS)
    assert pos[0].quantity == 100
    assert pos[0].cost_price == 1600.0


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        ThsAdapter()  # 抽象类不可实例化


@pytest.mark.asyncio
async def test_web_client_login_flow(tmp_path, monkeypatch, respx_mock: MockRouter):
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    from app.vault.store import Vault
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)

    respx_mock.get("https://ths.test/qrcode").mock(
        return_value=httpx.Response(200, json={"data": {"qrcode": "qr-data"}}))
    respx_mock.get("https://ths.test/poll").mock(
        return_value=httpx.Response(200, json={"data": {"status": 1, "token": "t1"}}))

    vault = Vault(tmp_path)
    client = ThsWebClient(vault, httpx.AsyncClient(),
                          endpoint_prefix="https://ths.test")
    await client.login_qrcode()
    ok = await client.poll_login()
    assert ok is True
    assert client.is_logged_in
    assert vault.load_session()["token"] == "t1"


def test_web_client_has_no_trade_methods():
    forbidden = ["place_order", "buy", "sell", "trade", "order"]
    src = (Path(__file__).resolve().parent.parent
           / "app/ths_client/web_client.py")
    text = src.read_text()
    for word in forbidden:
        assert word not in text, f"发现交易语义方法: {word}"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_ths_client.py -q`
Expected: FAIL

- [ ] **Step 3: 实现 base / parsers / web_client**

```python
# backend/app/ths_client/base.py
from abc import ABC, abstractmethod

from app.models import Position, Stock


class ThsAdapter(ABC):
    """同花顺只读客户端抽象接口。禁止添加任何交易类方法。"""

    @abstractmethod
    async def login_qrcode(self) -> dict: ...

    @abstractmethod
    async def poll_login(self) -> bool: ...

    @abstractmethod
    async def query_watchlist(self) -> list[Stock]: ...

    @abstractmethod
    async def query_positions(self) -> list[Position]: ...

    @abstractmethod
    async def refresh_session(self) -> bool: ...

    @property
    @abstractmethod
    def is_logged_in(self) -> bool: ...

    @abstractmethod
    async def logout(self) -> None: ...
```

```python
# backend/app/ths_client/parsers.py
import json

from app.models import Position, Stock


def parse_watchlist(text: str) -> list[Stock]:
    data = json.loads(text)
    stocks = []
    for item in data:
        stocks.append(Stock(
            code=item["code"], name=item["name"],
            market=item.get("market", "SH"),
        ))
    return stocks


def parse_positions(text: str) -> list[Position]:
    data = json.loads(text)
    positions = []
    for item in data:
        positions.append(Position(
            code=item["code"], name=item["name"],
            quantity=int(item["amount"]), cost_price=float(item["cost"]),
            available=int(item.get("enable_amount", 0)),
        ))
    return positions
```

```python
# backend/app/ths_client/web_client.py
"""同花顺网页版只读客户端（逆向接口实现）。

⚠️ 只读约束：本模块只负责登录与查询（自选/持仓）。严禁添加下单、撤单、
委托、交易等任何方法。接口 endpoint 的逆向值与字段说明见 README.md。
"""
import json
import logging

import httpx

from app.models import Position, Stock
from app.ths_client.base import ThsAdapter
from app.ths_client.parsers import parse_positions, parse_watchlist
from app.vault.store import Vault

logger = logging.getLogger(__name__)


class ThsWebClient(ThsAdapter):
    def __init__(self, vault: Vault, client: httpx.AsyncClient,
                 endpoint_prefix: str, timeout: float = 10.0):
        self._vault = vault
        self._client = client
        self._prefix = endpoint_prefix
        self._timeout = timeout
        self._pending_qr = None

    @property
    def is_logged_in(self) -> bool:
        return self._vault.is_logged_in

    async def _get_json(self, path: str, **params) -> dict:
        headers = {}
        session = self._vault.load_session()
        if session and session.get("token"):
            headers["Authorization"] = f"Bearer {session['token']}"
        r = await self._client.get(self._prefix + path, params=params,
                                   headers=headers, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    async def login_qrcode(self) -> dict:
        data = await self._get_json("/qrcode")
        self._pending_qr = data.get("data", {})
        return {"qrcode_data": self._pending_qr.get("qrcode", "")}

    async def poll_login(self) -> bool:
        data = await self._get_json("/poll")
        status = data.get("data", {}).get("status", 0)
        if status == 1:
            token = data["data"].get("token")
            self._vault.save_session({
                "token": token,
                "user": data["data"].get("user"),
            })
            return True
        return False

    async def query_watchlist(self) -> list[Stock]:
        data = await self._get_json("/watchlist")
        return parse_watchlist(_json_text(data))

    async def query_positions(self) -> list[Position]:
        data = await self._get_json("/positions")
        return parse_positions(_json_text(data))

    async def refresh_session(self) -> bool:
        try:
            await self._get_json("/session/check")
            return True
        except Exception as e:
            logger.warning("会话保活失败: %s", e)
            return False

    async def logout(self) -> None:
        self._vault.clear()


def _json_text(data: dict) -> str:
    return json.dumps(data.get("data", []), ensure_ascii=False)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_ths_client.py -q`
Expected: 5 passed

- [ ] **Step 5: 记录逆向接口契约并提交**

`backend/app/ths_client/README.md` 记录：endpoint 前缀、`/qrcode` `/poll` `/watchlist` `/positions` `/session/check` 的请求与响应契约、字段来源说明，并注明"需通过浏览器开发者工具抓包核实，若有出入以实测为准"。

```bash
git add backend/app/ths_client backend/tests/test_ths_client.py
git commit -m "feat: THS 只读客户端（扫码登录+自选/持仓查询）"
```

---

### Task 6: 持仓盈亏计算 + 事件总线 + 调度器

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/portfolio.py`
- Create: `backend/app/core/events.py`
- Create: `backend/app/core/scheduler.py`
- Test: `backend/tests/test_core.py`

**Interfaces:**
- Consumes: Task 1 模型；Task 3 `MarketService.fetch_quotes`；Task 5 `ThsAdapter`
- Produces:
  - `compute_positions(positions, quotes) -> list[Position]`
  - `class EventBus`：`subscribe(type, cb)` / `publish(type, payload)`
  - `class EventType` 常量：`QUOTES/POSITIONS/NEWS/THS_STATUS/SOURCE_STATUS`
  - `class Scheduler`：`start()` / `stop()`；采集函数经构造器注入（便于测试）
  - `Scheduler.quotes/positions/news/seen_news` 缓存

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_core.py
import asyncio
from datetime import datetime

import pytest

from app.core.events import EventBus
from app.core.portfolio import compute_positions
from app.core.scheduler import Scheduler
from app.models import Position, Quote


def test_compute_positions():
    p = Position("600519", "贵州茅台", 100, 1600.0, available=100)
    q = Quote("600519", "贵州茅台", 1750.0, 50.0, 3.125,
              1700.0, 1760.0, 1690.0, 1700.0, 0, 0, datetime.now())
    out = compute_positions([p], {"600519": q})
    assert out[0].current_price == 1750.0
    assert out[0].market_value == 175000.0
    assert out[0].profit == 15000.0
    assert round(out[0].profit_pct, 2) == 9.38


def test_compute_positions_keeps_missing_quote():
    p = Position("000001", "平安银行", 100, 10.0)
    out = compute_positions([p], {})
    assert out[0].profit == 0.0


def test_event_bus_dispatch():
    bus = EventBus()
    got = []
    bus.subscribe("QUOTES", lambda p: got.append(p))
    bus.publish("QUOTES", {"x": 1})
    assert got == [{"x": 1}]


@pytest.mark.asyncio
async def test_scheduler_quotes_loop_publishes():
    async def fetch_quotes(codes):
        return {"600519": Quote("600519", "贵州茅台", 1.0, 0, 0,
                                1.0, 1.0, 1.0, 1.0, 0, 0, datetime.now())}

    bus = EventBus()
    published = []
    bus.subscribe("quotes", lambda p: published.append(p))
    sched = Scheduler(bus, quotes_fetcher=fetch_quotes, quotes_interval=0.05)
    sched.start()
    await asyncio.sleep(0.15)
    sched.stop()
    assert len(published) >= 1
    assert "600519" in published[0]
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_core.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# backend/app/core/portfolio.py
from app.models import Position, Quote


def compute_positions(positions: list[Position],
                      quotes: dict[str, Quote]) -> list[Position]:
    out = []
    for p in positions:
        q = quotes.get(p.code)
        if q:
            p.current_price = q.price
            p.market_value = round(p.quantity * q.price, 2)
            p.profit = round((q.price - p.cost_price) * p.quantity, 2)
            p.profit_pct = round((q.price - p.cost_price) / p.cost_price * 100, 2)
            p.day_change = round(q.change * p.quantity, 2)
            p.day_change_pct = q.change_pct
        out.append(p)
    return out
```

```python
# backend/app/core/events.py
from typing import Any, Callable

Sub = Callable[[Any], None]


class EventType:
    QUOTES = "quotes"
    POSITIONS = "positions"
    NEWS = "news"
    THS_STATUS = "ths_status"
    SOURCE_STATUS = "source_status"


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Sub]] = {}

    def subscribe(self, event_type: str, cb: Sub) -> None:
        self._subs.setdefault(event_type, []).append(cb)

    def publish(self, event_type: str, payload: Any) -> None:
        for cb in self._subs.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass
```

```python
# backend/app/core/scheduler.py
import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.core.events import EventBus, EventType
from app.models import NewsItem, Position, Quote

logger = logging.getLogger(__name__)

FETCHER = Callable[[list[str]], Awaitable[dict[str, Quote]]]


class Scheduler:
    def __init__(self, bus: EventBus,
                 quotes_fetcher: FETCHER,
                 positions_fetcher=None,
                 news_fetcher=None,
                 quotes_interval: float = 3.0,
                 positions_interval: float = 10.0,
                 news_interval: float = 60.0,
                 ths_adapter=None):
        self.bus = bus
        self._quotes_fetcher = quotes_fetcher
        self._positions_fetcher = positions_fetcher
        self._news_fetcher = news_fetcher
        self._ths = ths_adapter
        self.quotes_interval = quotes_interval
        self.positions_interval = positions_interval
        self.news_interval = news_interval
        self.quotes: dict[str, Quote] = {}
        self.positions: list[Position] = []
        self.news: list[NewsItem] = []
        self.seen_news: set[str] = set()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def _spawn(self, coro) -> asyncio.Task:
        return asyncio.create_task(coro)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            self._spawn(self._quotes_loop()),
            self._spawn(self._positions_loop()),
            self._spawn(self._news_loop()),
        ]

    def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()

    def _collect_codes(self) -> list[str]:
        codes = set(self.quotes.keys())
        for p in self.positions:
            codes.add(p.code)
        return sorted(codes)

    async def _quotes_loop(self):
        while self._running:
            try:
                codes = self._collect_codes()
                if codes:
                    self.quotes = await self._quotes_fetcher(codes)
                    self.bus.publish(EventType.QUOTES, self.quotes)
            except Exception as e:
                logger.warning("行情循环异常: %s", e)
            await asyncio.sleep(self.quotes_interval + random.uniform(0, 0.5))

    async def _positions_loop(self):
        while self._running:
            if self._positions_fetcher and self._ths and self._ths.is_logged_in:
                try:
                    self.positions = await self._positions_fetcher()
                    enriched = self._apply_quotes(self.positions)
                    self.bus.publish(EventType.POSITIONS, enriched)
                except Exception as e:
                    logger.warning("持仓循环异常: %s", e)
                    self.bus.publish(EventType.THS_STATUS,
                                     {"status": "error", "message": str(e)})
            await asyncio.sleep(self.positions_interval)

    def _apply_quotes(self, pos: list[Position]) -> list[Position]:
        from app.core.portfolio import compute_positions
        return compute_positions(pos, self.quotes)

    async def _news_loop(self):
        while self._running:
            if self._news_fetcher:
                try:
                    items = await self._news_fetcher(self._collect_codes())
                    fresh = [i for i in items if i.id not in self.seen_news]
                    self.seen_news.update(i.id for i in items)
                    if fresh:
                        self.news = fresh + self.news
                        self.news = self.news[:200]
                        self.bus.publish(EventType.NEWS, self.news)
                except Exception as e:
                    logger.warning("新闻循环异常: %s", e)
            await asyncio.sleep(self.news_interval)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_core.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/core backend/tests/test_core.py
git commit -m "feat: 持仓盈亏计算、事件总线与调度器"
```

---

### Task 7: REST + WebSocket API

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/api/ws.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: Task 2 `Vault`、Task 5 `ThsAdapter`、Task 6 `Scheduler`/`EventBus`
- Produces（REST，前缀 `/api`）:
  - `GET /api/status` → `{"logged_in": bool, "sources": {...}, "ths": {...}}`
  - `POST /api/login/qrcode` → `{"qrcode_data": str}`
  - `POST /api/login/poll` → `{"ok": bool}`
  - `POST /api/logout` → `{"ok": true}`
  - `GET /api/quotes` → `dict[str, Quote]`
  - `GET /api/positions` → `list[Position]`
  - `GET /api/news?type=individual|global|all` → `list[NewsItem]`
  - `POST /api/news/{news_id}/read` → `{"ok": true}`
- Produces（WS，路径 `/ws`）：`QUOTES/POSITIONS/NEWS/THS_STATUS/SOURCE_STATUS` 事件推送 `{"type": ..., "data": ...}`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_api.py
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.api.ws import ws_router
from app.core.events import EventBus
from app.vault.store import Vault


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    app = FastAPI()
    vault = Vault(tmp_path)
    app.state.vault = vault
    app.state.bus = EventBus()
    app.state.scheduler = None
    app.state.ths = None
    app.include_router(router, prefix="/api")
    app.include_router(ws_router)
    return app


@pytest.mark.asyncio
async def test_status_and_logout(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.get("/api/status")
        assert r.status_code == 200
        body = r.json()
        assert body["logged_in"] is False
        assert "sources" in body

        r2 = await c.post("/api/logout")
        assert r2.json() == {"ok": True}


@pytest.mark.asyncio
async def test_mark_news_read(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.post("/api/news/abc/read")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_api.py -q`
Expected: FAIL

- [ ] **Step 3: 实现 API 层**

```python
# backend/app/api/routes.py
from fastapi import APIRouter, Request

from app.core.portfolio import compute_positions

router = APIRouter()


@router.get("/status")
async def status(request: Request):
    vault = request.app.state.vault
    return {
        "logged_in": vault.is_logged_in,
        "sources": {"market": "ok", "news": "ok"},
        "ths": {"status": "ok" if vault.is_logged_in else "not_logged_in"},
    }


@router.post("/login/qrcode")
async def login_qrcode(request: Request):
    ths = request.app.state.ths
    return await ths.login_qrcode()


@router.post("/login/poll")
async def login_poll(request: Request):
    ths = request.app.state.ths
    return {"ok": await ths.poll_login()}


@router.post("/logout")
async def logout(request: Request):
    ths = request.app.state.ths
    if ths:
        await ths.logout()
    return {"ok": True}


@router.get("/quotes")
async def get_quotes(request: Request):
    sched = request.app.state.scheduler
    return sched.quotes if sched else {}


@router.get("/positions")
async def get_positions(request: Request):
    sched = request.app.state.scheduler
    if not sched:
        return []
    return compute_positions(sched.positions, sched.quotes)


@router.get("/news")
async def get_news(request: Request, type: str = "all"):
    sched = request.app.state.scheduler
    if not sched:
        return []
    items = sched.news
    if type in ("individual", "global"):
        items = [i for i in items if i.news_type == type]
    return items


@router.post("/news/{news_id}/read")
async def mark_read(request: Request, news_id: str):
    sched = request.app.state.scheduler
    if sched:
        for item in sched.news:
            if item.id == news_id:
                item.read = True
    return {"ok": True}
```

```python
# backend/app/api/ws.py
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import EventType

logger = logging.getLogger(__name__)
ws_router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event_type: str, payload):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json({"type": event_type, "data": payload})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    bus = ws.app.state.bus  # 直接从 app.state 取，避免 WebSocket 的 Depends 坑
    await manager.connect(ws)
    events = (EventType.QUOTES, EventType.POSITIONS, EventType.NEWS,
              EventType.THS_STATUS, EventType.SOURCE_STATUS)
    subs = [bus.subscribe(et, lambda p, et=et: asyncio.create_task(
        manager.broadcast(et, p))) for et in events]
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    finally:
        for sub in subs:
            pass  # 连接关闭即断开广播；事件总线订阅随连接生命周期释放
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/bin/pytest tests/test_api.py -q`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/api backend/tests/test_api.py
git commit -m "feat: REST 与 WebSocket API"
```

---

### Task 8: 应用组装（main.py）与配置

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/run.sh`
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: Task 2-7 全部
- Produces: `app.main:app`（FastAPI 实例）；`run.sh` 一键启动

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/test_main.py
def test_app_importable():
    from app.main import app
    assert app.title == "Investment Board"


def test_default_port():
    import os
    os.environ.pop("IB_PORT", None)
    from app.config import settings
    assert settings.port == 8210
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_main.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# backend/app/config.py
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8210
    data_dir: Path = Path.home() / ".investment-board"
    ths_endpoint_prefix: str = "https://eq.10jqka.com.cn"
    quotes_interval: float = 3.0
    positions_interval: float = 10.0
    news_interval: float = 60.0


settings = Settings()
settings.port = int(os.environ.get("IB_PORT", settings.port))
settings.data_dir = Path(os.environ.get("IB_DATA_DIR", str(settings.data_dir)))
settings.ths_endpoint_prefix = os.environ.get(
    "IB_THS_ENDPOINT", settings.ths_endpoint_prefix)
```

```python
# backend/app/main.py
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.ws import ws_router
from app.config import settings
from app.core.events import EventBus
from app.core.scheduler import Scheduler
from app.market.service import MarketService
from app.news.service import NewsService
from app.ths_client.web_client import ThsWebClient
from app.vault.store import Vault

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient()
    vault = Vault(settings.data_dir)
    market = MarketService(client)
    news = NewsService(client)
    ths = ThsWebClient(vault, client, settings.ths_endpoint_prefix)
    bus = EventBus()

    async def positions_fetcher():
        if ths.is_logged_in:
            return await ths.query_positions()
        return []

    async def news_fetcher(codes):
        ind = await news.fetch_individual(codes) if ths.is_logged_in else []
        glb = await news.fetch_global()
        return ind + glb

    sched = Scheduler(
        bus,
        quotes_fetcher=market.fetch_quotes,
        positions_fetcher=positions_fetcher,
        news_fetcher=news_fetcher,
        quotes_interval=settings.quotes_interval,
        positions_interval=settings.positions_interval,
        news_interval=settings.news_interval,
        ths_adapter=ths,
    )
    app.state.vault = vault
    app.state.ths = ths
    app.state.bus = bus
    app.state.scheduler = sched
    sched.start()
    yield
    sched.stop()
    await client.aclose()


app = FastAPI(title="Investment Board", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")
app.include_router(ws_router)
```

```bash
# backend/run.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port "${IB_PORT:-8210}"
```

- [ ] **Step 4: 运行测试验证通过 + 冒烟启动**

Run:
```bash
cd backend && chmod +x run.sh
.venv/bin/pytest tests/test_main.py -q
timeout 5 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8210 || true
```
Expected: 2 passed；uvicorn 正常启动无 ImportError（timeout 正常杀进程，退出码 124 属预期）

- [ ] **Step 5: 提交**

```bash
git add backend/app/main.py backend/app/config.py backend/run.sh backend/tests/test_main.py
git commit -m "feat: 应用组装与配置"
```

---

### Task 9: 前端脚手架 + 数据层（类型 / API / WebSocket / store）

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/ws.ts`
- Create: `frontend/src/store.tsx`
- Create: `frontend/src/theme.css`

**Interfaces:**
- Consumes: 后端 REST/WS 契约（Task 7）
- Produces:
  - `types.ts`：`Quote`/`Position`/`NewsItem`/`Status` 接口（字段与后端一致）
  - `client.ts`：`getStatus()` / `startLogin()` / `pollLogin()` / `logout()` / `getQuotes()` / `getPositions()` / `getNews(type)` / `markNewsRead(id)`
  - `ws.ts`：`connectWS(onEvent) => () => void`（自动重连）
  - `store.tsx`：`useApp()`，提供 `quotes/positions/news/status/connected` 及 actions

- [ ] **Step 1: 创建脚手架文件**

```bash
mkdir -p frontend/src/api frontend/src/pages frontend/src/components
```

`frontend/package.json`：

```json
{
  "name": "investment-board-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "echarts": "^5.5.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zustand": "^4.5.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0"
  }
}
```

`frontend/vite.config.ts`：

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8210', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8210', ws: true },
    },
  },
})
```

`frontend/tsconfig.json`（简化版，可改用 `tsc --init` 生成后合并）:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

- [ ] **Step 2: 编写类型与 API 客户端**

```ts
// frontend/src/types.ts
export interface Quote {
  code: string; name: string; price: number; change: number; change_pct: number
  open: number; high: number; low: number; prev_close: number
  volume: number; amount: number; ts: string
}
export interface Position {
  code: string; name: string; quantity: number; cost_price: number
  available: number; current_price: number; market_value: number
  profit: number; profit_pct: number; day_change: number; day_change_pct: number
}
export interface NewsItem {
  id: string; source: string; title: string; url: string
  published_at: string; news_type: 'individual' | 'global'
  related_codes: string[]; read: boolean
}
export interface Status {
  logged_in: boolean; sources: Record<string, string>; ths: { status: string }
}
export type WsEvent = { type: string; data: unknown }
```

```ts
// frontend/src/api/client.ts
import type { NewsItem, Position, Quote, Status } from '../types'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json() as Promise<T>
}

export const getStatus = () => json<Status>('/api/status')
export const startLogin = () => json<{ qrcode_data: string }>('/api/login/qrcode', { method: 'POST' })
export const pollLogin = () => json<{ ok: boolean }>('/api/login/poll', { method: 'POST' })
export const logout = () => json<{ ok: boolean }>('/api/logout', { method: 'POST' })
export const getQuotes = () => json<Record<string, Quote>>('/api/quotes')
export const getPositions = () => json<Position[]>('/api/positions')
export const getNews = (type: string) => json<NewsItem[]>(`/api/news?type=${type}`)
export const markNewsRead = (id: string) =>
  json<{ ok: boolean }>(`/api/news/${id}/read`, { method: 'POST' })
```

- [ ] **Step 3: 编写 WS 客户端（自动重连）**

```ts
// frontend/src/api/ws.ts
import type { WsEvent } from '../types'

export function connectWS(onEvent: (e: WsEvent) => void): () => void {
  let ws: WebSocket | null = null
  let closed = false
  let retry = 0

  const open = () => {
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
    ws.onmessage = (m) => { try { onEvent(JSON.parse(m.data)) } catch { /* ignore */ } }
    ws.onclose = () => {
      if (!closed) {
        retry = Math.min(retry + 1, 10)
        setTimeout(open, 1000 * retry)
      }
    }
    ws.onopen = () => { retry = 0 }
  }
  open()
  return () => { closed = true; ws?.close() }
}
```

- [ ] **Step 4: 编写 store（zustand）**

```tsx
// frontend/src/store.tsx
import { create } from 'zustand'
import { getNews, getPositions, getQuotes, getStatus, markNewsRead } from './api/client'
import { connectWS } from './api/ws'
import type { NewsItem, Position, Quote, Status } from './types'

interface AppState {
  quotes: Record<string, Quote>
  positions: Position[]
  news: NewsItem[]
  status: Status | null
  connected: boolean
  init: () => void
  setQuotes: (q: Record<string, Quote>) => void
  setPositions: (p: Position[]) => void
  setNews: (n: NewsItem[]) => void
  markRead: (id: string) => void
  refresh: () => Promise<void>
}

export const useApp = create<AppState>((set, get) => ({
  quotes: {},
  positions: [],
  news: [],
  status: null,
  connected: false,
  init() {
    connectWS((ev) => {
      const s = get()
      if (ev.type === 'quotes') s.setQuotes(ev.data as Record<string, Quote>)
      if (ev.type === 'positions') s.setPositions(ev.data as Position[])
      if (ev.type === 'news') s.setNews(ev.data as NewsItem[])
    })
    void get().refresh()
  },
  setQuotes: (q) => set({ quotes: q }),
  setPositions: (p) => set({ positions: p }),
  setNews: (n) => set({ news: n }),
  markRead(id) {
    set({ news: get().news.map((x) => (x.id === id ? { ...x, read: true } : x)) })
    void markNewsRead(id)
  },
  async refresh() {
    const [quotes, positions, news, status] = await Promise.all([
      getQuotes(), getPositions(), getNews('all'), getStatus(),
    ])
    set({ quotes, positions, news, status, connected: true })
  },
}))
```

- [ ] **Step 5: 入口与验证 build**

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './theme.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
)
```

```tsx
// frontend/src/App.tsx
import { useEffect } from 'react'
import { useApp } from './store'

export default function App() {
  const init = useApp((s) => s.init)
  useEffect(() => { init() }, [init])
  return <div className="app"><h1>Investment Board</h1></div>
}
```

`frontend/src/theme.css`（深色主题基础变量，卡片/字体/颜色在后续 Task 复用）：

```css
:root {
  --bg: #0f1419; --panel: #1a2029; --border: #2a3340;
  --text: #e6edf3; --muted: #8b98a5; --up: #e74c3c; --down: #2ecc71;
  --accent: #4f9cf9;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
       font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
```

Run:
```bash
cd frontend && npm install && npm run build
```
Expected: 构建成功（`tsc -b` 无类型错误，`dist/` 生成）

- [ ] **Step 6: 提交**

```bash
git add frontend
git commit -m "feat: 前端脚手架与数据层（类型/API/WS/store）"
```

---

### Task 10: 前端 · 看板页（自选行情 + 分时 sparkline + 持仓卡片）

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/PriceCard.tsx`
- Create: `frontend/src/components/Sparkline.tsx`
- Create: `frontend/src/components/PositionsSummary.tsx`
- Modify: `frontend/src/App.tsx`（加路由/页签切换，本阶段用简单 state 切换）

**Interfaces:**
- Consumes: Task 9 的 `useApp()`（`quotes/positions/status/connected`）
- Produces: 看板视图；`Sparkline(data: number[])`（ECharts 迷你折线）；`PriceCard(quote)`（红涨绿跌卡片）

- [ ] **Step 1: 编写组件**

```tsx
// frontend/src/components/PriceCard.tsx
import type { Quote } from '../types'

export default function PriceCard({ q }: { q: Quote }) {
  const up = q.change >= 0
  return (
    <div className="price-card">
      <div className="name">{q.name}<span className="code">{q.code}</span></div>
      <div className="price" style={{ color: up ? 'var(--up)' : 'var(--down)' }}>
        {q.price.toFixed(2)}
      </div>
      <div className="change" style={{ color: up ? 'var(--up)' : 'var(--down)' }}>
        {up ? '+' : ''}{q.change.toFixed(2)} ({up ? '+' : ''}{q.change_pct.toFixed(2)}%)
      </div>
      <div className="muted">数据来源：新浪/腾讯</div>
    </div>
  )
}
```

```tsx
// frontend/src/components/Sparkline.tsx
import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export default function Sparkline({ data }: { data: number[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chart.setOption({
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [{ type: 'line', data, smooth: true, symbol: 'none',
                 lineStyle: { width: 1.5, color: '#4f9cf9' } }],
    })
    return () => chart.dispose()
  }, [data])
  return <div ref={ref} style={{ width: 120, height: 40 }} />
}
```

```tsx
// frontend/src/components/PositionsSummary.tsx
import type { Position } from '../types'

export default function PositionsSummary({ positions }: { positions: Position[] }) {
  const totalProfit = positions.reduce((s, p) => s + p.profit, 0)
  const totalValue = positions.reduce((s, p) => s + p.market_value, 0)
  return (
    <div className="summary-card">
      <div>持仓市值 <b>¥{totalValue.toFixed(2)}</b></div>
      <div style={{ color: totalProfit >= 0 ? 'var(--up)' : 'var(--down)' }}>
        累计盈亏 <b>{totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(2)}</b>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 编写看板页**

```tsx
// frontend/src/pages/Dashboard.tsx
import { useApp } from '../store'
import PriceCard from '../components/PriceCard'
import PositionsSummary from '../components/PositionsSummary'
import Sparkline from '../components/Sparkline'

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes)
  const positions = useApp((s) => s.positions)
  const connected = useApp((s) => s.connected)
  const list = Object.values(quotes)
  return (
    <div className="page">
      <div className="status-bar">
        {connected ? '● 实时连接中' : '○ 连接断开，重连中…'}
      </div>
      <PositionsSummary positions={positions} />
      <h2>自选实时行情</h2>
      <div className="grid">
        {list.map((q) => (
          <div key={q.code} className="cell">
            <PriceCard q={q} />
            <Sparkline data={[q.prev_close, q.open, q.price]} />
          </div>
        ))}
        {list.length === 0 && <div className="muted">暂无行情数据（未登录时无自选，行情为空）</div>}
      </div>
    </div>
  )
}
```

（`Sparkline` 分时数据源：**MVP 范围内**明确使用 `[prev_close, open, price]` 三点预览；完整当日分时（接入 Task 3 已就绪的 `fetch_intraday`）列入本文档末尾的"后续扩展点"，不属于本 MVP。）

- [ ] **Step 3: 接入 App 页签**

`frontend/src/App.tsx` 增加页签：看板 / 持仓 / 新闻 / 设置，用 `useState<Page>` 切换并渲染对应页面组件。设置页与新闻页在 Task 11-13 实现，此处先渲染占位组件（页面文件未创建前用简单 div）。

- [ ] **Step 4: 验证 build**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src
git commit -m "feat: 前端看板页（行情卡片/迷你分时/持仓汇总）"
```

---

### Task 11: 前端 · 持仓页

**Files:**
- Create: `frontend/src/pages/Positions.tsx`

**Interfaces:**
- Consumes: `useApp().positions`
- Produces: 持仓明细表格视图

- [ ] **Step 1: 编写持仓页**

```tsx
// frontend/src/pages/Positions.tsx
import { useApp } from '../store'

export default function Positions() {
  const positions = useApp((s) => s.positions)
  return (
    <div className="page">
      <h2>持仓明细</h2>
      <table className="tbl">
        <thead>
          <tr>
            <th>代码</th><th>名称</th><th>持股</th><th>可用</th>
            <th>成本</th><th>现价</th><th>市值</th>
            <th>累计盈亏</th><th>盈亏%</th><th>当日盈亏</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.code}>
              <td>{p.code}</td><td>{p.name}</td>
              <td>{p.quantity}</td><td>{p.available}</td>
              <td>{p.cost_price.toFixed(2)}</td>
              <td>{p.current_price.toFixed(2)}</td>
              <td>¥{p.market_value.toFixed(2)}</td>
              <td style={{ color: p.profit >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.profit >= 0 ? '+' : ''}{p.profit.toFixed(2)}
              </td>
              <td style={{ color: p.profit_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.profit_pct.toFixed(2)}%
              </td>
              <td style={{ color: p.day_change >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.day_change >= 0 ? '+' : ''}{p.day_change.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {positions.length === 0 && <div className="muted">暂无持仓（未登录或账号无持仓）</div>}
    </div>
  )
}
```

- [ ] **Step 2: 验证 build**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/Positions.tsx
git commit -m "feat: 前端持仓页"
```

---

### Task 12: 前端 · 新闻页

**Files:**
- Create: `frontend/src/pages/News.tsx`
- Create: `frontend/src/components/NewsCard.tsx`

**Interfaces:**
- Consumes: `useApp().news` / `useApp().markRead`
- Produces: 新闻页（全局快讯 + 个股新闻 Tab，未读高亮，点击标记已读，来源标注）

- [ ] **Step 1: 编写新闻组件与页面**

```tsx
// frontend/src/components/NewsCard.tsx
import type { NewsItem } from '../types'

export default function NewsCard({ item, onRead }: { item: NewsItem; onRead: () => void }) {
  return (
    <a className={`news-card ${item.read ? 'read' : ''}`}
       href={item.url} target="_blank" rel="noreferrer" onClick={onRead}>
      <div className="news-title">{item.title}</div>
      <div className="news-meta">
        <span>{item.source === 'cls' ? '财联社' : '东财公告'}</span>
        <span>{item.published_at}</span>
        {item.related_codes.length > 0 &&
          <span>相关：{item.related_codes.join(', ')}</span>}
      </div>
    </a>
  )
}
```

```tsx
// frontend/src/pages/News.tsx
import { useState } from 'react'
import { useApp } from '../store'
import NewsCard from '../components/NewsCard'

export default function News() {
  const news = useApp((s) => s.news)
  const markRead = useApp((s) => s.markRead)
  const [tab, setTab] = useState<'all' | 'individual' | 'global'>('all')
  const items = news.filter((n) => tab === 'all' || n.news_type === tab)
  return (
    <div className="page">
      <h2>新闻</h2>
      <div className="tabs">
        {(['all', 'individual', 'global'] as const).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''}
                  onClick={() => setTab(t)}>
            {t === 'all' ? '全部' : t === 'individual' ? '个股' : '全局快讯'}
          </button>
        ))}
      </div>
      <div className="news-list">
        {items.map((n) => (
          <NewsCard key={n.id} item={n} onRead={() => markRead(n.id)} />
        ))}
        {items.length === 0 && <div className="muted">暂无新闻</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证 build**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/News.tsx frontend/src/components/NewsCard.tsx
git commit -m "feat: 前端新闻页（个股+全局，已读标记）"
```

---

### Task 13: 前端 · 设置页（扫码登录 / 注销 / 数据源健康）

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

**Interfaces:**
- Consumes: `client.startLogin()` / `pollLogin()` / `logout()`；`useApp().status`
- Produces: 设置页——扫码登录（二维码显示 + 轮询确认）、注销并清除本地数据、数据源健康灯

- [ ] **Step 1: 编写设置页**

```tsx
// frontend/src/pages/Settings.tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { logout, pollLogin, startLogin } from '../api/client'
import { useApp } from '../store'

export default function Settings() {
  const status = useApp((s) => s.status)
  const refresh = useApp((s) => s.refresh)
  const [qr, setQr] = useState<string>('')
  const [scanning, setScanning] = useState(false)
  const timer = useRef<number>()

  const beginLogin = useCallback(async () => {
    const r = await startLogin()
    setQr(r.qrcode_data)
    setScanning(true)
    timer.current = window.setInterval(async () => {
      const r = await pollLogin()
      if (r.ok) {
        window.clearInterval(timer.current)
        setScanning(false)
        setQr('')
        await refresh()
      }
    }, 2000)
  }, [refresh])

  const doLogout = useCallback(async () => {
    await logout()
    await refresh()
  }, [refresh])

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current) }, [])

  return (
    <div className="page">
      <h2>设置</h2>
      <section className="panel">
        <h3>同花顺账号（只读）</h3>
        {status?.logged_in ? (
          <>
            <p>已登录。程序仅读取自选与持仓，不做任何交易操作。</p>
            <button className="danger" onClick={doLogout}>注销并清除全部本地数据</button>
          </>
        ) : (
          <>
            <button onClick={beginLogin}>使用同花顺 App 扫码登录</button>
            {qr && <p className="muted">请在手机同花顺 App 扫描下方二维码（渲染：可将 qrcode_data 交给二维码组件，MVP 用字符占位提示）</p>}
            {scanning && <p className="muted">等待扫码确认…</p>}
          </>
        )}
      </section>
      <section className="panel">
        <h3>数据源健康</h3>
        <ul>
          <li>同花顺接口：{status?.logged_in ? '🟢 已连接' : '⚪ 未登录'}</li>
          <li>行情源：{status?.sources?.market ?? '—'}</li>
          <li>新闻源：{status?.sources?.news ?? '—'}</li>
        </ul>
        <p className="muted">行情来源：新浪财经 / 腾讯财经（公开接口）；新闻来源：东方财富公告 / 财联社电报</p>
      </section>
    </div>
  )
}
```

（二维码渲染：**MVP 范围内**在设置页以可复制的文本形式展示 `qrcode_data`，并提示用户用手机同花顺 App 扫码；图形二维码渲染（qrcode.react 等）列入收尾扩展点。）

- [ ] **Step 2: 验证 build**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: 前端设置页（扫码登录/注销/数据源健康）"
```

---

### Task 14: CI（下单黑名单静态扫描 + pytest + 前端 build）

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `scripts/check_no_trade.py`（下单黑名单扫描）
- Create: `Makefile`（根目录，一键安装/测试/build）

**Interfaces:**
- Consumes: 全部已实现代码
- Produces: CI 流水线；`make test` / `make build` / `make check`

- [ ] **Step 1: 编写黑名单扫描脚本**

```python
#!/usr/bin/env python3
# scripts/check_no_trade.py
"""合规静态检查：扫描代码库，禁止出现下单/交易语义。

遍历 backend/app，若在源码中发现以下词元（作为标识符/方法名/依赖名出现），
立即以非零码退出。仅允许在注释/文档字符串中以中文"严禁交易"等说明出现。
"""
import re
import sys
from pathlib import Path

FORBIDDEN = [
    r"\bplace_order\b", r"\bbuy\b", r"\bsell\b", r"\btrade\b",
    r"\border\b", r"easytrader", r"\b委托\b", r"\b下单\b",
    r"\b撤单\b", r"\b成交\b", r"\bamount.*buy", r"\bquantity.*sell",
]

ROOT = Path(__file__).resolve().parent.parent
HITS = []


def walk(py_files):
    for f in py_files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue  # 注释与文档字符串豁免
            for pat in FORBIDDEN:
                if re.search(pat, line):
                    HITS.append((f, i, pat, line.strip()))


walk((ROOT / "backend/app").rglob("*.py"))

# 允许在 base.py 的 docstring 中出现的"禁止添加任何交易类方法"说明——
# 但为避免误伤，检查独立函数/类定义行是否含交易语义。
for f, i, pat, line in HITS:
    # 白名单：抽象基类 docstring / 合规说明行
    if "禁止添加" in line or "只读" in line or "合规" in line:
        continue
    print(f"{f.relative_to(ROOT)}:{i}: 命中交易语义 {pat!r} -> {line}")
    sys.exit(1)

print("OK: 未发现交易语义代码。")
```

- [ ] **Step 2: 编写 CI**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: 合规静态检查（禁止交易语义）
        run: python scripts/check_no_trade.py
      - name: Install & Test
        working-directory: backend
        run: |
          pip install -e ".[dev]" respx
          python -m pytest -q
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - name: Build
        working-directory: frontend
        run: |
          npm ci || npm install
          npm run build
```

- [ ] **Step 3: 编写 Makefile**

```makefile
# Makefile
.PHONY: install test build check dev-backend dev-frontend

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" respx
	cd frontend && npm install

test:
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

check:
	python scripts/check_no_trade.py

dev-backend:
	cd backend && ./run.sh

dev-frontend:
	cd frontend && npm run dev
```

- [ ] **Step 4: 本地验证全部通过**

Run:
```bash
python scripts/check_no_trade.py && cd backend && .venv/bin/pytest -q && cd ../frontend && npm run build
```
Expected: 全部通过（含 Task 1-13 全部测试与前端构建）

- [ ] **Step 5: 提交**

```bash
git add .github scripts Makefile
git commit -m "ci: 合规静态检查 + 测试 + 前端构建流水线"
```

---

### Task 15: 文档、许可证与端到端联调

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `docs/architecture.md`
- Create: `docs/compliance.md`
- Create: `docs/ths-reverse-engineering.md`（接口逆向记录，指向 `backend/app/ths_client/README.md`）
- Create: `scripts/dev_demo.py`（可选：未登录时的演示数据注入，便于本地体验 UI）

**Interfaces:**
- Consumes: 全部
- Produces: 项目文档、许可证、端到端启动说明

- [ ] **Step 1: 编写 README**

内容必须包含：
- 项目简介与功能（自选行情/持仓盈亏/新闻）
- **合规声明**：仅供个人学习研究，不构成投资建议；数据版权归同花顺/新浪/腾讯/东财/财联社所有；账号风险自担；只读、无交易功能；访问频率受控
- **隐私说明**：凭据仅存本机加密（Keychain），数据不出本机，可一键清除
- 快速开始：`make install` → `make dev-backend` → `make dev-frontend` → 浏览器打开 5173
- 架构图（引用 `docs/architecture.md`）与目录结构
- 常见问题（THS 接口失效如何降级、如何反馈）

- [ ] **Step 2: 编写 LICENSE**

采用 **MIT License**（正文标准 MIT 模板，版权人 `chenjunhannop`，并附带合规/免责附注说明：本软件仅供个人学习研究，使用者需自行确认对同花顺等数据源的使用符合其服务条款与当地法律）。

- [ ] **Step 3: 编写 docs**

- `docs/compliance.md`：完整合规说明（第 5 节设计逐条落实说明 + 用户自查清单）
- `docs/architecture.md`：架构图（Mermaid）+ 数据流 + 模块职责
- `docs/ths-reverse-engineering.md`：逆向契约表、抓包方法、失效时的降级行为与 PR 指引

- [ ] **Step 4: 端到端联调验证**

Run:
```bash
# 终端1
cd backend && ./run.sh
# 终端2
cd frontend && npm run dev
# 终端3（验证后端健康）
curl -s http://127.0.0.1:8210/api/status
```
Expected：`/api/status` 返回 JSON；前端 5173 打开可看到深色主题页面；无登录时行情/持仓为空、新闻页显示全局快讯（公开源，未登录也应有数据）。

- [ ] **Step 5: 提交并推送**

```bash
git add -A
git commit -m "docs: README/LICENSE/架构/合规/逆向说明；端到端联调"
git push -u origin main
```

---

## 收尾与后续扩展点

MVP 完成后：`make check && make test && make build` 全绿即交付。后续扩展（不在本计划内）：完整当日分时（store 接入 `fetch_intraday`）、K 线、资产历史曲线、价格提醒、多市场、二维码渲染优化、WebSocket 断线事件总线清理。

---

## 执行记录（As-Built）

> 全部 15 个任务于 2026-08-18 完成。最终验证：`make check`（合规扫描通过）/ `make test`（29 passed）/ `make build`（成功）。
> 实现与计划的主要偏差记录如下（均为满足计划测试意图的最小修正或增强，未改变设计目标）。

| Task | Commit | 偏差 / 增强 |
|---|---|---|
| 2 | c37ef86 | 测试 `read_text()` 改 `read_bytes()`（密文是二进制，原测试会抛 UnicodeDecodeError） |
| 3 | 9fc372f | ① `parse_sina` 代码提取改 `text.split("hq_str_")[1].split("=")[0][2:]`（原 `[:6]` 会截到市场前缀）② 腾讯 fixture 展开为完整 ~40 字段格式 ③ 分时 fixture 改逗号分隔 ④ mock 补充 sz000001 行 |
| 4 | 13587fe | 补充第 4 个测试 `test_fetch_individual_maps_related_code`（覆盖 Interfaces 声明的 `fetch_individual`，计划只写了 3 个却标 4 passed） |
| 6 | d20fd80 | 去掉 `_quotes_loop` 的 `if codes:` 守卫（空启动时 fetcher 永不被调导致测试失败；`MarketService` 对空代码早退，生产安全） |
| 7 | 377a704 | ① ws 改"每连接自推送"，避免 N 连接时广播 O(N²) 任务 ② `EventBus` 增 `unsubscribe` 且 `subscribe` 返回回调，连接关闭时清理订阅防泄漏 ③ routes 对 `ths=None` 返回 503 |
| 9 | 06f8b7b | 补写 `index.html`（计划未给内容）；`.gitignore` 加 `*.tsbuildinfo` |
| 14 | 8aeb45b / 39a360f | ① Makefile/CI 用 `python3`（本机无 `python` 别名）② **合规扫描重写为 AST 方案**：原正则 `\bbuy\b` 漏掉 `buy_stock` 等组合标识符，AST 检查标识符前缀，天然豁免注释/字符串；已验证 buy_stock/place_order/中文"买入"均被拦截 |
| 15 | 118d8fc | 未创建可选 `scripts/dev_demo.py`（需新增后端注入端点，牵动测试，保持最小变更面）；README 快速开始 URL 用 `localhost:5173`（Vite 默认绑定 IPv6 localhost） |

**已知外部依赖问题**：财联社电报公开接口当前返回 404（第三方接口变动），新闻源被优雅捕获返回空列表、应用不崩溃；已如实写入 README FAQ，待实测修正 `CLS_TELEGRAPH_URL` 或接口字段。
