"""配置管理 - 使用 pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置 - 使用 pydantic-settings 支持多环境"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ANIME_",
        extra="ignore"
    )
    
    # ========== MiniMax LLM 配置 ==========
    orch_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    orch_model: str = "MiniMax/MiniMax-M2.5"
    orch_api_key: str = ""
    
    # ========== 数据源配置 ==========
    bangumi_api_url: str = "https://api.bangumi.tv/v0"
    bilibili_api_url: str = "https://api.bilibili.com/pgc/season"
    jikan_api_url: str = "https://api.jikan.moe/v4"
    anilist_api_url: str = "https://graphql.anilist.co"
    
    # ========== Redis 配置 ==========
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  # 默认为 False，使用内存缓存
    
    # ========== 缓存配置 ==========
    cache_ttl: int = 3600  # 查询缓存 TTL（秒）
    session_ttl: int = 86400  # 会话缓存 TTL（24小时）
    
    # ========== 日志配置 ==========
    log_level: str = "INFO"
    log_file: str = "logs/anime_agent.log"
    
    # ========== 服务配置 ==========
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # ========== Agent 配置 ==========
    max_tool_retries: int = 2  # 工具调用最大重试次数
    tool_timeout: int = 3  # 工具调用超时时间（秒）
    max_conversation_turns: int = 10  # 最大对话轮次
    
    # ========== 验证方法 ==========
    def validate(self) -> bool:
        """验证配置"""
        if not self.orch_api_key:
            print("警告: ANIME_ORCH_API_KEY 未设置")
            return False
        return True
    
    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.log_level.upper() in ["WARNING", "ERROR", "CRITICAL"]


# 全局配置实例
settings = Settings()
