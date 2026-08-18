#!/usr/bin/env python3
# scripts/check_no_trade.py
"""合规静态检查：扫描代码库，禁止出现下单/交易语义。

遍历 backend/app，若在源码中发现以下词元（作为标识符/方法名/依赖名出现），
立即以非零码退出。仅允许在注释/文档字符串中以中文"严禁交易"等说明出现。
"""
import re
import sys
from pathlib import Path

FORBIDDEN = [
    r"\bplace_order\b", r"\bbuy\b", r"\bsell\b", r"\btrade\b",
    r"\border\b", r"easytrader", r"\b委托\b", r"\b下单\b",
    r"\b撤单\b", r"\b成交\b", r"\bamount.*buy", r"\bquantity.*sell",
]

ROOT = Path(__file__).resolve().parent.parent
HITS = []


def _is_docstring_open(stripped: str) -> bool:
    """判断三引号行是否开启了一个未在本行闭合的字符串/文档字符串。"""
    quotes = stripped.count('"""') + stripped.count("'''")
    return quotes % 2 == 1


def walk(py_files):
    for f in py_files:
        in_doc = False  # 是否处于多行文档字符串内部
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if in_doc:
                # 文档字符串内：仅在闭合行退出，其余行整行豁免
                if _is_docstring_open(stripped):
                    in_doc = False
                continue
            if stripped.startswith("#"):
                continue  # 注释豁免
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # 单行三引号字符串直接豁免；多行则进入文档字符串状态
                if _is_docstring_open(stripped):
                    in_doc = True
                continue  # 文档字符串/字符串字面量豁免
            for pat in FORBIDDEN:
                if re.search(pat, line):
                    HITS.append((f, i, pat, line.strip()))


walk((ROOT / "backend/app").rglob("*.py"))

# 允许在 docstring 中出现的"禁止添加任何交易类方法"等说明——
# 上面的多行文档字符串状态机已整行豁免；此处白名单作为兜底，
# 仅放过明显属于合规说明的行。
for f, i, pat, line in HITS:
    if "禁止添加" in line or "只读" in line or "合规" in line:
        continue
    print(f"{f.relative_to(ROOT)}:{i}: 命中交易语义 {pat!r} -> {line}")
    sys.exit(1)

print("OK: 未发现交易语义代码。")
