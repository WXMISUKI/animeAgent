# utils/cache.py
"""缓存工具"""

import hashlib
import json
import time
from typing import Optional


class QueryCache:
    """查询结果缓存"""
    
    def __init__(self, ttl: int = 3600):
        self._cache = {}
        self._ttl = ttl
    
    def _make_key(self, query: str, params: dict) -> str:
        """生成缓存 key"""
        data = json.dumps({"query": query, "params": params}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, query: str, params: dict) -> Optional[str]:
        """获取缓存"""
        key = self._make_key(query, params)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return result
            else:
                del self._cache[key]
        return None
    
    def set(self, query: str, params: dict, value: str):
        """设置缓存"""
        key = self._make_key(query, params)
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def size(self) -> int:
        """返回缓存大小"""
        return len(self._cache)
