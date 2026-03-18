# skills/__init__.py
"""Skills 模块

提供多种技能:
- AnimeQuerySkill: 番剧查询技能
- AnimeDetailSkill: 番剧详情查询技能
- RankingSkill: 番剧排行榜技能

Example:
    >>> from src.skills import AnimeQuerySkill
    >>> skill = AnimeQuerySkill()
    >>> result = await skill.execute({"query_params": {}, "context": {}})
"""

from .base import BaseSkill, SkillInput, SkillOutput
from .query import AnimeQuerySkill
from .detail import AnimeDetailSkill
from .ranking import RankingSkill

__all__ = [
    "BaseSkill",
    "SkillInput", 
    "SkillOutput",
    "AnimeQuerySkill",
    "AnimeDetailSkill",
    "RankingSkill"
]
