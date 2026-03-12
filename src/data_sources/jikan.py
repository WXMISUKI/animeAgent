# data_sources/jikan.py
"""Jikan API 数据源适配器

Jikan (時間) 是一个免费的非官方 MyAnimeList API
文档: https://docs.api.jikan.moe/
"""

import aiohttp
from typing import Optional
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class JikanAPI(AnimeDataSource):
    """Jikan API 数据源 - 基于 MyAnimeList"""
    
    BASE_URL = "https://api.jikan.moe/v4"
    NAME = "Jikan"
    
    # 季度映射
    SEASON_MAP = {
        "01": "winter",
        "02": "winter", 
        "03": "spring",
        "04": "spring",
        "05": "spring",
        "06": "summer",
        "07": "summer",
        "08": "summer",
        "09": "fall",
        "10": "fall",
        "11": "fall",
        "12": "winter"
    }
    
    # 动画类型映射
    TYPE_MAP = {
        "tv": 1,
        "ova": 2,
        "movie": 3,
        "special": 4,
        "ona": 5,
        "music": 6,
        "all": None
    }
    
    # 评分排序
    SORT_MAP = {
        "rating": "score",
        "hot": "popularity",
        "latest": "start_date"
    }
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧
        
        根据参数选择合适的 API 端点:
        - 有时间范围 -> /seasons/{year}/{season}
        - 无时间范围 -> /seasons/now
        - 有关键词 -> /anime?q={keyword}
        """
        
        # 优先处理关键词搜索
        if params.keyword:
            return await self._search_by_keyword(params)
        
        # 根据时间范围获取季度数据
        if params.time_range:
            return await self._get_season(params)
        
        # 默认获取当前季度
        return await self._get_current_season(params)
    
    async def _get_current_season(self, params: QueryParams) -> list[AnimeInfo]:
        """获取当前季度番剧"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # 获取当前季度
                async with session.get(
                    f"{self.BASE_URL}/seasons/now",
                    params={"limit": 25},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        print(f"[JikanAPI] API 返回错误: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", [])
                    
                    # 过滤动画
                    items = [item for item in items if item.get("type") == "TV"]
                    
                    # 应用排序
                    items = self._sort_results(items, params.sort_by)
                    
                    return [self._parse_anime(item) for item in items[:20]]
                    
        except Exception as e:
            print(f"[JikanAPI] 获取当前季度失败: {e}")
            return []
    
    async def _get_season(self, params: QueryParams) -> list[AnimeInfo]:
        """获取指定年份/季度的番剧"""
        
        # 解析时间范围
        year, season = self._parse_time_range(params.time_range)
        
        if not year:
            # 无法解析，返回当前季度
            return await self._get_current_season(params)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/seasons/{year}/{season}"
                
                async with session.get(
                    url,
                    params={"limit": 25},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        print(f"[JikanAPI] API 返回错误: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", [])
                    
                    # 应用排序
                    items = self._sort_results(items, params.sort_by)
                    
                    return [self._parse_anime(item) for item in items[:20]]
                    
        except Exception as e:
            print(f"[JikanAPI] 获取季度失败: {e}")
            return []
    
    async def _search_by_keyword(self, params: QueryParams) -> list[AnimeInfo]:
        """通过关键词搜索番剧"""
        
        keyword = params.keyword or params.time_range or "anime"
        
        try:
            async with aiohttp.ClientSession() as session:
                query_params = {
                    "q": keyword,
                    "limit": 20,
                    "type": "tv"
                }
                
                async with session.get(
                    f"{self.BASE_URL}/anime",
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", [])
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            print(f"[JikanAPI] 关键词搜索失败: {e}")
            return []
    
    def _parse_time_range(self, time_range: str) -> tuple[Optional[int], Optional[str]]:
        """解析时间范围为年份和季度
        
        Args:
            time_range: 时间范围字符串，支持：
            - "2025-01" / "2025年1月" → 2025年冬季
            - "2025夏" / "2025夏季" → 2025年夏季
            - "2025" → 2025年（默认返回冬季）
            - "本月" / "最新" → 当前季度
            
        Returns:
            (year, season) 元组
        """
        
        import re
        
        if not time_range:
            return None, None
            
        time_range = time_range.strip().lower()
        
        # 处理中文格式：2025年1月 → 2025-01
        time_range = time_range.replace("年", "-").replace("月", "").replace(" ", "")
        
        # 处理季节关键词
        season_keywords = {
            "春": "spring",
            "夏": "summer", 
            "秋": "fall",
            "冬": "winter"
        }
        
        for kw, season in season_keywords.items():
            if kw in time_range:
                # 匹配 "2025夏" / "2025夏季" / "2025年春" 等
                match = re.match(r"(\d{4})", time_range)
                if match:
                    return int(match.group(1)), season
        
        # 匹配 YYYY-MM 或 YYYY 格式
        match = re.match(r"(\d{4})(?:-(\d{1,2}))?", time_range)
        if match:
            year = int(match.group(1))
            month = match.group(2)
            
            if month:
                month = int(month)
                season = self.SEASON_MAP.get(f"{month:02d}", "winter")
            else:
                # 只有年份，默认返回冬季（1月）
                season = "winter"
            
            return year, season
        
        # 处理"本月"、"最新"等关键词
        from datetime import datetime
        now = datetime.now()
        
        if "本月" in time_range or "当前" in time_range:
            return None, None
        
        if "最新" in time_range or "最近" in time_range:
            return now.year, self.SEASON_MAP[f"{now.month:02d}"]
        
        # 无法解析，返回当前季度
        return None, None
    
    def _sort_results(self, items: list, sort_by: str) -> list:
        """排序结果"""
        
        if not items:
            return items
        
        sort_key = self.SORT_MAP.get(sort_by, "score")
        
        if sort_by == "rating":
            # 评分从高到低
            return sorted(items, key=lambda x: x.get("score", 0) or 0, reverse=True)
        elif sort_by == "hot":
            # 热门（popularity 越低越热门）
            return sorted(items, key=lambda x: x.get("popularity", 999999) or 999999)
        else:
            # 最新
            return sorted(items, key=lambda x: x.get("aired", {}).get("string", ""), reverse=True)
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析 Jikan 原始数据为 AnimeInfo"""
        
        # 处理 ID
        anime_id = str(raw.get("mal_id", ""))
        
        # 处理标题
        title = raw.get("title_english") or raw.get("title", "")
        title_cn = raw.get("title_japanese", "")
        
        # 处理评分
        rating = raw.get("score")
        
        # 处理简介
        summary = raw.get("synopsis", "") or ""
        if summary and len(summary) > 200:
            summary = summary[:200] + "..."
        
        # 处理日期
        air_date = ""
        aired = raw.get("aired", {})
        if isinstance(aired, dict):
            air_date = aired.get("string", "")
        
        # 处理封面
        cover_url = None
        images = raw.get("images", {})
        if isinstance(images, dict):
            jpg = images.get("jpg", {})
            if isinstance(jpg, dict):
                cover_url = jpg.get("image_url") or jpg.get("large_image_url")
        
        # 处理链接
        source_url = raw.get("url", "")
        
        # 处理番剧类型
        anime_type = raw.get("type", "TV")
        
        return AnimeInfo(
            id=f"jikan_{anime_id}",
            name=title,
            name_cn=title_cn,
            air_date=air_date,
            rating=rating,
            summary=summary,
            platform="Jikan",
            source_url=source_url,
            cover_url=cover_url
        )
    
    async def get_detail(self, anime_id: str) -> Optional[AnimeInfo]:
        """获取番剧详情"""
        
        jikan_id = anime_id.replace("jikan_", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/anime/{jikan_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    raw = data.get("data", {})
                    
                    return self._parse_anime(raw)
                    
        except Exception as e:
            print(f"[JikanAPI] 获取详情失败: {e}")
            return None


# 快捷函数
async def get_current_season() -> list[AnimeInfo]:
    """获取当前季度番剧"""
    api = JikanAPI()
    params = QueryParams(anime_type="all", sort_by="rating")
    return await api._get_current_season(params)


async def get_season(year: int, season: str) -> list[AnimeInfo]:
    """获取指定年份/季度的番剧
    
    Args:
        year: 年份，如 2025
        season: 季度，如 winter, spring, summer, fall
    """
    api = JikanAPI()
    params = QueryParams(anime_type="all", sort_by="rating")
    return await api._get_season(params)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("测试 Jikan API...")
        
        # 测试获取当前季度
        print("\n1. 获取当前季度番剧:")
        api = JikanAPI()
        result = await api._get_current_season(QueryParams(sort_by="rating"))
        print(f"   找到 {len(result)} 部番剧")
        for anime in result[:3]:
            print(f"   - {anime.name}: {anime.rating}分")
        
        # 测试获取指定季度
        print("\n2. 获取 2025 年冬季番剧:")
        result = await api._get_season(QueryParams(time_range="2025-01", sort_by="rating"))
        print(f"   找到 {len(result)} 部番剧")
        for anime in result[:3]:
            print(f"   - {anime.name}: {anime.rating}分")
        
        # 测试搜索
        print("\n3. 搜索 'Frieren':")
        result = await api._search_by_keyword(QueryParams(keyword="Frieren"))
        print(f"   找到 {len(result)} 部番剧")
        for anime in result[:3]:
            print(f"   - {anime.name}: {anime.rating}分")
    
    asyncio.run(test())
