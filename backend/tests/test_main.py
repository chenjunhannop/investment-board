"""应用装配与默认配置的单元测试."""


def test_app_importable():
    """App 模块可导入且标题正确."""
    from app.main import app
    assert app.title == "Investment Board"


def test_default_port():
    """未设置 IB_PORT 时默认端口为 8210."""
    import os
    os.environ.pop("IB_PORT", None)
    from app.config import settings
    assert settings.port == 8210
