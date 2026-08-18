"""同花顺网页版只读客户端（逆向接口实现）.

只读约束：本模块仅负责登录与查询（自选/持仓），严禁添加任何交易类方法.
接口 endpoint 的逆向值与字段说明见 README.md.
"""
import json
import logging
from typing import Any

import httpx

from app.models import Position, Stock
from app.ths_client.base import ThsAdapter
from app.ths_client.parsers import parse_positions, parse_watchlist
from app.vault.store import Vault

logger = logging.getLogger(__name__)


class ThsWebClient(ThsAdapter):
    """同花顺网页版只读客户端（登录/会话/自选/持仓查询实现）."""

    def __init__(self,
                 vault: Vault,
                 client: httpx.AsyncClient,
                 endpoint_prefix: str,
                 timeout: float = 10.0):
        """初始化只读客户端.

        Args:
            vault: 会话凭据存储.
            client: 共享的 httpx 异步客户端.
            endpoint_prefix: 同花顺接口地址前缀.
            timeout: 单次请求超时秒数，默认 10 秒.
        """
        self._vault = vault
        self._client = client
        self._prefix = endpoint_prefix
        self._timeout = timeout
        self._pending_qr: dict | None = None

    @property
    def is_logged_in(self) -> bool:
        """是否已处于登录状态."""
        return self._vault.is_logged_in

    async def _get_json(self, path: str, **params: Any) -> dict[str, Any]:
        """请求同花顺接口并返回 JSON 载荷.

        Args:
            path: 接口路径（如 "/qrcode"）.
            **params: 附加查询参数.

        Returns:
            接口返回的 JSON 字典.

        Raises:
            httpx.HTTPStatusError: 接口返回非 2xx 状态码时抛出.
        """
        headers = {}
        session = self._vault.load_session()
        if session and session.get("token"):
            headers["Authorization"] = f"Bearer {session['token']}"
        r = await self._client.get(self._prefix + path,
                                   params=params,
                                   headers=headers,
                                   timeout=self._timeout)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        return data

    async def login_qrcode(self) -> dict:
        """获取登录二维码数据.

        Returns:
            包含 ``qrcode_data`` 字段的字典；请求失败时字段为空串.
        """
        data = await self._get_json("/qrcode")
        self._pending_qr = data.get("data", {})
        return {"qrcode_data": self._pending_qr.get("qrcode", "")}

    async def poll_login(self) -> bool:
        """轮询登录状态，成功后保存会话凭据.

        Returns:
            登录成功返回 True，否则返回 False.
        """
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
        """查询当前自选股列表.

        Returns:
            自选股 Stock 列表.
        """
        data = await self._get_json("/watchlist")
        return parse_watchlist(_json_text(data))

    async def query_positions(self) -> list[Position]:
        """查询当前持仓列表.

        Returns:
            持仓 Position 列表.
        """
        data = await self._get_json("/positions")
        return parse_positions(_json_text(data))

    async def refresh_session(self) -> bool:
        """刷新/校验会话是否仍然有效.

        Returns:
            会话有效返回 True；请求异常返回 False.
        """
        try:
            await self._get_json("/session/check")
            return True
        except Exception as e:
            logger.warning("会话保活失败: %s", e)
            return False

    async def logout(self) -> None:
        """登出并清除本地会话凭据."""
        self._vault.clear()


def _json_text(data: dict) -> str:
    """把接口返回 JSON 字典中的 data 字段序列化为文本.

    Args:
        data: 接口返回的 JSON 字典.

    Returns:
        序列化后的 data 文本；data 缺失时返回 "[]".
    """
    return json.dumps(data.get("data", []), ensure_ascii=False)
