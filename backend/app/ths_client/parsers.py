"""同花顺接口返回文本的解析器.

解析自选与持仓接口返回的 JSON 文本为领域模型列表.
"""
import json

from app.models import Position, Stock


def parse_watchlist(text: str) -> list[Stock]:
    """解析自选股接口返回文本为 Stock 列表.

    Args:
        text: 自选股接口返回的 JSON 文本.

    Returns:
        Stock 列表；market 字段缺失时默认 "SH".

    Raises:
        ValueError: 文本不是合法 JSON 时抛出.
    """
    data = json.loads(text)
    stocks = []
    for item in data:
        stocks.append(Stock(
            code=item["code"],
            name=item["name"],
            market=item.get("market", "SH"),
        ))
    return stocks


def parse_positions(text: str) -> list[Position]:
    """解析持仓接口返回文本为 Position 列表.

    Args:
        text: 持仓接口返回的 JSON 文本.

    Returns:
        Position 列表；数量与成本字段会转为 int/float.

    Raises:
        ValueError: 文本不是合法 JSON 或必填字段缺失时抛出.
    """
    data = json.loads(text)
    positions = []
    for item in data:
        positions.append(
            Position(
                code=item["code"],
                name=item["name"],
                quantity=int(item["amount"]),
                cost_price=float(item["cost"]),
                available=int(item.get("enable_amount", 0)),
            ))
    return positions
