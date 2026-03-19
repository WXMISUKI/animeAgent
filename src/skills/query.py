# skills/query.py
"""番剧查询 Skill"""

from .base import BaseSkill, SkillInput, SkillOutput
from ..data_sources.jikan import JikanAPI
from ..data_sources.anilist import AniListAPI
from ..data_sources.bangumi import BangumiAPI
from ..data_sources.bilibili import BilibiliAPI
from ..data_sources.router import DataSourceRouter
from ..models.query_params import QueryParams


class AnimeQuerySkill(BaseSkill):
    """番剧查询 Skill
    
    使用多数据源获取数据：
    - Jikan API: MyAnimeList 数据（主要查日漫）
    - AniList API: 全球动漫数据
    - Bangumi API: 中文番剧数据（国漫、日漫）
    - Bilibili API: B站数据（国漫、日漫）
    
    查询策略：并行查询所有数据源，合并结果后由大模型评价筛选
    """
    
    name = "query"
    description = "查询番剧列表"
    
    def __init__(self):
        # 初始化所有数据源
        self.data_sources = [
            JikanAPI(),     # Jikan API - MyAnimeList 数据
            AniListAPI(),  # AniList API - 全球数据
            BangumiAPI(),  # Bangumi API - 中文数据
            BilibiliAPI(), # Bilibili API - B站数据
        ]
        self.router = DataSourceRouter(self.data_sources)
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """执行查询"""
        try:
            params = input_data.get("query_params", {})
            
            # 构建 QueryParams
            query_params = QueryParams(
                time_range=params.get("time_range"),
                platform=params.get("platform", "all"),
                anime_type=params.get("anime_type", "all"),
                sort_by=params.get("sort_by", "latest"),
                keyword=params.get("keyword")
            )
            
            # 并行查询数据源
            results = await self.router.search(query_params)
            
            # 转换为字典
            data = [anime.to_dict() for anime in results]
            
            return self._create_success_output(
                data,
                {
                    "skill": self.name,
                    "count": len(data),
                    "sources": [s.NAME for s in self.data_sources]
                }
            )
            
        except Exception as e:
            return self._create_error_output(str(e))
