# models/anime_info.py
"""番剧信息模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnimeInfo:
    """番剧信息"""
    
    id: str
    name: str
    name_cn: Optional[str] = None
    air_date: Optional[str] = None
    rating: Optional[float] = None
    summary: str = ""
    platform: str = ""
    source_url: str = ""
    cover_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.name_cn or self.name
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "名称": self.display_name,
            "原名": self.name,
            "播出时间": self.air_date,
            "评分": self.rating,
            "简介": self.summary[:100] + "..." if len(self.summary) > 100 else self.summary,
            "数据来源": self.platform,  # 数据来源平台
            "平台": self.platform,
            "链接": self.source_url,
            "封面": self.cover_url,
            "标签": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnimeInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_cn=data.get("name_cn"),
            air_date=data.get("air_date"),
            rating=data.get("rating"),
            summary=data.get("summary", ""),
            platform=data.get("platform", ""),
            source_url=data.get("source_url", ""),
            cover_url=data.get("cover_url"),
            tags=data.get("tags", [])
        )
