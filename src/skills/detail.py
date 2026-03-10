# skills/detail.py
"""番剧详情 Skill"""

from .base import BaseSkill, SkillInput, SkillOutput
from ..data_sources.bangumi import BangumiAPI
from ..data_sources.bilibili import BilibiliAPI


class AnimeDetailSkill(BaseSkill):
    """番剧详情 Skill"""
    
    name = "detail"
    description = "查询番剧详情"
    
    def __init__(self):
        self.bangumi = BangumiAPI()
        self.bilibili = BilibiliAPI()
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """执行详情查询"""
        try:
            params = input_data.get("query_params", {})
            anime_id = params.get("anime_id", "")
            
            if not anime_id:
                return self._create_error_output("缺少 anime_id 参数")
            
            # 优先从 Bilibili 获取
            if anime_id.startswith("bilibili_"):
                result = await self.bilibili.get_detail(anime_id)
            elif anime_id.startswith("bgm_"):
                result = await self.bangumi.get_detail(anime_id)
            else:
                # 尝试两个数据源
                result = await self.bilibili.get_detail(f"bilibili_{anime_id}")
                if not result:
                    result = await self.bangumi.get_detail(f"bgm_{anime_id}")
            
            if result:
                return self._create_success_output(
                    result.to_dict(),
                    {"skill": self.name, "source": result.platform}
                )
            else:
                return self._create_error_output("未找到番剧详情")
                
        except Exception as e:
            return self._create_error_output(str(e))
