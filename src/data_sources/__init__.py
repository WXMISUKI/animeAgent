# data_sources/__init__.py
"""数据源模块

提供多种番剧数据源:
- Jikan API: 基于 MyAnimeList 的全球动漫数据库
- AniList API: 全球动漫数据源
- Bangumi API: 中文番剧社区数据
- Baidu Search: 百度搜索（降级方案）

Example:
    >>> from src.data_sources import JikanAPI, AniListAPI
    >>> from src.data_sources.router import DataSourceRouter
    >>> 
    >>> sources = [JikanAPI(), AniListAPI()]
    >>> router = DataSourceRouter(sources)
"""

from .base import AnimeDataSource
from .jikan import JikanAPI
from .anilist import AniListAPI
from .bangumi import BangumiAPI
from .router import DataSourceRouter

__all__ = [
    "AnimeDataSource",
    "JikanAPI",
    "AniListAPI", 
    "BangumiAPI",
    "DataSourceRouter"
]
