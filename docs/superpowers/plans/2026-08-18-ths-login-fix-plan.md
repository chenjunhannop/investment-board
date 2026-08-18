# 同花顺登录链路修复实施计划（扫码登录）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把同花顺登录链路从失效的 `eq.10jqka.com.cn` 逆向接口迁移到已实测可用的 `upass.10jqka.com.cn` 网页版扫码登录（`creatCode`/`creatImg`/`getInfoNew`），并让自选/持仓查询走新接口，端到端扫码登录可用。

**Architecture:** 后端 `ThsWebClient` 登录链路重写（登录域换到 `upass.10jqka.com.cn`，二维码返回真实 PNG 图片，登录态 cookie 捕获后经 Vault 加密存储，鉴权从 Bearer token 改为 cookie）；`ThsAdapter` 抽象接口签名同步更新（`poll_login` 增 qrid 参数、返回 `{ok,reason}`）；前端设置页二维码改为 `<img>` 图片展示 + 按 reason 流转 + 过期自动刷新；查询接口 URL 配置化（`search.10jqka.com.cn` 已知线索，含真实扫码抓包确认步骤）。

**Tech Stack:** Python 3.11 / httpx / respx（测试）、React 18 + TS + Vite、AES-256-GCM（Vault）、ruff/yapf/mypy、eslint/prettier

## Global Constraints

- 只改：`backend/app/ths_client/*`、`backend/app/api/routes.py`、`backend/app/config.py`、`backend/tests/*`、`frontend/src/api/client.ts`、`frontend/src/pages/Settings.tsx`、`README.md`、`docs/ths-reverse-engineering.md`（其余不碰）
- **只读红线**：不得引入以 buy/sell/trade/order 为前缀的标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK
- **测试硬性 29 passed**；`make check`（合规）必须 OK；`make lint`（ruff/yapf/eslint/prettier）零错；`make typecheck`（mypy）通过；`make build` 成功
- 命令一律用 `backend/.venv/bin/` 下的工具；前端 `cd frontend && npm run ...`
- 新代码 docstring 用 Google 风格（句末 ASCII `.`），ruff D 规则零错误
- `poll_login` 返回契约：`{ok: bool, reason?: 'expired'|'waiting'|'confirmed'}`（`ok=true` 成功）；`login_qrcode` 返回 `{qrid: str, qrcode_img: str(base64 png), error?: str}`
- 会话 cookie 经 Vault AES-256-GCM 加密存 `~/.investment-board/session.enc`；测试用 `IB_TEST_KEYCHAIN`
- commit message 用 `feat:` 类型（阿里 commitlint type-enum 含 feat）
- 查询接口 URL 配置化（`IB_THS_WATCHLIST_URL`/`IB_THS_POSITIONS_URL` 环境变量可覆盖），默认值按已知线索 `https://search.10jqka.com.cn/service/getSelfStock`（自选）；持仓默认留空串，抓包确认后填
- 所有外部请求带超时（10s）与异常捕获（优雅降级，不抛 500）

---

### Task 1: 后端登录链路重写（upass 扫码）

**Files:**
- Modify: `backend/app/ths_client/base.py`（ThsAdapter 签名）
- Modify: `backend/app/ths_client/web_client.py`（login_qrcode/poll_login 重写 + cookie 鉴权）
- Modify: `backend/app/config.py`（`ths_endpoint_prefix` 默认改 `https://upass.10jqka.com.cn`）
- Modify: `backend/app/api/routes.py`（login_poll 读 body 传 qrid，返回 `{ok,reason}`）

**Interfaces:**
- Consumes: `Vault`（load_session/save_session/clear）；httpx.AsyncClient（共享）
- Produces: `ThsAdapter.login_qrcode() -> dict`（`{qrid, qrcode_img}`）；`ThsAdapter.poll_login(qrid: str) -> dict`（`{ok, reason}`）；cookie 经 `self._vault` 持久化

- [ ] **Step 1: 更新 ThsAdapter 抽象接口签名（base.py）**

把 `base.py` 中 `poll_login` 抽象方法替换为：

```python
    @abstractmethod
    async def poll_login(self, qrid: str) -> dict:
        """轮询扫码登录状态，成功后捕获登录态 cookie 并持久化.

        Args:
            qrid: 扫码登录二维码 ID（来自 login_qrcode）.

        Returns:
            {"ok": bool, "reason": "expired"|"waiting"|"confirmed"} 状态字典；
            ok 为 True 表示登录成功.
        """
        ...
```

`login_qrcode` 的 docstring 更新为：返回 `{"qrid", "qrcode_img"}`（qrcode_img 为 base64 PNG）。其余抽象方法签名不变。

- [ ] **Step 2: 重写 web_client.py 的登录方法 + cookie 鉴权**

替换 `login_qrcode`、`poll_login` 方法，并在 `__init__` 增加查询 URL 参数（Task 2 用）：

```python
    def __init__(self,
                 vault: Vault,
                 client: httpx.AsyncClient,
                 endpoint_prefix: str,
                 timeout: float = 10.0,
                 watchlist_url: str = "",
                 positions_url: str = ""):
        """初始化只读客户端.

        Args:
            vault: 会话凭据存储.
            client: 共享的 httpx 异步客户端.
            endpoint_prefix: 同花顺登录接口地址前缀（默认 upass.10jqka.com.cn）.
            timeout: 单次请求超时秒数，默认 10 秒.
            watchlist_url: 自选查询完整 URL；空串表示未配置.
            positions_url: 持仓查询完整 URL；空串表示未配置.
        """
        self._vault = vault
        self._client = client
        self._prefix = endpoint_prefix
        self._timeout = timeout
        self._watchlist_url = watchlist_url
        self._positions_url = positions_url
        self._pending_qrid: str | None = None

    @property
    def is_logged_in(self) -> bool:
        """是否已处于登录状态."""
        return self._vault.is_logged_in

    def _apply_session(self) -> None:
        """把 Vault 中保存的 cookie 恢复为客户端 cookie（幂等）.

        Returns:
            None.
        """
        session = self._vault.load_session()
        if session and session.get("cookies"):
            self._client.cookies.update(session["cookies"])

    async def login_qrcode(self) -> dict:
        """获取扫码登录二维码.

        请求 upass 的 creatCode 拿 qrid，再请求 creatImg 拿二维码 PNG，
        以 base64 返回供前端 <img> 展示.

        Returns:
            {"qrid": str, "qrcode_img": str(base64 png)}；失败时含 "error" 说明.
        """
        try:
            r = await self._client.get(
                self._prefix + "/scan/creatCode",
                timeout=self._timeout,
            )
            r.raise_for_status()
            data = r.json()
            qrid = data.get("qrid", "")
            if not qrid:
                return {"qrid": "", "qrcode_img": "", "error": "creatCode 未返回 qrid"}
            img = await self._client.get(
                self._prefix + f"/scan/creatImg?qrid={qrid}",
                timeout=self._timeout,
            )
            img.raise_for_status()
            b64 = base64.b64encode(img.content).decode("ascii")
            self._pending_qrid = qrid
            return {"qrid": qrid, "qrcode_img": b64}
        except Exception as e:
            logger.warning("获取登录二维码失败（第三方接口可能已变动）: %s", e)
            return {
                "qrid": "",
                "qrcode_img": "",
                "error": f"同花顺接口暂时不可用（{e.__class__.__name__}）",
            }

    async def poll_login(self, qrid: str) -> dict:
        """轮询扫码登录状态，成功后捕获登录态 cookie 并持久化.

        Args:
            qrid: 扫码登录二维码 ID.

        Returns:
            {"ok": True} 登录成功；否则 {"ok": False, "reason": ...}.
        """
        data = {
            "qrid": qrid,
            "state": 1,
            "source": "pc_web",
            "page_source": "web_screen",
            "request_type": "login",
        }
        try:
            r = await self._client.post(
                self._prefix + "/scan/getInfoNew",
                data=data,
                timeout=self._timeout,
            )
            r.raise_for_status()
            res = r.json()
            status = int(res.get("status", 0))
        except Exception as e:
            logger.warning("轮询扫码状态失败: %s", e)
            return {"ok": False, "reason": "waiting"}
        if status == 0:
            return {"ok": False, "reason": "expired"}
        if status == 1:
            return {"ok": False, "reason": "waiting"}
        if status == 2:
            return {"ok": False, "reason": "confirmed"}
        # status == 3：验证成功，跟随跳转捕获登录态 cookie
        redir = "https://www.10jqka.com.cn/"
        try:
            await self._client.get(redir, timeout=self._timeout)
        except Exception as e:
            logger.warning("捕获登录态 cookie 失败: %s", e)
        cookies = {k: v for k, v in self._client.cookies.items()}
        self._vault.save_session({"cookies": cookies})
        return {"ok": True}
```

删除原 `_get_json` 中基于 `Authorization: Bearer` 的 header 逻辑（改为 `_apply_session` cookie 恢复），并在 `query_watchlist`/`query_positions`/`refresh_session` 调用前调用 `self._apply_session()`（Task 2 统一处理）。

- [ ] **Step 3: config.py 登录前缀默认值改为 upass**

`backend/app/config.py`：`ths_endpoint_prefix: str = "https://upass.10jqka.com.cn"`，并在环境变量读取段加查询 URL 配置：

```python
settings.ths_endpoint_prefix = os.environ.get(
    "IB_THS_ENDPOINT", settings.ths_endpoint_prefix)
```

新增字段（Settings 类内，watchlist_url/positions_url 默认空串）：
```python
    ths_watchlist_url: str = ""
    ths_positions_url: str = ""
```
环境变量读取追加：
```python
settings.ths_watchlist_url = os.environ.get("IB_THS_WATCHLIST_URL", settings.ths_watchlist_url)
settings.ths_positions_url = os.environ.get("IB_THS_POSITIONS_URL", settings.ths_positions_url)
```

- [ ] **Step 4: routes.py login_poll 读 body 传 qrid，返回 {ok, reason}**

`backend/app/api/routes.py` 的 `login_poll` 改为：

```python
@router.post("/login/poll")
async def login_poll(request: Request):
    """轮询同花顺扫码登录结果.

    Args:
        request: FastAPI 请求，携带挂载了 ths 的 app.state.

    Returns:
        {"ok": bool, "reason": str|None}，表示本次轮询的扫码状态.

    Raises:
        HTTPException: 503 当同花顺客户端未注入.
    """
    ths = request.app.state.ths
    if ths is None:
        raise HTTPException(status_code=503, detail="THS 客户端未配置")
    body = await request.json()
    qrid = (body or {}).get("qrid", "")
    if not qrid:
        return {"ok": False, "reason": "waiting"}
    return await ths.poll_login(qrid)
```

- [ ] **Step 5: 验证（mock 层先过）**

```bash
backend/.venv/bin/ruff check backend/app/ths_client backend/app/api/routes.py backend/app/config.py
backend/.venv/bin/mypy backend/app
backend/.venv/bin/pytest -q   # 预期 test_web_client_login_flow 失败（旧契约），其余通过
```

> 说明：Task 1 会让旧 `test_web_client_login_flow` 红（它 mock 的是旧 `/qrcode`+`/poll` 契约），属预期；Task 3 更新测试后恢复全绿。

- [ ] **Step 6: 提交**

```bash
git add backend/app/ths_client/base.py backend/app/ths_client/web_client.py backend/app/config.py backend/app/api/routes.py
git commit -m "feat: 同花顺登录链路迁移到 upass 扫码（creatCode/getInfoNew）"
```

---

### Task 2: 查询接口适配（自选/持仓）+ 会话恢复

**Files:**
- Modify: `backend/app/ths_client/web_client.py`（query_watchlist/query_positions/refresh_session + _apply_session 接入）
- Modify: `backend/app/main.py`（构造 ThsWebClient 时传查询 URL）
- Modify: `backend/app/ths_client/parsers.py`（如需，保持现有解析器）

**Interfaces:**
- Consumes: Task 1 的 `_apply_session`/`_watchlist_url`/`_positions_url`；`config.settings.ths_watchlist_url/ths_positions_url`
- Produces: `query_watchlist() -> list[Stock]`、`query_positions() -> list[Position]`、`refresh_session() -> bool`

- [ ] **Step 1: 重写查询方法与 refresh_session（cookie 鉴权）**

替换 `query_watchlist`、`query_positions`、`refresh_session`：

```python
    async def query_watchlist(self) -> list[Stock]:
        """查询当前自选股列表.

        Returns:
            自选股 Stock 列表；未配置接口或请求失败时返回空列表.
        """
        if not self._watchlist_url:
            logger.warning("自选查询接口未配置（IB_THS_WATCHLIST_URL）")
            return []
        self._apply_session()
        try:
            r = await self._client.get(self._watchlist_url, timeout=self._timeout)
            r.raise_for_status()
            return parse_watchlist(_json_text(r.json()))
        except Exception as e:
            logger.warning("查询自选失败: %s", e)
            return []

    async def query_positions(self) -> list[Position]:
        """查询当前持仓列表.

        Returns:
            持仓 Position 列表；未配置接口或请求失败时返回空列表.
        """
        if not self._positions_url:
            logger.warning("持仓查询接口未配置（IB_THS_POSITIONS_URL）")
            return []
        self._apply_session()
        try:
            r = await self._client.get(self._positions_url, timeout=self._timeout)
            r.raise_for_status()
            return parse_positions(_json_text(r.json()))
        except Exception as e:
            logger.warning("查询持仓失败: %s", e)
            return []

    async def refresh_session(self) -> bool:
        """校验会话是否仍然有效.

        Returns:
            会话有效返回 True；未配置接口或请求异常返回 False.
        """
        if not self._watchlist_url:
            return self._vault.is_logged_in
        self._apply_session()
        try:
            r = await self._client.get(self._watchlist_url, timeout=self._timeout)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.warning("会话校验失败: %s", e)
            return False
```

> `_json_text` 保留（`data.get("data", [])` 兼容）；若实测新接口响应不包裹 `{"data": ...}`，在 Task 5 抓包确认后调整 `_json_text` 或解析器（计划保留此适配点，见 As-Built）。

- [ ] **Step 2: main.py 构造 ThsWebClient 时传查询 URL**

`backend/app/main.py` 中 `ThsWebClient(...)` 构造处，追加 `watchlist_url=settings.ths_watchlist_url, positions_url=settings.ths_positions_url`（先读该文件确认构造点与 `endpoint_prefix` 传参方式）。

- [ ] **Step 3: 验证**

```bash
backend/.venv/bin/ruff check backend/app/ths_client backend/app/main.py
backend/.venv/bin/mypy backend/app
backend/.venv/bin/yapf -dr backend/app backend/tests
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/ths_client/web_client.py backend/app/main.py
git commit -m "feat: 自选/持仓查询接口配置化并接入 cookie 会话"
```

---

### Task 3: 测试适配（新契约）

**Files:**
- Modify: `backend/tests/test_ths_client.py`（扫码流程 mock 更新 + 新增用例）
- Modify: `backend/tests/test_api.py`（如涉及 login/poll 契约）

**Interfaces:**
- Consumes: Task 1 新契约（`login_qrcode` 返回 `{qrid,qrcode_img}`；`poll_login(qrid)` 返回 `{ok,reason}`）
- Produces: 29+ 测试全绿

- [ ] **Step 1: 更新扫码流程测试（test_web_client_login_flow）**

替换原测试为（mock 新接口 `creatCode`/`creatImg`/`getInfoNew`）：

```python
@pytest.mark.asyncio
async def test_web_client_login_flow(tmp_path, monkeypatch, respx_mock: MockRouter):
    """扫码登录流程（creatCode/getInfoNew）可完成并持久化会话."""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    from app.vault.store import Vault
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)

    respx_mock.get("https://ths.test/scan/creatCode").mock(
        return_value=httpx.Response(200, json={"qrid": "usk_t1"}))
    respx_mock.get("https://ths.test/scan/creatImg?qrid=usk_t1").mock(
        return_value=httpx.Response(200, content=b"PNGDATA"))
    respx_mock.post("https://ths.test/scan/getInfoNew").mock(
        return_value=httpx.Response(200, json={"status": 3}))
    respx_mock.get("https://www.10jqka.com.cn/").mock(
        return_value=httpx.Response(200, headers={"Set-Cookie": "u=u1; Path=/"},
                                    json={}))

    vault = Vault(tmp_path)
    client = ThsWebClient(vault, httpx.AsyncClient(),
                          endpoint_prefix="https://ths.test")
    qr = await client.login_qrcode()
    assert qr["qrid"] == "usk_t1"
    assert qr["qrcode_img"] == "UE5HREFUQQ=="  # base64("PNGDATA")
    ok = await client.poll_login("usk_t1")
    assert ok["ok"] is True
    assert client.is_logged_in
    assert vault.load_session()["cookies"]["u"] == "u1"
```

- [ ] **Step 2: 新增轮询状态用例**

```python
@pytest.mark.asyncio
async def test_poll_login_status_machine(tmp_path, monkeypatch, respx_mock: MockRouter):
    """轮询状态映射：0=expired, 1=waiting, 2=confirmed."""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    from app.vault.store import Vault
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)

    def _status(n):
        return httpx.Response(200, json={"status": n})

    for status, expected in [(0, "expired"), (1, "waiting"), (2, "confirmed")]:
        respx_mock.reset()
        respx_mock.post("https://ths.test/scan/getInfoNew").mock(
            return_value=_status(status))
        vault = Vault(tmp_path)
        client = ThsWebClient(vault, httpx.AsyncClient(),
                              endpoint_prefix="https://ths.test")
        res = await client.poll_login("q")
        assert res["ok"] is False
        assert res["reason"] == expected
```

- [ ] **Step 3: 新增降级用例（接口异常不抛 500）**

```python
@pytest.mark.asyncio
async def test_login_qrcode_graceful_degrade(tmp_path, monkeypatch, respx_mock: MockRouter):
    """creatCode 失败时返回 error 而非抛出异常."""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    from app.vault.store import Vault
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)

    respx_mock.get("https://ths.test/scan/creatCode").mock(
        return_value=httpx.Response(403))
    vault = Vault(tmp_path)
    client = ThsWebClient(vault, httpx.AsyncClient(),
                          endpoint_prefix="https://ths.test")
    res = await client.login_qrcode()
    assert res["qrcode_img"] == ""
    assert "error" in res
```

- [ ] **Step 4: 检查 test_api.py 是否引用旧契约（login/poll），同步修正**

`backend/tests/test_api.py`：若 mock 了 `/api/login/poll` 旧行为，更新为新 `{ok,reason}` 契约。先读文件确认。

- [ ] **Step 5: 验证**

```bash
backend/.venv/bin/pytest -q   # 期望全部通过（29 + 新增）
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py   # OK
```

- [ ] **Step 6: 提交**

```bash
git add backend/tests/test_ths_client.py backend/tests/test_api.py
git commit -m "feat: 更新同花顺扫码登录测试到新接口契约"
```

---

### Task 4: 前端扫码登录改造

**Files:**
- Modify: `frontend/src/api/client.ts`（startLogin/pollLogin 类型）
- Modify: `frontend/src/pages/Settings.tsx`（二维码图片、reason 流转、过期刷新）

**Interfaces:**
- Consumes: 后端新契约（`/api/login/qrcode` → `{qrid,qrcode_img,error?}`；`/api/login/poll` → `{ok,reason?}`）
- Produces: 前端扫码登录交互完整（图片二维码 + 自动刷新）

- [ ] **Step 1: client.ts 更新类型**

```ts
export interface LoginQrcode {
  qrid: string;
  qrcode_img: string;
  error?: string;
}
export interface LoginPoll {
  ok: boolean;
  reason?: 'expired' | 'waiting' | 'confirmed';
}
export const startLogin = () => json<LoginQrcode>('/api/login/qrcode', { method: 'POST' });
export const pollLogin = (qrid: string) =>
  json<LoginPoll>('/api/login/poll', { method: 'POST', body: JSON.stringify({ qrid }) });
```

- [ ] **Step 2: Settings.tsx 重写扫码逻辑（图片 + reason + 过期刷新）**

`beginLogin`/轮询逻辑改为：

```tsx
const beginLogin = useCallback(async () => {
  setError('');
  setQr('');
  try {
    const r = await startLogin();
    if (!r.qrcode_img || r.error) {
      setError(r.error || '获取二维码失败，请稍后再试');
      return;
    }
    setQr(`data:image/png;base64,${r.qrcode_img}`);
    setScanning(true);
    setStatusText('请在手机同花顺 App 扫描二维码');
    timer.current = window.setInterval(async () => {
      const res = await pollLogin(r.qrid);
      if (res.ok) {
        window.clearInterval(timer.current);
        setScanning(false);
        setQr('');
        await refresh();
      } else if (res.reason === 'expired') {
        window.clearInterval(timer.current);
        beginLogin(); // 二维码失效自动刷新
      } else if (res.reason === 'confirmed') {
        setStatusText('已扫码，请在手机上确认登录');
      }
    }, 2000);
  } catch {
    setError('获取登录二维码失败，请检查后端服务后重试');
  }
}, [refresh]);
```

- 新增 `statusText` state；二维码渲染改为 `<img src={qr} alt="同花顺登录二维码" />`
- 保留登出、错误提示、`qr-box` 结构；`pollLogin` 从 `api/client` 导入改为带参

- [ ] **Step 3: 验证**

```bash
cd frontend && npm run lint && npm run format:check && npm run build
python3 scripts/check_no_trade.py   # OK
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/client.ts frontend/src/pages/Settings.tsx
git commit -m "feat: 前端扫码登录支持二维码图片与自动刷新"
```

---

### Task 5: 文档更新、全量验收与真实扫码端到端

**Files:**
- Modify: `README.md`（FAQ 第 1 条更新为已修复/新接口）
- Modify: `docs/ths-reverse-engineering.md`（契约表更新为 upass 扫码接口）
- Modify: `docs/superpowers/plans/2026-08-18-ths-login-fix-plan.md`（追加 As-Built）

- [ ] **Step 1: 更新 README FAQ 第 1 条与逆向文档契约表**

- README：移除"当前已知 qrcode 404"的失效标注，改为"登录链路已迁移至 upass 网页版扫码（2026-08 修复）"；说明自选/持仓接口配置化（`IB_THS_WATCHLIST_URL`/`IB_THS_POSITIONS_URL`）
- `docs/ths-reverse-engineering.md`：契约表改为新接口（`/scan/creatCode`、`/scan/creatImg`、`/scan/getInfoNew`），字段映射更新（cookie 会话而非 Bearer token）

- [ ] **Step 2: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（check OK / lint 零错 / typecheck Success / test ≥29 passed / build 成功）。

- [ ] **Step 3: 本地接口冒烟（mock 网络不可用时验证降级）**

```bash
cd backend && (./run.sh &) && sleep 4
curl -s -X POST http://127.0.0.1:8210/api/login/qrcode   # 期望 {qrid,qrcode_img} 或优雅降级 error
curl -s -X POST http://127.0.0.1:8210/api/login/poll -H "Content-Type: application/json" -d '{"qrid":"x"}'
pkill -f "uvicorn app.main"
```

- [ ] **Step 4: 真实扫码端到端（需要用户配合一次）**

> **本步骤需用户用手机同花顺 App 扫码确认**（用户已同意配合）。

1. 启动后端 + 前端 dev server
2. 浏览器打开设置页 → 点击"扫码登录" → 确认二维码图片显示
3. 用户手机同花顺 App 扫码 → 手机确认 → 观察前端状态流转（等待→已扫码→登录成功）
4. 确认自选/持仓页：若查询接口默认值可用则展示数据；若空，则用 browser-use 抓包登录后自选/持仓真实请求，更新 `IB_THS_WATCHLIST_URL`/`IB_THS_POSITIONS_URL`（环境变量或 config 默认值），重试
5. 记录结果与抓包接口到 As-Built

- [ ] **Step 5: As-Built 执行记录 + 推送**

在计划文档末尾追加 As-Built 表（各任务 commit hash、验证结果、真实扫码抓包得到的接口路径、任何偏差）。然后：

```bash
git add README.md docs/ths-reverse-engineering.md docs/superpowers/plans/2026-08-18-ths-login-fix-plan.md
git commit -m "docs: 同花顺登录修复计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 6: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。

---

## As-Built 执行记录（2026-08-18 追加）

### 各任务提交与验证

| Task | Commit（短 hash） | 验证结果 | 备注 / 偏差 |
| --- | --- | --- | --- |
| Task 1 后端登录链路重写 | `bd65f97` | `ruff check`、`mypy` 通过；`pytest` 中 `test_web_client_login_flow` 红 | **预期红**：旧测试 mock 的是旧 `/qrcode`+`/poll` 契约，属计划内预期（Task 3 恢复全绿） |
| Task 2 查询接口配置化 + 会话恢复 | `97093de` | `ruff` / `mypy` / `yapf` 通过 | **偏差：删死代码**——重写 `query_watchlist`/`query_positions`/`refresh_session` 时顺带清理了已无引用的旧 `_get_json`/Bearer header 相关死代码 |
| Task 3 测试适配 | `e0e3049` | `pytest` 31 passed；`ruff` / `mypy` / `check_no_trade.py` 通过 | **偏差：D403 措辞**——ruff D403（docstring 祈使句首）对中文 docstring 的告警按项目惯例处理（中文措辞 + 句末 ASCII `.`） |
| Task 4 前端扫码登录改造 | `393ae26` | `npm run lint` / `format:check` / `build` 通过；`check_no_trade.py` OK | **偏差：死 CSS 未清**——`Settings.tsx` 遗留少量不再使用的样式类未清理（不影响构建与运行，留待后续视觉收尾） |

### Task 5 全量验收与本地冒烟（2026-08-18）

- **全量验收**：`make check`（OK：未发现交易语义代码）→ `make lint`（ruff / yapf / eslint / prettier 零错）→ `make typecheck`（后端 mypy Success，前端 tsc Success）→ `make test`（**31 passed**）→ `make build`（Vite 构建成功）。
- **本地接口冒烟**（`./run.sh` + curl，**真实网络环境**，非 mock）：
  - `POST /api/login/qrcode` → `{"qrid":"usk_...","qrcode_img":"<base64 PNG>"}`；真实命中 `upass.10jqka.com.cn/scan/creatCode` + `/scan/creatImg`，均 `200 OK`，返回有效二维码图。
  - `POST /api/login/poll`（`{"qrid":"x"}`）→ `{"ok":false,"reason":"expired"}`；真实命中 `/scan/getInfoNew` `200 OK`，非法 qrid 优雅降级为 `expired`（不抛 500）。
  - `GET /api/status` → 正常（`ths: not_logged_in`，行情 / 新闻 ok）。
  - 冒烟后按计划 `pkill -f "uvicorn app.main"` 停止服务。

### 已知待办 / 偏差汇总

1. **真实扫码端到端（Task 5 Step 4）未做**：需用户用手机同花顺 App 扫码确认（二维码展示 → 手机确认 → 状态流转 → 自选/持仓数据）。**待用户配合后由主 agent 完成并补充本节。**
2. **查询接口默认空串**：`ths_watchlist_url` / `ths_positions_url` 默认均为空串（`IB_THS_WATCHLIST_URL` / `IB_THS_POSITIONS_URL` 可覆盖）。自选已知线索 `https://search.10jqka.com.cn/service/getSelfStock` 待真实扫码抓包确认后填默认值；持仓 URL 待抓包。未配置时查询优雅返回空列表（记 WARNING）。
3. **`_json_text` 包裹层级适配点**：默认假定查询响应为 `{"data":[...]}`；若实测新查询接口不包裹，需在真实扫码抓包后调整（计划保留的适配点）。
4. **文档同步**：本次除计划指定文件外，同步更新了 `backend/app/ths_client/README.md`（原为旧 eq / Bearer 契约，与 `docs/ths-reverse-engineering.md` 互为引用，一并修正为新契约）。

### Task 5 提交

| 提交 | 内容 |
| --- | --- |
| `docs: 同花顺登录修复计划追加执行记录（as-built）` | README FAQ 更新 + `docs/ths-reverse-engineering.md` 契约表/轮询语义更新 + `backend/app/ths_client/README.md` 同步 + 本 As-Built |
