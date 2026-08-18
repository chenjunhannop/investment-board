# backend/app/config.py
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8210
    data_dir: Path = Path.home() / ".investment-board"
    ths_endpoint_prefix: str = "https://eq.10jqka.com.cn"
    quotes_interval: float = 3.0
    positions_interval: float = 10.0
    news_interval: float = 60.0


settings = Settings()
settings.port = int(os.environ.get("IB_PORT", settings.port))
settings.data_dir = Path(os.environ.get("IB_DATA_DIR", str(settings.data_dir)))
settings.ths_endpoint_prefix = os.environ.get("IB_THS_ENDPOINT", settings.ths_endpoint_prefix)
