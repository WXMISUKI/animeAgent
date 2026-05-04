# config.py
"""配置管理"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置"""

    # LLM 配置（豆包 / Volcengine Ark）
    ORCH_API_BASE: str = os.getenv("ORCH_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
    ORCH_MODEL: str = os.getenv("ORCH_MODEL", "")
    ORCH_API_KEY: str = os.getenv("ORCH_API_KEY", "")

    # 数据源配置
    BANGUMI_API_URL: str = os.getenv("BANGUMI_API_URL", "https://api.bangumi.tv/v0")
    BILIBILI_API_URL: str = os.getenv("BILIBILI_API_URL", "https://api.bilibili.com/pgc/season")

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/anime_agent.log")

    # 缓存配置
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))

    # 服务配置
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    @classmethod
    def validate(cls) -> bool:
        """验证配置"""
        if not cls.ORCH_API_KEY:
            print("警告: ORCH_API_KEY 未设置")
            return False
        return True


# 配置实例
config = Config()
