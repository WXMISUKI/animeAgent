"""数据源集成测试

测试各个数据源的搜索功能，特别是国漫搜索
"""

import pytest
import asyncio
import logging
from src.data_sources.jikan import JikanAPI
from src.data_sources.anilist import AniListAPI
from src.data_sources.bangumi import BangumiAPI
from src.data_sources.bilibili import BilibiliAPI
from src.data_sources.router import DataSourceRouter
from src.models.query_params import QueryParams

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)


class TestJikanSearch:
    """Jikan 搜索测试"""
    
    @pytest.mark.asyncio
    async def test_search_keyword(self):
        """测试关键词搜索"""
        api = JikanAPI()
        params = QueryParams(keyword="Frieren", anime_type="all")
        
        results = await api.search(params)
        
        print(f"\n📊 Jikan 关键词搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_movie(self):
        """测试剧场版搜索"""
        api = JikanAPI()
        params = QueryParams(anime_type="剧场版", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 Jikan 剧场版搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
        
        assert len(results) > 0


class TestAniListSearch:
    """AniList 搜索测试"""
    
    @pytest.mark.asyncio
    async def test_search_keyword(self):
        """测试关键词搜索"""
        api = AniListAPI()
        params = QueryParams(keyword="Frieren", anime_type="all")
        
        results = await api.search(params)
        
        print(f"\n📊 AniList 关键词搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_movie(self):
        """测试剧场版搜索"""
        api = AniListAPI()
        params = QueryParams(anime_type="剧场版", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 AniList 剧场版搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
        
        assert len(results) > 0


class TestBangumiSearch:
    """Bangumi 搜索测试"""
    
    @pytest.mark.asyncio
    async def test_search_keyword(self):
        """测试关键词搜索"""
        api = BangumiAPI()
        params = QueryParams(keyword="Frieren", anime_type="all")
        
        results = await api.search(params)
        
        print(f"\n📊 Bangumi 关键词搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
    
    @pytest.mark.asyncio
    async def test_search_chinese_anime(self):
        """测试国漫搜索"""
        api = BangumiAPI()
        params = QueryParams(anime_type="国漫", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 Bangumi 国漫搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")


class TestBilibiliSearch:
    """Bilibili 搜索测试"""
    
    @pytest.mark.asyncio
    async def test_search_keyword(self):
        """测试关键词搜索"""
        api = BilibiliAPI()
        params = QueryParams(keyword="Frieren", anime_type="all")
        
        results = await api.search(params)
        
        print(f"\n📊 Bilibili 关键词搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
    
    @pytest.mark.asyncio
    async def test_search_chinese_anime_type(self):
        """测试国漫搜索（通过 anime_type 参数）"""
        api = BilibiliAPI()
        params = QueryParams(anime_type="国漫", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 Bilibili 国漫搜索结果 (anime_type='国漫'): {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
    
    @pytest.mark.asyncio
    async def test_search_chinese_anime_keyword(self):
        """测试国漫搜索（通过 keyword 参数）"""
        api = BilibiliAPI()
        params = QueryParams(keyword="国漫", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 Bilibili 国漫搜索结果 (keyword='国漫'): {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")
    
    @pytest.mark.asyncio
    async def test_search_movie(self):
        """测试剧场版搜索"""
        api = BilibiliAPI()
        params = QueryParams(anime_type="剧场版", sort_by="rating")
        
        results = await api.search(params)
        
        print(f"\n📊 Bilibili 剧场版搜索结果: {len(results)} 条")
        for r in results[:3]:
            print(f"   - {r.name} ({r.platform}) 评分: {r.rating}")


class TestDataSourceRouter:
    """数据源路由器测试"""
    
    @pytest.mark.asyncio
    async def test_search_all_sources(self):
        """测试全数据源搜索"""
        # 创建数据源
        sources = [
            JikanAPI(),
            AniListAPI(),
            BangumiAPI(),
            BilibiliAPI(),
        ]
        
        router = DataSourceRouter(sources)
        params = QueryParams(keyword="Frieren", sort_by="rating")
        
        results = await router.search(params)
        
        print(f"\n📊 全数据源搜索结果: {len(results)} 条")
        
        # 按平台分组
        by_platform = {}
        for r in results:
            platform = r.platform
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(r)
        
        for platform, items in by_platform.items():
            print(f"   {platform}: {len(items)} 条")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_chinese_anime(self):
        """测试国漫搜索"""
        sources = [
            JikanAPI(),
            AniListAPI(),
            BangumiAPI(),
            BilibiliAPI(),
        ]
        
        router = DataSourceRouter(sources)
        params = QueryParams(anime_type="国漫", sort_by="rating")
        
        results = await router.search(params)
        
        print(f"\n📊 国漫搜索结果: {len(results)} 条")
        
        # 按平台分组
        by_platform = {}
        for r in results:
            platform = r.platform
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(r)
        
        for platform, items in by_platform.items():
            print(f"   {platform}: {len(items)} 条")
            for item in items[:3]:
                print(f"      - {item.name} 评分: {item.rating}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
