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
