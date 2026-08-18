"""行情服务：按代码列表抓取实时行情，并在新浪/腾讯两个数据源间自动切换.

主数据源为新浪，失败时自动切换备用源腾讯；同时提供日内分时数据获取.
"""
import logging

import httpx

from app.market.parsers import parse_sina, parse_sina_intraday, parse_tencent
from app.models import IntradayPoint, Quote

logger = logging.getLogger(__name__)

SINA_QUOTE_URL = "https://hq.sinajs.cn/list={codes}"
SINA_INTRA = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{c}.html="
              "/CN_MarketDataService.getKLineData?symbol={c}&scale=60&ma=no&datalen=1")
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={codes}"


def _normalize(code: str) -> str:
    """把 6 位股票代码转换为带交易所前缀的行情代码.

    Args:
        code: 6 位股票代码，如 "600519".

    Returns:
        带前缀的代码，如 "600519" -> "sh600519"，"000001" -> "sz000001".
    """
    # "600519" -> "sh600519", "000001" -> "sz000001"
    return ("sh" if code.startswith(("6", "9")) else "sz") + code


def _split_codes(codes: list[str]) -> str:
    """去重并归一化代码列表，拼接为行情接口可用的查询串.

    Args:
        codes: 6 位股票代码列表.

    Returns:
        逗号分隔的规范化代码串；空列表返回空串.
    """
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(_normalize(c))
    return ",".join(out)


class MarketService:
    """实时行情服务：主备数据源切换 + 日内分时获取."""

    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        """初始化行情服务.

        Args:
            client: 共享的 httpx 异步客户端.
            timeout: 单次请求超时秒数，默认 10 秒.
        """
        self._client = client
        self._timeout = timeout
        self.primary_source = "sina"
        self.fallback_source = "tencent"

    async def fetch_quotes(self, codes: list[str]) -> dict[str, Quote]:
        """按代码列表抓取实时行情.

        Args:
            codes: 6 位股票代码列表，如 ["600519", "000001"].

        Returns:
            以代码为 key 的 Quote 字典；空列表返回空字典，两个源都失败也返回空字典.
        """
        query = _split_codes(codes)
        if not query:
            return {}
        for source, url in ((self.primary_source, SINA_QUOTE_URL), (self.fallback_source,
                                                                    TENCENT_QUOTE_URL)):
            try:
                r = await self._client.get(url.format(codes=query),
                                           timeout=self._timeout,
                                           headers={"Referer": "https://finance.sina.com.cn"})
                r.raise_for_status()
                return self._parse_all(source, r.text, codes)
            except Exception as e:
                logger.warning("行情源 %s 失败，切换: %s", source, e)
                self.primary_source, self.fallback_source = (self.fallback_source,
                                                             self.primary_source)
        return {}

    def _parse_all(self, source: str, text: str, codes: list[str]) -> dict[str, Quote]:
        """按数据源选择解析器，逐行解析行情文本为 Quote 字典.

        Args:
            source: 数据源标识（"sina" 或 "tencent"）.
            text: 行情接口返回的文本.
            codes: 原始 6 位代码列表（保留用于字典 key 对齐）.

        Returns:
            以代码为 key 的 Quote 字典；单行解析失败会被跳过.
        """
        result: dict[str, Quote] = {}
        parser = parse_sina if source == "sina" else parse_tencent
        for line in text.strip().splitlines():
            if '="' not in line:
                continue
            try:
                q = parser(line)
                result[q.code] = q
            except Exception:
                continue
        return result

    async def fetch_intraday(self, code: str) -> list[IntradayPoint]:
        """获取单只股票的日内分时数据.

        Args:
            code: 6 位股票代码.

        Returns:
            分时数据点列表；获取失败时返回空列表.
        """
        try:
            r = await self._client.get(SINA_INTRA.format(c=code), timeout=self._timeout)
            r.raise_for_status()
            return parse_sina_intraday(r.text)
        except Exception as e:
            logger.warning("分时获取失败 %s: %s", code, e)
            return []
