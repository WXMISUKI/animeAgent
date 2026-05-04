# data_sources/bangumi.py
"""Bangumi 数据源适配器

Bangumi 番组计划 API
文档: https://bangumi.github.io/api/
"""

import aiohttp
import json
import logging
from typing import Optional
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams

logger = logging.getLogger("BangumiAPI")


class BangumiAPI(AnimeDataSource):
    """Bangumi 数据源
    
    支持的查询：
    - 动画条目搜索
    - 章节、评分、类型等详细信息
    """
    
    BASE_URL = "https://api.bgm.tv/v0"
    NAME = "Bangumi"
    
    # 中文类型映射
    CHINESE_TYPE_MAP = {
        "剧场版": 2,   # 电影
        "电影": 2,
        "OVA": 3,     # OVA
        "TV": 1,      # TV
        "动画": 1,
        "特别篇": 4,
        "SP": 4,
        "音乐": 6,
        "网盘": 5      # ONA
    }
    
    def __init__(self):
        self._headers = {
            "User-Agent": "AnimeAgent/1.0",
            "Content-Type": "application/json"
        }
    
    def _parse_anime_type(self, anime_type: str) -> Optional[int]:
        """解析动画类型为 Bangumi type"""
        if not anime_type or anime_type == "all":
            return None
        return self.CHINESE_TYPE_MAP.get(anime_type)
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧
        
        Bangumi API:
        - type=1: TV
        - type=2: 电影
        - type=3: OVA
        - type=4: 特别篇
        - type=5: ONA
        - type=6: 音乐
        """
        
        logger.info(f"🔍 [BangumiAPI] search 开始, anime_type={params.anime_type}, keyword={params.keyword}, time_range={params.time_range}")
        
        # 解析动画类型
        anime_type = self._parse_anime_type(params.anime_type)
        
        # 关键词搜索
        if params.keyword:
            result = await self._search_by_keyword(params, anime_type)
        # 时间范围搜索
        elif params.time_range:
            result = await self._get_by_time_range(params, anime_type)
        # 默认获取近期热门
        else:
            result = await self._get_recent(anime_type)
        
        logger.info(f"✅ [BangumiAPI] search 完成, 返回 {len(result)} 条数据")
        return result
    
    async def _search_by_keyword(self, params: QueryParams, anime_type: int = None) -> list[AnimeInfo]:
        """通过关键词搜索
        
        Bangumi 搜索 API: https://api.bgm.tv/v0/search/subject
        """
        
        keyword = params.keyword
        
        logger.info(f"🔍 [BangumiAPI] _search_by_keyword 请求:")
        logger.info(f"   关键词: {keyword}")
        logger.info(f"   类型: {anime_type}")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/search/subject"
                
                query_params = {
                    "keyword": keyword,
                    "type": 2,  # 动画
                    "limit": 20
                }
                
                if anime_type:
                    query_params["type"] = anime_type
                
                logger.info(f"   URL: {url}")
                logger.info(f"   参数: {json.dumps(query_params)}")
                
                async with session.get(
                    url,
                    params=query_params,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    status = resp.status
                    data = await resp.json()
                    
                    logger.info(f"📥 [BangumiAPI] _search_by_keyword 响应:")
                    logger.info(f"   状态码: {status}")
                    logger.info(f"   响应内容: {json.dumps(data, ensure_ascii=False)[:1000]}")
                    
                    if status != 200:
                        logger.warning(f"❌ [BangumiAPI] HTTP错误: {status}")
                        return []
                    
                    items = data.get("data", []) or []
                    logger.info(f"📊 [BangumiAPI] 搜索到 {len(items)} 条数据")
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            logger.error(f"💥 [BangumiAPI] _search_by_keyword 异常: {str(e)}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return []
    
    async def _get_by_time_range(self, params: QueryParams, anime_type: int = None) -> list[AnimeInfo]:
        """按时间范围获取"""
        
        import re
        
        time_range = params.time_range
        if not time_range:
            return await self._get_recent(anime_type)
        
        # 解析时间范围 "2026-03" -> year=2026, month=3
        match = re.match(r"(\d{4})?-?(\d{1,2})?", time_range)
        if not match:
            return await self._get_recent(anime_type)
        
        year, month = match.groups()
        
        try:
            async with aiohttp.ClientSession() as session:
                # 使用 calendar 接口获取特定年份的动画
                if year:
                    url = f"{self.BASE_URL}/calendar"
                    async with session.get(
                        url,
                        headers=self._headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status != 200:
                            return []
                        
                        data = await resp.json()
                        
                        # 筛选指定月份的动画
                        items = []
                        for item in data:
                            if "items" in item:
                                for anime in item.get("items", []):
                                    items.append(anime)
                        
                        # 过滤类型
                        if anime_type:
                            items = [i for i in items if i.get("type") == anime_type]
                        
                        return [self._parse_anime(item) for item in items[:20]]
                else:
                    return await self._get_recent(anime_type)
                    
        except Exception as e:
            print(f"[BangumiAPI] 时间范围查询失败: {e}")
            return []
    
    async def _get_recent(self, anime_type: int = None) -> list[AnimeInfo]:
        """获取近期热门"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # 使用 rank 接口获取排行榜
                url = f"{self.BASE_URL}/subjects"
                
                params = {
                    "type": anime_type or 2,  # 默认动画
                    "limit": 20,
                    "sort": "rank"
                }
                
                async with session.get(
                    url,
                    params=params,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        print(f"[BangumiAPI] 获取热门失败: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    items = data.get("data", []) or []
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            print(f"[BangumiAPI] 获取近期热门失败: {e}")
            return []
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析 Bangumi 原始数据"""
        
        # 处理评分
        rating = raw.get("rating")
        if isinstance(rating, dict):
            rating = rating.get("score")
        
        # 处理图片
        cover_url = None
        images = raw.get("images")
        if isinstance(images, dict):
            cover_url = images.get("large") or images.get("common")
        
        # 处理简介
        summary = raw.get("summary", "")
        if summary and len(summary) > 200:
            summary = summary[:200] + "..."
        
        # 处理日期
        air_date = raw.get("air_date", "")
        
        return AnimeInfo(
            id=f"bgm_{raw.get('id', '')}",
            name=raw.get("name", ""),
            name_cn=raw.get("name_cn"),
            air_date=air_date,
            rating=rating,
            summary=summary,
            platform="Bangumi",
            source_url=f"https://bangumi.tv/subject/{raw.get('id', '')}",
            cover_url=cover_url
        )
    
    async def get_detail(self, anime_id: str) -> Optional[AnimeInfo]:
        """获取番剧详情"""
        
        bgm_id = anime_id.replace("bgm_", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/subjects/{bgm_id}",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    raw = await resp.json()
                    return self._parse_anime(raw)
                    
        except Exception as e:
            print(f"[BangumiAPI] 详情查询失败: {e}")
            return None
