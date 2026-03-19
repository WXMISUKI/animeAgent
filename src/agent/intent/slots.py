"""槽位定义 - 用于参数校验和反问"""

import re
from typing import Dict, Any, List, Optional


class SlotDefinition:
    """槽位定义 - 用于参数校验和反问"""
    
    # 槽位定义字典
    DEFINITIONS = {
        "time_range": {
            "type": "string",
            "required": False,
            "description": "时间范围",
            "examples": ["2026-03", "本月", "最新", "2026春", "2024年7月"],
            "validate": lambda x: _validate_time_range(x) if x else True
        },
        "platform": {
            "type": "string",
            "required": False,
            "description": "平台",
            "enum": ["jikan", "anilist", "bangumi", "bilibili", "all"],
            "default": "all"
        },
        "anime_type": {
            "type": "string",
            "required": False,
            "description": "番剧类型",
            "enum": ["日漫", "国漫", "美漫", "剧场版", "OVA", "all"],
            "default": "all"
        },
        "sort_by": {
            "type": "string",
            "required": False,
            "description": "排序方式",
            "enum": ["latest", "hot", "rating"],
            "default": "rating"
        },
        "keyword": {
            "type": "string",
            "required": False,
            "description": "关键词搜索"
        },
        "anime_id": {
            "type": "string",
            "required": False,
            "description": "番剧ID"
        }
    }
    
    # 意图必需的槽位
    REQUIRED_SLOTS = {
        "detail": ["keyword", "anime_id"],  # 详情需要关键词或ID
        "query": [],  # 查询可选
        "ranking": [],  # 排行榜可选
    }
    
    # 番剧类型关键词映射
    ANIME_TYPE_KEYWORDS = {
        "国漫": ["国漫", "国产", "国创", "中国动画", "国产动漫", "国产番", "国动"],
        "日漫": ["日漫", "日本动画", "日本动漫", "日本番", "日番", "日本动画"],
        "剧场版": ["剧场版", "电影版", "动画电影", "动漫电影", "电影"],
        "OVA": ["OVA", "OAD", "OVA动画"]
    }
    
    # 排序方式关键词映射
    SORT_BY_KEYWORDS = {
        "hot": ["最热", "热门", "火", "热度", "最火", "人气", "火爆"],
        "latest": ["最新", "新番", "刚出", "上新", "最近"],
        "rating": ["评分", "高分", "推荐", "评分高", "口碑好", "评价好"]
    }
    
    # 时间范围关键词映射
    TIME_KEYWORDS = {
        "本月": ["本月", "这个月", "当月"],
        "最新": ["最新", "最近", "新番", "刚出"],
        "春": ["春季", "春番", "春天", "春"],
        "夏": ["夏季", "夏番", "夏天", "夏"],
        "秋": ["秋季", "秋番", "秋天", "秋"],
        "冬": ["冬季", "冬番", "冬天", "冬"]
    }
    
    @classmethod
    def get_required_slots(cls, intent: str) -> List[str]:
        """获取意图必需的槽位"""
        return cls.REQUIRED_SLOTS.get(intent, [])
    
    @classmethod
    def get_enum_values(cls, slot_name: str) -> List[str]:
        """获取槽位的枚举值"""
        slot_def = cls.DEFINITIONS.get(slot_name)
        if slot_def and "enum" in slot_def:
            return slot_def["enum"]
        return []
    
    @classmethod
    def get_default_value(cls, slot_name: str) -> Any:
        """获取槽位的默认值"""
        slot_def = cls.DEFINITIONS.get(slot_name)
        if slot_def and "default" in slot_def:
            return slot_def["default"]
        return None


def _validate_time_range(value: str) -> bool:
    """验证时间范围格式"""
    # 简单验证：年份+月份、季节、本月、最新等
    patterns = [
        r"^\d{4}-\d{2}$",  # 2026-03
        r"^\d{4}年\d{1,2}月$",  # 2026年3月
        r"^\d{4}春|夏|秋|冬$",  # 2026春
        r"^本月$",
        r"^最新$",
        r"^最近$"
    ]
    return any(re.match(p, value) for p in patterns)
