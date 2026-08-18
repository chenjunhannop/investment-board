import json

from app.models import Position, Stock


def parse_watchlist(text: str) -> list[Stock]:
    data = json.loads(text)
    stocks = []
    for item in data:
        stocks.append(Stock(
            code=item["code"], name=item["name"],
            market=item.get("market", "SH"),
        ))
    return stocks


def parse_positions(text: str) -> list[Position]:
    data = json.loads(text)
    positions = []
    for item in data:
        positions.append(Position(
            code=item["code"], name=item["name"],
            quantity=int(item["amount"]), cost_price=float(item["cost"]),
            available=int(item.get("enable_amount", 0)),
        ))
    return positions
