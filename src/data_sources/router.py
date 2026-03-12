# data_sources/router.py
"""数据源路由器"""

import asyncio
from typing import List
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class DataSourceRouter:
    """数据源路由器
    
    根据 platform 参数选择对应的数据源进行查询
    
    支持的平台:
    - "jikan": Jikan API (MyAnimeList 数据源)
    - "anilist": AniList API (全球动漫数据源)
    - "bangumi": Bangumi API (中文番剧数据)
    - "all": 同时查询 Jikan + AniList (默认)
    """
    
    # 平台名称到数据源名称的映射
    PLATFORM_MAP = {
        "jikan": ["Jikan"],
        "anilist": ["AniList"],
        "bangumi": ["Bangumi"],
        "all": ["Jikan", "AniList"],  # 默认查询 Jikan + AniList
    }
    
    # 平台别名（兼容旧版本）
    ALIAS_MAP = {
        "bilibili": "all",  # 旧的 bilibili 映射到 all
        "iqiyi": "all",
        "tencent": "all",
    }
    
    def __init__(self, sources: List[AnimeDataSource]):
        self.sources = sources
        # 创建名称到数据源的映射
        self.source_map = {source.NAME: source for source in sources}
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """查询数据源
        
        根据 platform 参数选择要查询的数据源
        """
        
        # 获取平台参数（处理别名）
        platform = params.platform or "all"
        # 转换别名
        platform = self.ALIAS_MAP.get(platform, platform)
        
        # 获取要查询的数据源列表
        source_names = self.PLATFORM_MAP.get(platform, self.PLATFORM_MAP["all"])
        
        # 过滤出需要查询的数据源
        sources_to_query = []
        for name in source_names:
            if name in self.source_map:
                sources_to_query.append(self.source_map[name])
        
        # 如果没有匹配的数据源，使用所有数据源
        if not sources_to_query:
            sources_to_query = self.sources
        
        # 并行查询所有选中的数据源
        async def fetch_with_timeout(source, timeout=10):
            try:
                return await asyncio.wait_for(source.search(params), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"[DataSourceRouter] {source.NAME} 查询超时")
                return []
            except Exception as e:
                print(f"[DataSourceRouter] {source.NAME} 查询失败: {e}")
                return []
        
        # 并行执行，带超时保护
        results = await asyncio.gather(
            *[fetch_with_timeout(s) for s in sources_to_query],
            return_exceptions=True
        )
        
        # 合并结果并去重
        return self._merge_results([r for r in results if isinstance(r, list)])
    
    def _merge_results(self, results: List[List[AnimeInfo]]) -> List[AnimeInfo]:
        """合并去重"""
        seen = set()
        merged = []
        for result_list in results:
            for anime in result_list:
                if anime.id not in seen:
                    seen.add(anime.id)
                    merged.append(anime)
        
        # 按评分排序
        return sorted(merged, key=lambda x: x.rating or 0, reverse=True)
