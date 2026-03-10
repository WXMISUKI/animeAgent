# tests/test_models.py
"""数据模型测试"""

import pytest
from src.models.query_params import QueryParams
from src.models.anime_info import AnimeInfo


class TestQueryParams:
    """QueryParams 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        params = QueryParams()
        assert params.platform == "all"
        assert params.anime_type == "all"
        assert params.sort_by == "latest"
    
    def test_to_dict(self):
        """测试转换为字典"""
        params = QueryParams(
            time_range="2026-03",
            platform="bilibili",
            anime_type="日漫",
            sort_by="rating"
        )
        
        result = params.to_dict()
        assert result["time_range"] == "2026-03"
        assert result["platform"] == "bilibili"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "time_range": "2026-03",
            "platform": "bilibili",
            "anime_type": "日漫",
            "sort_by": "rating",
            "keyword": "test"
        }
        
        params = QueryParams.from_dict(data)
        assert params.time_range == "2026-03"
        assert params.platform == "bilibili"


class TestAnimeInfo:
    """AnimeInfo 测试"""
    
    def test_display_name(self):
        """测试显示名称"""
        anime = AnimeInfo(
            id="1",
            name="Frieren",
            name_cn="葬送的芙莉莲"
        )
        assert anime.display_name == "葬送的芙莉莲"
    
    def test_display_name_no_cn(self):
        """测试无中文名时显示原名"""
        anime = AnimeInfo(
            id="1",
            name="Frieren"
        )
        assert anime.display_name == "Frieren"
    
    def test_to_dict(self):
        """测试转换为字典"""
        anime = AnimeInfo(
            id="1",
            name="Frieren",
            name_cn="葬送的芙莉莲",
            rating=9.2,
            platform="Bilibili"
        )
        
        result = anime.to_dict()
        assert result["名称"] == "葬送的芙莉莲"
        assert result["评分"] == 9.2
        assert result["平台"] == "Bilibili"
