"""同花顺客户端（解析/抽象接口/登录流程/合规）的单元测试."""
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
    """解析自选列表 JSON 得到 Stock 列表."""
    stocks = parse_watchlist(WATCHLIST)
    assert stocks[0].code == "600519"
    assert stocks[0].name == "贵州茅台"


def test_parse_positions():
    """解析持仓 JSON 得到 Position 列表."""
    pos = parse_positions(POSITIONS)
    assert pos[0].quantity == 100
    assert pos[0].cost_price == 1600.0


def test_adapter_is_abstract():
    """抽象基类不可实例化."""
    with pytest.raises(TypeError):
        ThsAdapter()  # 抽象类不可实例化


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
        return_value=httpx.Response(200, headers={"Set-Cookie": "u=u1; Path=/"}, json={}))

    vault = Vault(tmp_path)
    client = ThsWebClient(vault, httpx.AsyncClient(), endpoint_prefix="https://ths.test")
    qr = await client.login_qrcode()
    assert qr["qrid"] == "usk_t1"
    assert qr["qrcode_img"] == "UE5HREFUQQ=="  # base64("PNGDATA")
    ok = await client.poll_login("usk_t1")
    assert ok["ok"] is True
    assert client.is_logged_in
    assert vault.load_session()["cookies"]["u"] == "u1"


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
        respx_mock.post("https://ths.test/scan/getInfoNew").mock(return_value=_status(status))
        vault = Vault(tmp_path)
        client = ThsWebClient(vault, httpx.AsyncClient(), endpoint_prefix="https://ths.test")
        res = await client.poll_login("q")
        assert res["ok"] is False
        assert res["reason"] == expected


@pytest.mark.asyncio
async def test_login_qrcode_graceful_degrade(tmp_path, monkeypatch, respx_mock: MockRouter):
    """CreatCode 失败时返回 error 而非抛出异常."""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    from app.vault.store import Vault
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)

    respx_mock.get("https://ths.test/scan/creatCode").mock(return_value=httpx.Response(403))
    vault = Vault(tmp_path)
    client = ThsWebClient(vault, httpx.AsyncClient(), endpoint_prefix="https://ths.test")
    res = await client.login_qrcode()
    assert res["qrcode_img"] == ""
    assert "error" in res


def test_web_client_has_no_trade_methods():
    """客户端源码不得出现交易语义标识符."""
    forbidden = ["place_order", "buy", "sell", "trade", "order"]
    src = (Path(__file__).resolve().parent.parent / "app/ths_client/web_client.py")
    text = src.read_text()
    for word in forbidden:
        assert word not in text, f"发现交易语义方法: {word}"
