"""全局配置：从环境变量读取运行参数，提供唯一 settings 单例."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    """后端运行配置（主机、端口、数据目录与各轮询周期）."""

    host: str = "127.0.0.1"
    port: int = 8210
    data_dir: Path = Path.home() / ".investment-board"
    ths_endpoint_prefix: str = "https://upass.10jqka.com.cn"
    ths_watchlist_url: str = ""
    ths_positions_url: str = ""
    quotes_interval: float = 3.0
    positions_interval: float = 10.0
    news_interval: float = 60.0


settings = Settings()
settings.port = int(os.environ.get("IB_PORT", settings.port))
settings.data_dir = Path(os.environ.get("IB_DATA_DIR", str(settings.data_dir)))
settings.ths_endpoint_prefix = os.environ.get("IB_THS_ENDPOINT", settings.ths_endpoint_prefix)
settings.ths_watchlist_url = os.environ.get("IB_THS_WATCHLIST_URL", settings.ths_watchlist_url)
settings.ths_positions_url = os.environ.get("IB_THS_POSITIONS_URL", settings.ths_positions_url)
