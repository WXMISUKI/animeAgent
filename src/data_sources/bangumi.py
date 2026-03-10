# data_sources/bangumi.py
"""Bangumi 数据源适配器"""

import os
import aiohttp
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


# 模拟数据 - 用于测试
MOCK_ANIME_DATA = [
    {
        "id": "1",
        "name": "葬送のフリーレン",
        "name_cn": "葬送的芙莉莲",
        "air_date": "2026-03-01",
        "rating": 9.2,
        "summary": "勇者一行人解散后，魔法使芙莉莲独自继续旅行...",
        "images": {"large": "https://cdn.bgm.tv/subjectcover.jpg"}
    },
    {
        "id": "2", 
        "name": "SPY×FAMILY Season 3",
        "name_cn": "间谍过家家 第三季",
        "air_date": "2026-03-05",
        "rating": 8.8,
        "summary": "间谍黄昏伪装成精神科医生，组建临时家庭潜入名校...",
        "images": {"large": "https://cdn.bgm.tv/subjectcover.jpg"}
    },
    {
        "id": "3",
        "name": "ブルーロック",
        "name_cn": "蓝色监狱",
        "air_date": "2026-03-10",
        "rating": 8.5,
        "summary": "日本国家足球场选拔最自私的前锋...",
        "images": {"large": "https://cdn.bgm.tv/subjectcover.jpg"}
    },
    {
        "id": "4",
        "name": "ダンダリン",
        "name_cn": "断断续续",
        "air_date": "2026-03-15",
        "rating": 8.3,
        "summary": "职场劳动漫画改编...",
        "images": {"large": "https://cdn.bgm.tv/subjectcover.jpg"}
    },
    {
        "id": "5",
        "name": "ホロライブ",
        "name_cn": "Hololive 第二季",
        "air_date": "2026-03-20",
        "rating": 8.7,
        "summary": "VTuber 们的日常...",
        "images": {"large": "https://cdn.bgm.tv/subjectcover.jpg"}
    }
]


class BangumiAPI(AnimeDataSource):
    """Bangumi 数据源"""
    
    BASE_URL = os.getenv("BANGUMI_API_URL", "https://api.bangumi.tv/v0")
    NAME = "Bangumi"
    USE_MOCK = True  # 默认使用模拟数据
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        # 如果启用模拟数据，返回模拟数据
        if self.USE_MOCK:
            return self._get_mock_data(params)
        
        query_params = {
            "type": 2,  # 动画
        }
        
        # 添加时间过滤
        if params.time_range:
            query_params["air_date"] = params.time_range
        
        # 添加排序
        sort_map = {
            "latest": "air_date",
            "hot": "rank",
            "rating": "rating"
        }
        query_params["sort"] = sort_map.get(params.sort_by, "air_date")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/subjects/filter",
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return self._get_mock_data(params)
                    
                    data = await resp.json()
                    items = data.get("data", [])
                    
                    return [self._parse_anime(item) for item in items[:20]]
                    
        except Exception as e:
            print(f"[BangumiAPI] 查询失败: {e}")
            # 失败时返回模拟数据
            return self._get_mock_data(params)
    
    def _get_mock_data(self, params: QueryParams) -> list[AnimeInfo]:
        """获取模拟数据"""
        results = []
        for item in MOCK_ANIME_DATA:
            anime = self._parse_anime(item)
            # 根据参数过滤
            if params.anime_type == "日漫" or params.anime_type == "all":
                results.append(anime)
            elif params.anime_type == "国漫":
                # 国漫返回空
                pass
        return results
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析 Bangumi 原始数据"""
        
        return AnimeInfo(
            id=f"bgm_{raw.get('id', '')}",
            name=raw.get("name", ""),
            name_cn=raw.get("name_cn"),
            air_date=raw.get("air_date"),
            rating=raw.get("rating", {}).get("score") if isinstance(raw.get("rating"), dict) else None,
            summary=raw.get("summary", ""),
            platform="Bangumi",
            source_url=f"https://bangumi.tv/subject/{raw.get('id', '')}",
            cover_url=raw.get("images", {}).get("large") if isinstance(raw.get("images"), dict) else None
        )
    
    async def get_detail(self, anime_id: str) -> AnimeInfo | None:
        """获取番剧详情"""
        
        bgm_id = anime_id.replace("bgm_", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/subjects/{bgm_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    raw = await resp.json()
                    return self._parse_anime(raw)
                    
        except Exception as e:
            print(f"[BangumiAPI] 详情查询失败: {e}")
            return None
