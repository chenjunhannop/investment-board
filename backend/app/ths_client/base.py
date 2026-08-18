"""同花顺只读客户端抽象接口.

只负责登录与会话/自选/持仓查询，禁止添加任何交易类方法.
"""
from abc import ABC, abstractmethod

from app.models import Position, Stock


class ThsAdapter(ABC):
    """同花顺只读客户端抽象基类（禁止交易）."""

    @abstractmethod
    async def login_qrcode(self) -> dict:
        """获取登录二维码数据.

        Returns:
            包含 ``qrid`` 与 ``qrcode_img``（base64 PNG）字段的字典.
        """
        ...

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

    @abstractmethod
    async def query_watchlist(self) -> list[Stock]:
        """查询当前自选股列表.

        Returns:
            自选股 Stock 列表.
        """
        ...

    @abstractmethod
    async def query_positions(self) -> list[Position]:
        """查询当前持仓列表.

        Returns:
            持仓 Position 列表.
        """
        ...

    @abstractmethod
    async def refresh_session(self) -> bool:
        """刷新/校验会话是否仍然有效.

        Returns:
            会话有效返回 True，否则返回 False.
        """
        ...

    @property
    @abstractmethod
    def is_logged_in(self) -> bool:
        """是否已处于登录状态."""
        ...

    @abstractmethod
    async def logout(self) -> None:
        """登出并清除本地会话凭据."""
        ...
