# backend/app/market/service.py
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
    # "600519" -> "sh600519", "000001" -> "sz000001"
    return ("sh" if code.startswith(("6", "9")) else "sz") + code


def _split_codes(codes: list[str]) -> str:
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(_normalize(c))
    return ",".join(out)


class MarketService:
    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        self._client = client
        self._timeout = timeout
        self.primary_source = "sina"
        self.fallback_source = "tencent"

    async def fetch_quotes(self, codes: list[str]) -> dict[str, Quote]:
        query = _split_codes(codes)
        if not query:
            return {}
        for source, url in ((self.primary_source, SINA_QUOTE_URL),
                            (self.fallback_source, TENCENT_QUOTE_URL)):
            try:
                r = await self._client.get(
                    url.format(codes=query), timeout=self._timeout,
                    headers={"Referer": "https://finance.sina.com.cn"})
                r.raise_for_status()
                return self._parse_all(source, r.text, codes)
            except Exception as e:
                logger.warning("行情源 %s 失败，切换: %s", source, e)
                self.primary_source, self.fallback_source = (
                    self.fallback_source, self.primary_source)
        return {}

    def _parse_all(self, source: str, text: str, codes: list[str]) -> dict[str, Quote]:
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
        try:
            r = await self._client.get(SINA_INTRA.format(c=code),
                                       timeout=self._timeout)
            r.raise_for_status()
            return parse_sina_intraday(r.text)
        except Exception as e:
            logger.warning("分时获取失败 %s: %s", code, e)
            return []
