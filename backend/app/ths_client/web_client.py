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

    def __init__(self,
                 vault: Vault,
                 client: httpx.AsyncClient,
                 endpoint_prefix: str,
                 timeout: float = 10.0):
        self._vault = vault
        self._client = client
        self._prefix = endpoint_prefix
        self._timeout = timeout
        self._pending_qr: dict | None = None

    @property
    def is_logged_in(self) -> bool:
        return self._vault.is_logged_in

    async def _get_json(self, path: str, **params) -> dict:
        headers = {}
        session = self._vault.load_session()
        if session and session.get("token"):
            headers["Authorization"] = f"Bearer {session['token']}"
        r = await self._client.get(self._prefix + path,
                                   params=params,
                                   headers=headers,
                                   timeout=self._timeout)
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
