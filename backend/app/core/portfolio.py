"""持仓计算：将实时行情绑定到持仓，得出市值/盈亏/当日涨跌快照."""
from app.models import Position, Quote


def compute_positions(positions: list[Position], quotes: dict[str, Quote]) -> list[Position]:
    """绑定行情后计算每笔持仓的市值、盈亏与当日涨跌.

    Args:
        positions: 原始持仓列表（可能已有部分字段，行情相关字段将被覆盖）.
        quotes: 以股票代码为 key 的实时行情字典，缺失代码的持仓保持原值.

    Returns:
        与输入等长的新持仓列表；能匹配到行情的持仓字段被就地更新.
    """
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
