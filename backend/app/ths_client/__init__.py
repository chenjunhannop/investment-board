"""同花顺网页版只读客户端：抽象接口与 HTTP 实现."""
from app.ths_client.base import ThsAdapter
from app.ths_client.web_client import ThsWebClient

__all__ = ["ThsAdapter", "ThsWebClient"]
