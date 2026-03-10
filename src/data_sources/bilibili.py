# data_sources/bilibili.py
"""Bilibili 数据源适配器"""

import os
import aiohttp
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class BilibiliAPI(AnimeDataSource):
    """Bilibili 数据源"""
    
    BASE_URL = os.getenv("BILIBILI_API_URL", "https://api.bilibili.com/pgc/season")
    NAME = "Bilibili"
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        # Bilibili API 参数映射
        type_map = {
            "日漫": 1,
            "国漫": 2,
            "all": 0
        }
        
        query_params = {
            "fnval": 4048,  # 返回详细信息
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # 使用搜索接口
                search_url = f"{self.BASE_URL}/global/api/search"
                query_params["search_type"] = "media"
                query_params["keyword"] = params.keyword or params.time_range or "番剧"
                
                async with session.get(
                    search_url,
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    result = data.get("result", [])
                    items = result.get("media", []) if isinstance(result, dict) else []
                    
                    return [self._parse_anime(item) for item in items[:20]]
                    
        except Exception as e:
            print(f"[BilibiliAPI] 查询失败: {e}")
            return []
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析 Bilibili 原始数据"""
        
        # 处理评分
        rating = raw.get("score")
        if rating:
            rating = float(rating)
        
        # 处理封面
        cover = raw.get("cover")
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('id', '')}",
            name=raw.get("title", ""),
            name_cn=raw.get("title", ""),
            air_date=raw.get("pub_time", ""),
            rating=rating,
            summary=raw.get("desc", ""),
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('id', '')}/",
            cover_url=cover
        )
    
    async def get_detail(self, anime_id: str) -> AnimeInfo | None:
        """获取番剧详情"""
        
        bid = anime_id.replace("bilibili_", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/global/api/view",
                    params={"id": bid},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    raw = await resp.json()
                    return self._parse_anime(raw.get("result", {}))
                    
        except Exception as e:
            print(f"[BilibiliAPI] 详情查询失败: {e}")
            return None
