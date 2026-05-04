"""Redis 版 Checkpointer - 用于生产环境

使用 langgraph-checkpoint-postgres 的异步版本，
通过 Redis 作为存储后端（需要先安装依赖）

注意：需要安装 langgraph-checkpoint-redis
pip install langgraph-checkpoint-redis
"""

import logging
from typing import Optional, Any
from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)

# 尝试导入 Redis Checkpointer
REDIS_CHECKPOINTER_AVAILABLE = False
RedisSaver = None

try:
    from langgraph.checkpoint.redis import RedisSaver
    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    logger.warning("langgraph-checkpoint-redis 未安装，将使用内存版 Checkpointer")
    RedisSaver = None


class RedisCheckpointer:
    """Redis 版 Checkpointer 封装类
    
    适用于生产环境，支持：
    - 多实例共享状态
    - 持久化存储
    - 大规模应用
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "langgraph:",
        ttl: Optional[int] = 86400  # 默认 24 小时
    ):
        """
        Args:
            redis_url: Redis 连接地址
            key_prefix: 键前缀
            ttl: 过期时间（秒）
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._saver: Optional[BaseCheckpointSaver] = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            if not REDIS_CHECKPOINTER_AVAILABLE or RedisSaver is None:
                raise RuntimeError(
                    "Redis Checkpointer 不可用，请安装: pip install langgraph-checkpoint-redis"
                )
            
            self._saver = RedisSaver.from_url(
                self.redis_url,
                key_prefix=self.key_prefix
            )
            self._initialized = True
            logger.info(f"✅ RedisCheckpointer 初始化完成: {self.redis_url}")
    
    @property
    def saver(self) -> BaseCheckpointSaver:
        """获取 LangGraph 兼容的 Saver"""
        self._ensure_initialized()
        return self._saver
    
    def get_checkpointer(self) -> BaseCheckpointSaver:
        """获取 Checkpointer（兼容旧接口）"""
        return self.saver


# 全局实例
_redis_checkpointer: Optional[RedisCheckpointer] = None


def get_redis_checkpointer(
    redis_url: str = None,
    key_prefix: str = "langgraph:",
    ttl: int = 86400
) -> RedisCheckpointer:
    """获取全局 RedisCheckpointer 实例
    
    Args:
        redis_url: Redis 连接地址
        key_prefix: 键前缀
        ttl: 过期时间
    """
    global _redis_checkpointer
    if _redis_checkpointer is None:
        from ...core.config import settings
        _redis_checkpointer = RedisCheckpointer(
            redis_url=redis_url or settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379",
            key_prefix=key_prefix,
            ttl=ttl
        )
    return _redis_checkpointer
