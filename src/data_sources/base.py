# data_sources/base.py
"""数据源基类"""

from abc import ABC, abstractmethod
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class AnimeDataSource(ABC):
    """番剧数据源抽象接口"""
    
    NAME = "base"
    
    @abstractmethod
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        pass
    
    @abstractmethod
    async def get_detail(self, anime_id: str) -> AnimeInfo | None:
        """获取番剧详情"""
        pass
