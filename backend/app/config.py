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
    # 前端构建产物目录：基于本文件位置解析到项目根 frontend/dist（与启动 CWD 无关）
    dist_dir: Path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    quotes_interval: float = 3.0
    news_interval: float = 60.0


settings = Settings()
settings.host = os.environ.get("IB_HOST", settings.host)
settings.port = int(os.environ.get("IB_PORT", settings.port))
settings.data_dir = Path(os.environ.get("IB_DATA_DIR", str(settings.data_dir)))
settings.dist_dir = Path(os.environ.get("IB_DIST_DIR", str(settings.dist_dir)))
