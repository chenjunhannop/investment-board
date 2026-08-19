"""一次性预置自选数据：持仓 + 15 领域龙头（每领域 7 只），逐只验证代码有效性.

用法: backend/.venv/bin/python scripts/seed_watchlist.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.config import settings
from app.core import watchlist

DEFAULT_GROUPS = [
    {"name": "持仓", "codes": ["600900", "601318", "000333", "002714", "600519", "002027"]},
    {"name": "银行", "codes": ["600036", "601398", "601939", "601288", "601166", "000001", "002142"]},
    {"name": "保险", "codes": ["601318", "601628", "601601", "601336", "601319", "002423", "000987"]},
    {"name": "白酒", "codes": ["600519", "000858", "000568", "600809", "002304", "000596", "603369"]},
    {"name": "家电", "codes": ["000333", "000651", "600690", "000921", "002508", "002032", "000100"]},
    {"name": "电力", "codes": ["600900", "600011", "600795", "601985", "600905", "600886", "600027"]},
    {"name": "养殖", "codes": ["002714", "300498", "000876", "002157", "002124", "002567", "300761"]},
    {"name": "传媒", "codes": ["002027", "300413", "300251", "300133", "600373", "601928", "601900"]},
    {"name": "医药", "codes": ["600276", "603259", "300760", "300015", "600436", "000538", "300122"]},
    {"name": "新能源", "codes": ["300750", "601012", "300274", "600438", "300014", "688599", "002460"]},
    {"name": "半导体", "codes": ["688981", "603501", "002371", "688012", "603986", "688008", "300661"]},
    {"name": "消费电子", "codes": ["002475", "002241", "300433", "000725", "601138", "600745", "688036"]},
    {"name": "券商", "codes": ["600030", "300059", "601688", "601211", "600999", "000776", "601995"]},
    {"name": "汽车", "codes": ["002594", "601633", "000625", "601127", "601238", "600104", "600660"]},
    {"name": "有色", "codes": ["601899", "603993", "600111", "600547", "603799", "000807", "601600"]},
    {"name": "石油石化", "codes": ["601857", "600028", "600938", "002493", "600346", "600309", "002648"]},
]


def verify_code(client: httpx.Client, code: str) -> bool:
    """用新浪行情接口验证股票代码是否有效.

    Args:
        client: httpx 客户端.
        code: 6 位股票代码.

    Returns:
        接口返回有效行情（股票名非空）返回 True.
    """
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    r = client.get(f"https://hq.sinajs.cn/list={prefix}{code}",
                   headers={"Referer": "https://finance.sina.com.cn"}, timeout=8)
    body = r.text
    # 新浪返回 var hq_str_sh600519="贵州茅台,..."；无效代码返回空引号
    return '"' in body and body.split('"')[1].strip() != ""


def main() -> None:
    """验证代码有效性并写入预置自选（跳过无效代码）."""
    client = httpx.Client()
    removed = []
    try:
        for g in DEFAULT_GROUPS:
            watchlist.add_group(settings.data_dir, g["name"])
            for code in g["codes"]:
                if verify_code(client, code):
                    watchlist.add_stock(settings.data_dir, g["name"], code)
                else:
                    removed.append(f"{g['name']}:{code}")
                    print(f"[跳过无效] {g['name']}:{code}")
    finally:
        client.close()
    data = watchlist.load_watchlist(settings.data_dir)
    total = sum(len(g["stocks"]) for g in data["groups"])
    print(f"完成：{len(data['groups'])} 个文件夹，{total} 只股票；无效剔除 {len(removed)} 只")
    if removed:
        print("剔除清单:", removed)


if __name__ == "__main__":
    main()
