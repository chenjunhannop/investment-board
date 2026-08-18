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
