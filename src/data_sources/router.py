# data_sources/router.py
"""数据源路由器"""

import asyncio
from typing import List
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class DataSourceRouter:
    """数据源路由器"""
    
    def __init__(self, sources: List[AnimeDataSource]):
        self.sources = sources
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """并行查询所有数据源"""
        
        async def fetch_with_timeout(source, timeout=5):
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
            *[fetch_with_timeout(s) for s in self.sources],
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
