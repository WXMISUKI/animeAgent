# skills/base.py
"""Skill 基类"""

from abc import ABC, abstractmethod
from typing import TypedDict


class SkillInput(TypedDict):
    """Skill 输入"""
    query_params: dict
    context: dict


class SkillOutput(TypedDict):
    """Skill 输出"""
    success: bool
    data: list[dict] | dict | None
    error: str | None
    metadata: dict


class BaseSkill(ABC):
    """Skill 基类"""
    
    name: str = "base_skill"
    description: str = "基础技能"
    
    @abstractmethod
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """执行 Skill"""
        pass
    
    def can_handle(self, intent: dict) -> bool:
        """判断是否能处理该意图"""
        return intent.get("action") == self.name
    
    def _create_error_output(self, error: str) -> SkillOutput:
        """创建错误输出"""
        return {
            "success": False,
            "data": None,
            "error": error,
            "metadata": {"skill": self.name}
        }
    
    def _create_success_output(self, data, metadata: dict = None) -> SkillOutput:
        """创建成功输出"""
        return {
            "success": True,
            "data": data,
            "error": None,
            "metadata": metadata or {"skill": self.name}
        }
