"""Redis 缓存实现"""

import json
import logging
from typing import Optional, Any
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存 - 支持查询缓存和会话存储"""
    
    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379/0",
        enabled: bool = False
    ):
        self.enabled = enabled and REDIS_AVAILABLE
        self.redis_url = redis_url
        self._client = None
        
        if self.enabled:
            try:
                self._client = redis.from_url(redis_url, decode_responses=True)
                # 测试连接
                self._client.ping()
                logger.info(f"Redis 缓存已启用: {redis_url}")
            except Exception as e:
                logger.warning(f"Redis 连接失败，降级为内存缓存: {e}")
                self.enabled = False
                self._client = None
    
    @property
    def client(self):
        """获取 Redis 客户端"""
        return self._client
    
    def _make_key(self, prefix: str, *args) -> str:
        """生成缓存 key"""
        key_data = ":".join(str(arg) for arg in args if arg)
        return f"anime_agent:{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    # ========== 查询缓存 ==========
    
    def get_query_cache(self, query: str, params: dict = None) -> Optional[str]:
        """获取查询缓存"""
        if not self.enabled:
            return None
        
        try:
            key = self._make_key("query", query, json.dumps(params or {}, sort_keys=True))
            return self._client.get(key)
        except Exception as e:
            logger.warning(f"查询缓存获取失败: {e}")
            return None
    
    def set_query_cache(
        self, 
        query: str, 
        value: str, 
        params: dict = None, 
        ttl: int = 3600
    ):
        """设置查询缓存"""
        if not self.enabled:
            return
        
        try:
            key = self._make_key("query", query, json.dumps(params or {}, sort_keys=True))
            self._client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"查询缓存设置失败: {e}")
    
    def clear_query_cache(self):
        """清空查询缓存"""
        if not self.enabled:
            return
        
        try:
            for key in self._client.scan_iter("anime_agent:query:*"):
                self._client.delete(key)
        except Exception as e:
            logger.warning(f"清空查询缓存失败: {e}")
    
    # ========== 会话存储 ==========
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话数据"""
        if not self.enabled:
            return None
        
        try:
            key = self._make_key("session", session_id)
            data = self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"会话获取失败: {e}")
            return None
    
    def set_session(
        self, 
        session_id: str, 
        context: dict, 
        ttl: int = 86400
    ):
        """设置会话数据"""
        if not self.enabled:
            return
        
        try:
            key = self._make_key("session", session_id)
            self._client.setex(key, ttl, json.dumps(context, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"会话设置失败: {e}")
    
    def delete_session(self, session_id: str):
        """删除会话"""
        if not self.enabled:
            return
        
        try:
            key = self._make_key("session", session_id)
            self._client.delete(key)
        except Exception as e:
            logger.warning(f"会话删除失败: {e}")
    
    # ========== 通用操作 ==========
    
    def get(self, key: str) -> Optional[str]:
        """通用获取"""
        if not self.enabled:
            return None
        
        try:
            return self._client.get(f"anime_agent:{key}")
        except Exception as e:
            logger.warning(f"缓存获取失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """通用设置"""
        if not self.enabled:
            return
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            self._client.setex(f"anime_agent:{key}", ttl, value)
        except Exception as e:
            logger.warning(f"缓存设置失败: {e}")
    
    def delete(self, key: str):
        """通用删除"""
        if not self.enabled:
            return
        
        try:
            self._client.delete(f"anime_agent:{key}")
        except Exception as e:
            logger.warning(f"缓存删除失败: {e}")
    
    def ping(self) -> bool:
        """检查 Redis 连接"""
        if not self.enabled:
            return False
        
        try:
            return self._client.ping()
        except Exception:
            return False


# 全局缓存实例（延迟初始化）
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """获取全局 Redis 缓存实例"""
    global _redis_cache
    if _redis_cache is None:
        from ..core.config import settings
        _redis_cache = RedisCache(
            redis_url=settings.redis_url,
            enabled=settings.redis_enabled
        )
    return _redis_cache
