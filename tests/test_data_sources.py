"""数据源测试"""

import pytest
from src.data_sources.jikan import JikanAPI
from src.data_sources.router import DataSourceRouter
from src.models.query_params import QueryParams


class TestJikanAPI:
    """Jikan API 测试"""
    
    @pytest.mark.asyncio
    async def test_parse_time_range_winter(self):
        """测试冬季时间解析"""
        api = JikanAPI()
        
        # 测试 "2025-01" 格式
        year, season = api._parse_time_range("2025-01")
        assert year == 2025
        assert season == "winter"
    
    @pytest.mark.asyncio
    async def test_parse_time_range_summer(self):
        """测试夏季时间解析"""
        api = JikanAPI()
        
        # 测试 "2025夏" 格式
        year, season = api._parse_time_range("2025夏")
        assert year == 2025
        assert season == "summer"
    
    @pytest.mark.asyncio
    async def test_parse_time_range_year_only(self):
        """测试仅年份解析"""
        api = JikanAPI()
        
        # 测试 "2025" 格式
        year, season = api._parse_time_range("2025")
        assert year == 2025
        assert season == "winter"  # 默认冬季
    
    @pytest.mark.asyncio
    async def test_parse_time_range_chinese(self):
        """测试中文时间解析"""
        api = JikanAPI()
        
        # 测试 "2025年7月" 格式
        year, season = api._parse_time_range("2025年7月")
        assert year == 2025
        assert season == "summer"
    
    @pytest.mark.asyncio
    async def test_parse_anime(self):
        """测试番剧数据解析"""
        api = JikanAPI()
        
        raw_data = {
            "mal_id": 12345,
            "title_english": "Test Anime",
            "title_japanese": "テストアニメ",
            "score": 8.5,
            "synopsis": "A test anime description",
            "aired": {"string": "2024-04-01"},
            "type": "TV",
            "images": {"jpg": {"image_url": "https://example.com/image.jpg"}},
            "url": "https://myanimelist.net/anime/12345"
        }
        
        anime = api._parse_anime(raw_data)
        
        assert anime.id == "jikan_12345"
        assert anime.name == "Test Anime"
        assert anime.name_cn == "テストアニメ"
        assert anime.rating == 8.5
        assert anime.platform == "Jikan"


class TestDataSourceRouter:
    """数据源路由器测试"""
    
    def test_platform_map(self):
        """测试平台映射"""
        from src.data_sources.jikan import JikanAPI
        from src.data_sources.anilist import AniListAPI
        
        sources = [JikanAPI(), AniListAPI()]
        router = DataSourceRouter(sources)
        
        # 测试 jikan 平台
        assert "Jikan" in router.PLATFORM_MAP["jikan"]
        
        # 测试 all 平台
        assert "Jikan" in router.PLATFORM_MAP["all"]
        assert "AniList" in router.PLATFORM_MAP["all"]
    
    def test_alias_map(self):
        """测试平台别名"""
        from src.data_sources.jikan import JikanAPI
        
        sources = [JikanAPI()]
        router = DataSourceRouter(sources)
        
        # 测试 bilibili 别名
        assert router.ALIAS_MAP["bilibili"] == "all"


class TestQueryParams:
    """查询参数测试"""
    
    def test_default_params(self):
        """测试默认参数"""
        params = QueryParams()
        
        assert params.platform == "all"
        assert params.anime_type == "all"
        assert params.sort_by == "latest"  # 默认值是 latest
    
    def test_custom_params(self):
        """测试自定义参数"""
        params = QueryParams(
            platform="jikan",
            time_range="2025-01",
            keyword="Frieren"
        )
        
        assert params.platform == "jikan"
        assert params.time_range == "2025-01"
        assert params.keyword == "Frieren"
