from app.models import Position, Quote


def compute_positions(positions: list[Position],
                      quotes: dict[str, Quote]) -> list[Position]:
    out = []
    for p in positions:
        q = quotes.get(p.code)
        if q:
            p.current_price = q.price
            p.market_value = round(p.quantity * q.price, 2)
            p.profit = round((q.price - p.cost_price) * p.quantity, 2)
            p.profit_pct = round((q.price - p.cost_price) / p.cost_price * 100, 2)
            p.day_change = round(q.change * p.quantity, 2)
            p.day_change_pct = q.change_pct
        out.append(p)
    return out
