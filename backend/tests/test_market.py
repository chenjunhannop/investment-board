"""行情解析与服务（去重合并、源切换）的单元测试."""
import httpx
import pytest
from respx import MockRouter

from app.market.parsers import parse_sina, parse_sina_intraday, parse_tencent
from app.market.service import MarketService

SINA_LINE = ('var hq_str_sh600519="贵州茅台,1700.00,1700.00,1750.00,'
             '1760.00,1690.00,1750.00,1751.00,30000,520000000.00,'
             '...,2026-08-18,10:30:00,00";')
SINA_LINE_SZ = ('var hq_str_sz000001="平安银行,12.00,11.90,12.50,12.60,11.80,'
                '12.50,12.51,20000,250000000.00,'
                '...,2026-08-18,10:30:00,00";')
TENCENT_LINE = ('v_sh600519="1~贵州茅台~600519~1750.00~1700.00~1700.00~'
                '30000~52000~26000~1750.00~100~1749.00~200~1748.00~300~'
                '1747.00~400~1746.00~500~1750.00~100~1751.00~200~1752.00~'
                '300~1753.00~400~1754.00~500~1750.00~20260818103000~'
                '50.00~2.94~1760.00~1690.00~1750.00~30000~52000~1.15~28.50~7.20";')


def test_parse_sina_quote():
    """解析新浪行情行得到正确的代码/名称/价格与涨跌字段."""
    q = parse_sina(SINA_LINE)
    assert q.code == "600519"
    assert q.name == "贵州茅台"
    assert q.price == 1750.0
    assert q.prev_close == 1700.0
    assert q.change == 50.0
    assert round(q.change_pct, 2) == 2.94


def test_parse_tencent_quote():
    """解析腾讯行情行得到正确的代码/价格/涨跌幅."""
    q = parse_tencent(TENCENT_LINE)
    assert q.code == "600519"
    assert q.price == 1750.0
    assert q.change_pct == 2.94


def test_parse_sina_intraday():
    """解析新浪分时文本得到若干日内数据点."""
    text = '1,09:30,1700.00,1700.00,100\n2,09:31,1701.00,1700.50,200\n'
    pts = parse_sina_intraday(text)
    assert len(pts) == 2
    assert pts[0].time == "09:30"
    assert pts[0].price == 1700.0


@pytest.mark.asyncio
async def test_fetch_quotes_dedupes_and_merges(respx_mock: MockRouter):
    """重复代码去重合并后返回去重的行情结果."""
    respx_mock.get("https://hq.sinajs.cn/list=sh600519,sz000001").mock(
        return_value=httpx.Response(200, text=SINA_LINE + "\n" + SINA_LINE_SZ))
    svc = MarketService(httpx.AsyncClient())
    quotes = await svc.fetch_quotes(["600519", "600519", "000001", "000001"])
    assert set(quotes) == {"600519", "000001"}
    assert svc.primary_source == "sina"


@pytest.mark.asyncio
async def test_fetch_quotes_falls_back_when_sina_fails(respx_mock: MockRouter):
    """新浪源失败时自动切换到腾讯源."""
    respx_mock.get("https://hq.sinajs.cn/list=sh600519").mock(return_value=httpx.Response(500))
    respx_mock.get("https://qt.gtimg.cn/q=sh600519").mock(
        return_value=httpx.Response(200, text=TENCENT_LINE))
    svc = MarketService(httpx.AsyncClient())
    quotes = await svc.fetch_quotes(["600519"])
    assert quotes["600519"].name == "贵州茅台"
    assert svc.primary_source == "tencent"
