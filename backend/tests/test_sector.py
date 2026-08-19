"""东财板块/新浪指数解析器的单元测试."""
from app.market.sector import (
    parse_indices,
    parse_sector_board,
    parse_sector_kline,
    parse_sina_indices,
)

SINA = ('var hq_str_sh000001="上证指数,3952.12,3990.30,3893.49,3966.00,3880.00,0,0,'
        '2607014,56719724,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0";')


def test_parse_sina_indices():
    """新浪指数（GBK 已转码）解析为带高低开的指数快照."""
    r = parse_sina_indices(SINA)
    assert len(r) == 1
    assert r[0]["name"] == "上证指数"
    assert r[0]["price"] == 3893.49
    assert r[0]["open"] == 3952.12
    assert r[0]["prev_close"] == 3990.30
    assert abs(r[0]["change"] - (3893.49 - 3990.30)) < 0.001
    assert r[0]["change_pct"] < 0


INDEX = {
    "data": {
        "f43": 393086,
        "f44": 396114,
        "f45": 391708,
        "f46": 395212,
        "f57": "000001",
        "f58": "上证指数",
        "f60": 399030,
        "f169": -5944,
        "f170": -149
    }
}


def test_parse_indices():
    """指数 ×100 整数正确转浮点."""
    r = parse_indices(INDEX)[0]
    assert r["name"] == "上证指数"
    assert r["price"] == 3930.86
    assert r["change_pct"] == -1.49


def test_parse_sector_board_filters_cold():
    """冷门板块（含股 < 10）被过滤，父子层级去重."""
    data = {
        "data": {
            "diff": [
                {
                    "f12": "BK1",
                    "f14": "银行",
                    "f3": 90,
                    "f62": 100,
                    "f104": 37,
                    "f105": 0,
                    "f128": "招商银行",
                    "f140": "600036"
                },
                {
                    "f12": "BK2",
                    "f14": "银行Ⅱ",
                    "f3": 90,
                    "f62": 100,
                    "f104": 37,
                    "f105": 0,
                    "f128": "招商银行",
                    "f140": "600036"
                },
                {
                    "f12": "BK3",
                    "f14": "氨纶",
                    "f3": 356,
                    "f62": 5,
                    "f104": 1,
                    "f105": 0,
                    "f128": "",
                    "f140": ""
                },
            ]
        }
    }
    r = parse_sector_board(data)
    names = [x["name"] for x in r["top_gainers"]]
    assert names == ["银行"]  # 氨纶被过滤，银行Ⅱ去重
    assert r["top_gainers"][0]["change_pct"] == 90.0  # f3 不缩放（90 表示 90% 涨幅，测试数据）
    assert r["fund_flow"][0]["fund_flow"] == 100.0
    assert r["market"] == {"up": 75, "down": 0}


def test_parse_sector_kline():
    """K线字符串转结构化列表."""
    data = {"data": {"klines": ["2026-08-18,750.55,753.50,766.55,747.98,2809112,915286883.00"]}}
    r = parse_sector_kline(data)
    assert r[0][0] == "2026-08-18"
    assert r[0][2] == 753.50
    assert len(r[0]) == 7
