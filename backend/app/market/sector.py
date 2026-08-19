"""东财板块/新浪指数数据服务（公开接口，含冷门过滤与异常兜底）.

数据来源：新浪指数 hq.sinajs.cn、东方财富行业板块 clist/get 与板块日K kline/get。
东财接口对 httpx TLS 指纹阻断，故用系统 curl 请求（curl 指纹被接受）。
所有接口为只读公开数据，不涉及任何交易操作.
"""
import asyncio
import json
import logging
import re
import subprocess
import time

import httpx

logger = logging.getLogger(__name__)

EM_HEADERS = ["Referer: https://quote.eastmoney.com/"]

EM_HOSTS = ["push2.eastmoney.com", "push2delay.eastmoney.com", "push2his.eastmoney.com"]


def _curl_json(url: str, request_timeout: float, retries: int = 4) -> dict:
    """用系统 curl 请求东财接口，带多域名 fallback（规避限流/断开）.

    Args:
        url: 东财接口地址（host 会被逐个替换尝试）.
        request_timeout: 单次请求超时秒数.
        retries: 每个域名重试次数.

    Returns:
        接口返回的 JSON 字典.

    Raises:
        RuntimeError: 全部域名重试耗尽仍失败时抛出.
    """
    last: Exception | None = None
    for host in EM_HOSTS:
        # 替换 URL 中的 host（东财多域名同构，备选域名可绕过临时限流）
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(url)
        alt_url = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
        for attempt in range(retries):
            try:
                r = subprocess.run([
                    "curl", "-s", "--max-time",
                    str(int(request_timeout)), "-H", "Referer: https://quote.eastmoney.com/",
                    alt_url
                ],
                                   capture_output=True,
                                   text=True,
                                   timeout=request_timeout + 3)
                if r.returncode == 0 and r.stdout.strip():
                    return json.loads(r.stdout)
                last = RuntimeError(f"curl {host} exit {r.returncode}")
            except Exception as e:
                last = e
            time.sleep(0.5 * (attempt + 1))
    raise last if last else RuntimeError("curl request failed")


INDEX_SECIDS = ["1.000001", "0.399001", "0.399006"]  # 上证/深证/创业板（东财 secid，备用）
SINA_INDEX_URL = "https://hq.sinajs.cn/list=sh000001,sz399001,sz399006"
SINA_INDEX_KLINE_URL = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20x="
                        "/CN_MarketDataService.getKLineData?symbol={sym}"
                        "&scale=240&ma=no&datalen=30")
SECTOR_LIST_URL = ("https://push2.eastmoney.com/api/qt/clist/get"
                   "?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3"
                   "&fs=m:90+t:2&fields=f2,f3,f12,f14,f62,f104,f105,f128,f140")
KLINE_URL = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
             "?fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
             "&klt=101&fqt=1&lmt=60&end=20500101")
MIN_STOCKS = 10  # 冷门过滤：板块含股数下限


async def _get_with_retry(client: httpx.AsyncClient,
                          url: str,
                          request_timeout: float,
                          retries: int = 5) -> httpx.Response:
    """带重试的 GET 请求，缓解东财对复用连接偶发断开的抖动.

    Args:
        client: 共享 httpx 客户端.
        url: 请求地址.
        request_timeout: 单次请求超时秒数.
        retries: 重试次数（默认 5，东财偶发断开较多）.

    Returns:
        成功的 httpx.Response.

    Raises:
        httpx.HTTPError: 重试耗尽后仍失败时抛出最后一次异常.
    """
    import asyncio

    last: Exception | None = None
    for attempt in range(retries):
        try:
            return await client.get(url,
                                    headers={"Referer": "https://quote.eastmoney.com/"},
                                    timeout=request_timeout)
        except Exception as e:  # 东财偶发 Server disconnected，新连接通常可成功
            last = e
            await asyncio.sleep(0.3 * (attempt + 1))
    raise last if last else httpx.HTTPError("request failed")


def _num(value, scale: float = 1.0, default: float = 0.0) -> float:
    """把东财 ×100 整数或数值转为浮点，缺失用默认值.

    Args:
        value: 东财接口返回的数值（可能为 None）.
        scale: 缩放系数，默认 1.0（如指数报价需 /100）.
        default: 缺失时的默认值.

    Returns:
        缩放后的浮点值.
    """
    if value is None:
        return default
    try:
        return float(value) / scale
    except (TypeError, ValueError):
        return default


def _clean_name(name: str) -> str:
    """去除板块名 Ⅱ/Ⅲ 后缀用于去重.

    Args:
        name: 东财板块名，如 "股份制银行Ⅲ".

    Returns:
        去后缀后的名字，如 "股份制银行".
    """
    for suffix in ("Ⅲ", "Ⅱ"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def parse_sina_index_kline(text: str) -> list[list]:
    """解析新浪指数 K线 JSONP 为 klines 列表.

    输入: var x=([{"day":...,"open":...,"high":...,"low":...,"close":...,"volume":...},...]);

    Args:
        text: 新浪指数 K线响应原文.

    Returns:
        [[day, open, close, high, low, volume, 0], ...]（末位补 amount=0 兼容板块 K线格式）.
    """
    m = re.search(r'\(\[(.*)\]\);', text, re.S)
    if not m:
        return []
    try:
        data = json.loads("[" + m.group(1) + "]")
    except json.JSONDecodeError:
        return []
    rows: list[list] = []
    for it in data:
        try:
            rows.append([
                it["day"],
                float(it["open"]),
                float(it["close"]),
                float(it["high"]),
                float(it["low"]),
                float(it["volume"]),
                0.0,
            ])
        except (KeyError, ValueError):
            continue
    return rows


def parse_sina_indices(text: str) -> list[dict]:
    """解析新浪指数响应（GBK，含高低开）.

    格式: var hq_str_sh000001="名称,开盘,昨收,当前,最高,最低,买一,卖一,量,额,..."

    Args:
        text: 新浪指数响应原文（GBK 编码）.

    Returns:
        指数字典列表（code/name/price/high/low/open/prev_close/change/change_pct）.
    """
    lines = text.splitlines()
    out: list[dict] = []
    for line in lines:
        m = re.search(r'hq_str_(\w+)="(.*)"', line)
        if not m:
            continue
        code = m.group(1)
        fields = m.group(2).split(",")
        if len(fields) < 10:
            continue
        name = fields[0]
        try:
            open_p = float(fields[1])
            prev_close = float(fields[2])
            price = float(fields[3])
            high = float(fields[4])
            low = float(fields[5])
        except ValueError:
            continue
        change = price - prev_close
        change_pct = change / prev_close * 100.0 if prev_close else 0.0
        out.append({
            "code": code,
            "name": name,
            "price": price,
            "high": high,
            "low": low,
            "open": open_p,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
        })
    return out


def parse_indices(data: dict) -> list[dict]:
    """解析东财指数 stock/get 响应为指数快照列表.

    Args:
        data: 单只指数接口返回的 {"data": {...}} 字典.

    Returns:
        指数字典列表（code/name/price/high/low/open/prev_close/change/change_pct）.
    """
    d = data.get("data") or {}
    price = _num(d.get("f43"), 100.0)
    prev_close = _num(d.get("f60"), 100.0)
    return [{
        "code": d.get("f57", ""),
        "name": d.get("f58", ""),
        "price": price,
        "high": _num(d.get("f44"), 100.0),
        "low": _num(d.get("f45"), 100.0),
        "open": _num(d.get("f46"), 100.0),
        "prev_close": prev_close,
        "change": _num(d.get("f169"), 100.0),
        "change_pct": _num(d.get("f170"), 100.0),
    }]


def parse_sector_board(data: dict) -> dict:
    """解析东财板块列表响应，过滤冷门并去重父子层级.

    Args:
        data: clist/get 响应（{"data": {"diff": [...]}}）.

    Returns:
        {"top_gainers": [...], "top_losers": [...], "fund_flow": [...],
         "market": {"up": int, "down": int}}.
    """
    diff = (data.get("data") or {}).get("diff") or []
    seen: dict[str, dict] = {}
    market_up = market_down = 0
    for it in diff:
        up = int(it.get("f104") or 0)
        down = int(it.get("f105") or 0)
        market_up += up
        market_down += down
        if up + down < MIN_STOCKS:
            continue  # 冷门板块过滤
        raw_name = it.get("f14", "")
        name = _clean_name(raw_name)
        if name in seen:
            continue  # 父子层级去重
        seen[name] = {
            "secid": f"90.{it.get('f12', '')}",
            "name": raw_name,
            "change_pct": _num(it.get("f3")),  # f3 已是百分比（如 6.28 表示 6.28%），无需缩放
            "fund_flow": _num(it.get("f62")),
            "leader": it.get("f128", ""),
            "leader_code": it.get("f140", ""),
            "stocks": up + down,
        }
    rows = list(seen.values())
    top_gainers = sorted(rows, key=lambda r: r["change_pct"], reverse=True)[:5]
    top_losers = sorted(rows, key=lambda r: r["change_pct"])[:5]
    fund_flow = sorted(rows, key=lambda r: r["fund_flow"], reverse=True)[:10]
    return {
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "fund_flow": fund_flow,
        "market": {
            "up": market_up,
            "down": market_down
        },
    }


def parse_sector_kline(data: dict) -> list[list]:
    """解析东财板块日K响应为 klines 列表.

    Args:
        data: kline/get 响应.

    Returns:
        [[date, open, close, high, low, volume, amount], ...] 近 60 日.
    """
    klines = (data.get("data") or {}).get("klines") or []
    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append([
                parts[0],
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
                float(parts[4]),
                float(parts[5]),
                float(parts[6]),
            ])
    return rows


async def fetch_indices(client: httpx.AsyncClient) -> list[dict]:
    """抓取上证/深证/创业板指数快照与日K线（新浪数据源，稳定）.

    Args:
        client: 共享 httpx 客户端.

    Returns:
        指数字典列表（含 kline 字段）；失败时返回空列表.
    """
    last: Exception | None = None
    for _ in range(3):
        try:
            r = await client.get(SINA_INDEX_URL,
                                 headers={"Referer": "https://finance.sina.com.cn/"},
                                 timeout=8)
            r.raise_for_status()
            out = parse_sina_indices(r.content.decode("gbk", "ignore"))
            # 为每个指数拉日K（新浪 K线稳定，指数卡展示真实 K线）
            for idx in out:
                try:
                    kr = await client.get(SINA_INDEX_KLINE_URL.format(sym=idx["code"]),
                                          headers={"Referer": "https://finance.sina.com.cn/"},
                                          timeout=8)
                    kr.raise_for_status()
                    idx["kline"] = parse_sina_index_kline(kr.text)
                except Exception as e:
                    logger.warning("抓取指数 %s K线失败: %s", idx["code"], e)
                    idx["kline"] = []
            return out
        except Exception as e:
            last = e
            await asyncio.sleep(0.3)
    logger.warning("抓取指数失败: %s", last)
    return []


async def fetch_sector_board(client: httpx.AsyncClient) -> dict:
    """抓取行业板块排行（含资金/家数/领涨股，冷门过滤）.

    Args:
        client: 共享 httpx 客户端（保留签名兼容，实际用 curl 请求东财）.

    Returns:
        parse_sector_board 结果；失败时返回空结构.
    """
    try:
        data = await asyncio.to_thread(_curl_json, SECTOR_LIST_URL, 10.0)
        return parse_sector_board(data)
    except Exception as e:
        logger.warning("抓取板块排行失败: %s", e)
        return {
            "top_gainers": [],
            "top_losers": [],
            "fund_flow": [],
            "market": {
                "up": 0,
                "down": 0
            }
        }


async def fetch_sector_kline(client: httpx.AsyncClient, secid: str) -> list[list]:
    """抓取单个板块近 60 日K线.

    Args:
        client: 共享 httpx 客户端（保留签名兼容，实际用 curl 请求东财）.
        secid: 东财板块 secid，如 "90.BK1036".

    Returns:
        日K列表；失败时返回空列表.
    """
    try:
        data = await asyncio.to_thread(_curl_json, f"{KLINE_URL}&secid={secid}", 8.0)
        return parse_sector_kline(data)
    except Exception as e:
        logger.warning("抓取板块 %s K线失败: %s", secid, e)
        return []
