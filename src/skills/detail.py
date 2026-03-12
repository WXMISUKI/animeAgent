# skills/detail.py
"""番剧详情 Skill"""

from .base import BaseSkill, SkillInput, SkillOutput
from ..data_sources.jikan import JikanAPI
from ..data_sources.anilist import AniListAPI


class AnimeDetailSkill(BaseSkill):
    """番剧详情 Skill
    
    使用 Jikan API (MyAnimeList) + AniList API 获取数据
    """
    
    name = "detail"
    description = "查询番剧详情"
    
    def __init__(self):
        self.jikan = JikanAPI()
        self.anilist = AniListAPI()
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """执行详情查询"""
        try:
            params = input_data.get("query_params", {})
            anime_id = params.get("anime_id", "")
            
            if not anime_id:
                return self._create_error_output("缺少 anime_id 参数")
            
            # 根据 ID 前缀选择数据源
            if anime_id.startswith("jikan_"):
                result = await self.jikan.get_detail(anime_id)
            elif anime_id.startswith("anilist_"):
                result = await self.anilist.get_detail(anime_id)
            else:
                # 尝试 Jikan 数据源
                result = await self.jikan.get_detail(f"jikan_{anime_id}")
                if not result:
                    result = await self.anilist.get_detail(f"anilist_{anime_id}")
            
            if result:
                return self._create_success_output(
                    result.to_dict(),
                    {"skill": self.name, "source": result.platform}
                )
            else:
                return self._create_error_output("未找到番剧详情")
                
        except Exception as e:
            return self._create_error_output(str(e))
