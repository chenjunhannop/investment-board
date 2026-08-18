"""同花顺网页版只读客户端（逆向接口实现）.

只读约束：本模块仅负责登录与查询（自选/持仓），严禁添加任何交易类方法.
接口 endpoint 的逆向值与字段说明见 README.md.
"""
import base64
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

    async def _get_json(self, path: str, **params: Any) -> dict[str, Any]:
        """请求同花顺接口并返回 JSON 载荷（cookie 鉴权）.

        Args:
            path: 接口路径.
            **params: 附加查询参数.

        Returns:
            接口返回的 JSON 字典.

        Raises:
            httpx.HTTPStatusError: 接口返回非 2xx 状态码时抛出.
        """
        r = await self._client.get(self._prefix + path, params=params, timeout=self._timeout)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        return data

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
