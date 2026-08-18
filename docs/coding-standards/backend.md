# 后端规范：Google Python Style Guide 落地

> 适用范围：`backend/`（Python 3.11，FastAPI 服务）。
> 权威来源：[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。
> 落地方式：`yapf`（格式化）+ `ruff`（lint）+ `mypy`（类型检查），规则集与行宽以 `backend/pyproject.toml` 为准。

## 1. 命名

按 Google 规范与 PEP8 命名约定（由 ruff N 规则检查）：

| 类别 | 写法 | 示例 |
| --- | --- | --- |
| 模块名 | `lower_with_under` | `market/parsers.py` |
| 包名 | `lower_with_under` | `ths_client` |
| 类名 | `CapWords` | `MarketService`、`ThsAdapter` |
| 方法 / 函数名 | `lower_with_under` | `fetch_quotes`、`_split_codes` |
| 常量 | `UPPER_WITH_UNDER` | `IB_TEST_KEYCHAIN` |
| 内部（私有）标识符 | 前导下划线 `_name` | `_normalize`、`_get_or_create_key` |

## 2. 类型注解

- **公开 API（模块公开函数 / 类 / 方法）必须完整注解**：参数类型、返回类型必填。
- **容器必须使用泛型标注**：`list[str]` / `dict[str, X]`，禁止裸 `list` / `dict`；可选值显式写 `Optional[...]` 或 `X | None`。
- **禁止可变默认参数**（如 `def f(x=[])`）。
- 由 `mypy` 强制执行（`check_untyped_defs`、`warn_return_any`、`no_implicit_optional`）。

```python
def _split_codes(self, codes: list[str]) -> list[str]:
    """把代码列表拆分为单个 6 位代码。"""
    ...
```

## 3. docstring（Google 风格）

模块、public 类 / 方法必须有 docstring。格式：`"""一行摘要。` + 空行 + 可选 `Args:` / `Returns:` / `Raises:` 段（无参数 / 无返回 / 无异常可省略对应段）。由 ruff D 规则（`pydocstyle.convention = "google"`）检查。

**模板（与代码重构使用的模板完全一致）：**

```python
def fetch_quotes(self, codes: list[str]) -> dict[str, Quote]:
    """按代码列表抓取实时行情。

    Args:
        codes: 6 位股票代码列表，如 ["600519", "000001"]。

    Returns:
        以代码为 key 的 Quote 字典；空列表返回空字典。
    """
```

- 摘要用陈述句、句末加句号。
- `Args:` 每个参数一行，格式 `参数名: 描述`。
- `Raises:` 注明会抛出的异常及触发条件（如解析失败抛 `ValueError`）。
- 类 docstring 一句话说明用途；模块 docstring 说明模块职责。

## 4. main() 入口

`backend/app/main.py` 必须包含：

```python
def main() -> None:
    """启动 uvicorn 开发服务器（仅监听本机）。"""
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
```

## 5. 异常

- **捕获用具体异常类型**，禁止裸 `except:`。
- 需要兜底捕获时（如网络抖动）用 `except Exception` 并在 docstring / 注释中说明原因。
- **抛出用 `raise XxxError(...)` 并带错误信息**；不要用裸 `raise` 或吞掉异常。

```python
try:
    text = resp.text
except requests.RequestException as exc:
    raise ValueError(f"行情接口请求失败: {exc}") from exc
```

## 6. import

- **分组**：stdlib / 第三方 / 本地，组与组之间空一行。
- **每组内按字母序**。
- 由 ruff I 规则自动检查与修复（`ruff check --fix`）。

```python
import asyncio
import time
from typing import Optional

import requests
from pydantic import BaseModel

from app.market.parsers import parse_sina
```

## 7. 字符串

- **统一使用 f-string**（Python 3.11），禁止 `%` 格式化与 `+` 拼接。

```python
url = f"https://hq.sinajs.cn/list={code}"
```

## 8. 工具配置说明

实际配置位于 `backend/pyproject.toml`（与工具链落地保持一致）：

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "D", "N", "ASYNC"]
ignore = ["E501"]  # 行宽由 yapf 保证

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.yapf]
based_on_style = "google"
column_limit = 100

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
warn_return_any = true
warn_unused_ignores = true
no_implicit_optional = true
```

使用要点：

- **行宽 100**：yapf `column_limit=100` 与 ruff `line-length=100` 对齐；E501 交给 yapf 管。
- **唯一 formatter 是 yapf**（`based_on_style="google"`），**禁止使用 `ruff format`**，避免与 yapf 冲突。
- 常用命令（在 `backend/` 下用 `backend/.venv/bin/`）：

```bash
.venv/bin/yapf -ri app tests          # 全量 Google 风格格式化
.venv/bin/ruff check app tests        # lint（D10x 缺 docstring 按需补齐）
.venv/bin/ruff check app --fix        # 自动修复可修复项（如 import 排序）
.venv/bin/mypy app                    # 类型检查
```
