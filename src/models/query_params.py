# models/query_params.py
"""查询参数模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryParams:
    """查询参数"""
    
    time_range: Optional[str] = None   # "2026-03", "本周", "最新"
    platform: str = "all"              # bilibili/iqiyi/tencent/all
    anime_type: str = "all"            # 日漫/国漫/美漫/剧场版/all
    sort_by: str = "latest"            # latest/hot/rating
    keyword: Optional[str] = None        # 搜索关键词
    
    def to_dict(self) -> dict:
        return {
            "time_range": self.time_range,
            "platform": self.platform,
            "anime_type": self.anime_type,
            "sort_by": self.sort_by,
            "keyword": self.keyword
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QueryParams":
        return cls(
            time_range=data.get("time_range"),
            platform=data.get("platform", "all"),
            anime_type=data.get("anime_type", "all"),
            sort_by=data.get("sort_by", "latest"),
            keyword=data.get("keyword")
        )
