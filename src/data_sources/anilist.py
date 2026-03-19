# data_sources/anilist.py
"""AniList API 数据源

AniList GraphQL API
文档: https://docs.anilist.co/
"""

import aiohttp
from typing import Optional, List
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class AniListAPI(AnimeDataSource):
    """AniList API 数据源"""
    
    BASE_URL = "https://graphql.anilist.co"
    NAME = "AniList"
    
    # 季节映射
    SEASON_MAP = {
        "01": "WINTER",
        "02": "WINTER",
        "03": "SPRING",
        "04": "SPRING",
        "05": "SPRING",
        "06": "SUMMER",
        "07": "SUMMER",
        "08": "SUMMER",
        "09": "FALL",
        "10": "FALL",
        "11": "FALL",
        "12": "WINTER"
    }
    
    # 中文类型映射到 AniList format
    CHINESE_TYPE_MAP = {
        "剧场版": "MOVIE",
        "电影": "MOVIE",
        "OVA": "OVA",
        "OAD": "OVA",
        "TV": "TV",
        "动画": "TV",
        "特别篇": "SPECIAL",
        "SP": "SPECIAL",
        "网盘": "ONA",
        "音乐": "MUSIC"
    }
    
    def _parse_anime_type(self, anime_type: str) -> Optional[str]:
        """解析动画类型"""
        if not anime_type or anime_type == "all":
            return None
        
        # 先尝试中文映射
        if anime_type in self.CHINESE_TYPE_MAP:
            return self.CHINESE_TYPE_MAP[anime_type]
        
        # 直接使用大写英文
        anime_type_upper = anime_type.upper()
        valid_formats = ["TV", "TV_SHORT", "OVA", "ONA", "MOVIE", "SPECIAL", "MUSIC"]
        if anime_type_upper in valid_formats:
            return anime_type_upper
        
        return None
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        # 解析动画类型
        anime_format = self._parse_anime_type(params.anime_type)
        
        # 关键词搜索
        if params.keyword:
            return await self._search_by_keyword(params, anime_format)
        
        # 时间范围搜索
        if params.time_range:
            return await self._get_season(params, anime_format)
        
        # 默认获取当前季节
        return await self._get_current_season(params, anime_format)
    
    async def _get_current_season(self, params: QueryParams, anime_format: str = None) -> list[AnimeInfo]:
        """获取当前季节番剧"""
        
        from datetime import datetime
        now = datetime.now()
        year = now.year
        season = self.SEASON_MAP[f"{now.month:02d}"]
        
        return await self._fetch_season(year, season, params.sort_by, anime_format)
    
    async def _get_season(self, params: QueryParams, anime_format: str = None) -> list[AnimeInfo]:
        """获取指定季节番剧"""
        
        import re
        
        time_range = params.time_range.strip()
        
        # 处理中文格式
        time_range = time_range.replace("年", "-").replace("月", "")
        
        # 匹配年份
        match = re.match(r"(\d{4})(?:-(\d{1,2}))?", time_range)
        if not match:
            return await self._get_current_season(params, anime_format)
        
        year = int(match.group(1))
        month = match.group(2)
        
        if month:
            season = self.SEASON_MAP[f"{int(month):02d}"]
        else:
            season = "WINTER"  # 默认冬季
        
        return await self._fetch_season(year, season, params.sort_by, anime_format)
    
    async def _fetch_season(self, year: int, season: str, sort_by: str = "rating", anime_format: str = None) -> list[AnimeInfo]:
        """获取指定年份和季节的番剧"""
        
        # 排序
        sort_field = "SCORE_DESC" if sort_by == "rating" else "POPULARITY_DESC"
        
        # 构建查询
        query = """
        query ($season: MediaSeason, $year: Int, $sort: [MediaSort], $format: MediaFormat) {
            Page(perPage: 20) {
                media(season: $season, seasonYear: $year, type: ANIME, sort: $sort, format: $format) {
                    id
                    title {
                        english
                        romaji
                        native
                    }
                    format
                    episodes
                    duration
                    status
                    season
                    seasonYear
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    averageScore
                    popularity
                    coverImage {
                        large
                        medium
                    }
                    description
                    siteUrl
                }
            }
        }
        """
        
        variables = {
            "season": season,
            "year": year,
            "sort": [sort_field],
            "format": anime_format
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    json={"query": query, "variables": variables},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        print(f"[AniListAPI] API 返回错误: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", {}).get("Page", {}).get("media", [])
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            print(f"[AniListAPI] 获取季度失败: {e}")
            return []
    
    async def _search_by_keyword(self, params: QueryParams, anime_format: str = None) -> list[AnimeInfo]:
        """通过关键词搜索"""
        
        keyword = params.keyword or ""
        
        query = """
        query ($search: String, $sort: [MediaSort], $format: MediaFormat) {
            Page(perPage: 20) {
                media(search: $search, type: ANIME, sort: $sort, format: $format) {
                    id
                    title {
                        english
                        romaji
                        native
                    }
                    format
                    episodes
                    duration
                    status
                    season
                    seasonYear
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    averageScore
                    popularity
                    coverImage {
                        large
                        medium
                    }
                    description
                    siteUrl
                }
            }
        }
        """
        
        sort_field = "SCORE_DESC" if params.sort_by == "rating" else "POPULARITY_DESC"
        
        variables = {
            "search": keyword,
            "sort": [sort_field],
            "format": anime_format
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    json={"query": query, "variables": variables},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        print(f"[AniListAPI] 搜索返回错误: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", {}).get("Page", {}).get("media", [])
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            print(f"[AniListAPI] 搜索失败: {e}")
            return []
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析 AniList 数据"""
        
        # 处理标题
        title = raw.get("title", {})
        english_name = title.get("english") or title.get("romaji") or ""
        native_name = title.get("native") or ""
        
        # 处理日期
        start_date = raw.get("startDate", {})
        air_date = ""
        if start_date.get("year"):
            air_date = f"{start_date.get('year')}-"
            if start_date.get("month"):
                air_date += f"{start_date.get('month'):02d}-"
                if start_date.get("day"):
                    air_date += f"{start_date.get('day'):02d}"
        
        # 处理简介
        summary = raw.get("description", "") or ""
        if summary and len(summary) > 200:
            summary = summary[:200] + "..."
        
        # 处理封面
        cover = raw.get("coverImage", {})
        cover_url = cover.get("large") or cover.get("medium")
        
        # 处理评分
        rating = raw.get("averageScore")
        if rating:
            rating = rating / 10  # AniList 评分是 0-100，转换为 0-10
        
        return AnimeInfo(
            id=f"anilist_{raw.get('id', '')}",
            name=english_name,
            name_cn=native_name,
            air_date=air_date,
            rating=rating,
            summary=summary,
            platform="AniList",
            source_url=raw.get("siteUrl", ""),
            cover_url=cover_url
        )
    
    async def get_detail(self, anime_id: str) -> Optional[AnimeInfo]:
        """获取番剧详情"""
        
        anilist_id = anime_id.replace("anilist_", "")
        
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                title {
                    english
                    romaji
                    native
                }
                episodes
                duration
                status
                season
                seasonYear
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                averageScore
                popularity
                coverImage {
                    large
                    medium
                }
                description
                siteUrl
                studios {
                    nodes {
                        name
                    }
                }
                genres
            }
        }
        """
        
        try:
            anilist_id = int(anilist_id)
        except ValueError:
            return None
        
        variables = {"id": anilist_id}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    json={"query": query, "variables": variables},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    raw = data.get("data", {}).get("Media")
                    
                    if raw:
                        return self._parse_anime(raw)
                    return None
                    
        except Exception as e:
            print(f"[AniListAPI] 获取详情失败: {e}")
            return None


# 快捷函数
async def get_current_season() -> list[AnimeInfo]:
    """获取当前季节番剧"""
    api = AniListAPI()
    return await api._get_current_season(QueryParams(sort_by="rating"))


async def search_anime(keyword: str) -> list[AnimeInfo]:
    """搜索番剧"""
    api = AniListAPI()
    params = QueryParams(keyword=keyword, sort_by="rating")
    return await api._search_by_keyword(params)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("测试 AniList API...")
        
        api = AniListAPI()
        
        # 测试搜索
        print("\n1. 搜索 'Frieren':")
        result = await api._search_by_keyword(QueryParams(keyword="Frieren", sort_by="rating"))
        print(f"   找到 {len(result)} 部番剧")
        for anime in result[:3]:
            print(f"   - {anime.name}: {anime.rating}分")
    
    asyncio.run(test())
