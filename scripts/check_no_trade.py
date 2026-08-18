#!/usr/bin/env python3
# scripts/check_no_trade.py
"""合规静态检查：禁止后端出现交易语义的标识符或中文词。

设计说明：
- 用 AST 解析 Python 源码，检查所有标识符（函数/方法/类/变量/属性/参数名）
  是否以危险交易词为前缀（如 buy_stock、place_order、sell_shares 均会命中）。
  AST 方式天然排除字符串字面量、注释、文档字符串，避免误报；
  同时不会漏掉 buy_stock 这类组合标识符（正则 \\bbuy\\b 会漏）。
- 中文交易词（委托/下单/撤单/成交/买入/卖出）单独扫描非注释/非文档字符串行。
- 命中任一规则即非零码退出。

这是"代码级只读"合规承诺的静态防线：任何向 THS 客户端添加交易能力
的改动都必须在此被拦截，而不是靠代码审查纪律。
"""
import ast
import sys
from pathlib import Path

DANGER_PREFIXES = (
    "buy", "sell", "trade", "order",
    "place_order", "easytrader",
)
DANGER_CHINESE = ("委托", "下单", "撤单", "成交", "买入", "卖出")

ROOT = Path(__file__).resolve().parent.parent
HITS: list[str] = []


def _check_identifier(path: Path, name: str) -> None:
    """检查单个标识符是否命中交易语义前缀（含前缀词本身）。"""
    lower = name.lower()
    for prefix in DANGER_PREFIXES:
        if lower == prefix or lower.startswith(prefix):
            HITS.append(
                f"{path.relative_to(ROOT)}: 标识符 '{name}' 命中交易语义前缀 '{prefix}'"
            )


def _names_of(node) -> list[str]:
    """提取一个 AST 节点携带的标识符名（类型/属性/定义名/参数名）。"""
    names: list[str] = []
    if isinstance(node, ast.Name):
        names.append(node.id)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names.append(node.name)
    elif isinstance(node, ast.Attribute):
        names.append(node.attr)
    elif isinstance(node, ast.arg):
        names.append(node.arg)
    return names


def check_file(path: Path) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as e:
        HITS.append(f"{path.relative_to(ROOT)}: 语法错误 {e}")
        return

    for node in ast.walk(tree):
        for name in _names_of(node):
            _check_identifier(path, name)

    # 中文交易词：逐行扫描，跳过注释与文档字符串（AST 不覆盖中文字符串语义）
    in_doc = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if in_doc:
            if stripped.count('"""') + stripped.count("'''") % 2 == 1:
                in_doc = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') + stripped.count("'''") % 2 == 1:
                in_doc = True
            continue
        if stripped.startswith("#"):
            continue
        for word in DANGER_CHINESE:
            if word in line:
                HITS.append(
                    f"{path.relative_to(ROOT)}:{i}: 命中交易语义 '{word}'"
                )


for f in (ROOT / "backend/app").rglob("*.py"):
    check_file(f)

if HITS:
    print("命中交易语义，合规检查失败：")
    for h in HITS:
        print(" -", h)
    sys.exit(1)

print("OK: 未发现交易语义代码。")
