# tests/test_cache.py
"""缓存测试"""

import pytest
import time
from src.utils.cache import QueryCache


class TestQueryCache:
    """QueryCache 测试"""
    
    def test_set_and_get(self):
        """测试设置和获取缓存"""
        cache = QueryCache(ttl=60)
        
        cache.set("query1", {}, "result1")
        result = cache.get("query1", {})
        
        assert result == "result1"
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = QueryCache(ttl=60)
        
        result = cache.get("nonexistent", {})
        assert result is None
    
    def test_different_params(self):
        """测试不同参数生成不同缓存"""
        cache = QueryCache(ttl=60)
        
        cache.set("query1", {"page": 1}, "result1")
        cache.set("query1", {"page": 2}, "result2")
        
        assert cache.get("query1", {"page": 1}) == "result1"
        assert cache.get("query1", {"page": 2}) == "result2"
    
    def test_ttl_expired(self):
        """测试 TTL 过期"""
        cache = QueryCache(ttl=1)  # 1秒 TTL
        
        cache.set("query1", {}, "result1")
        time.sleep(1.1)
        
        result = cache.get("query1", {})
        assert result is None
    
    def test_clear(self):
        """测试清空缓存"""
        cache = QueryCache(ttl=60)
        
        cache.set("query1", {}, "result1")
        cache.set("query2", {}, "result2")
        
        assert cache.size() == 2
        
        cache.clear()
        
        assert cache.size() == 0
