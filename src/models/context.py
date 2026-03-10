# models/context.py
"""会话上下文模型"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Context:
    """会话上下文"""
    
    user_id: str
    conversation_history: list[dict] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)
    last_query_results: list = field(default_factory=list)
    
    def add_query_history(self, params: dict, results: list):
        """添加查询历史"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "params": params,
            "result_count": len(results)
        })
        self.last_query_results = results
        
        # 保持最近 20 轮对话
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def add_message(self, role: str, content: str):
        """添加消息到历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_recent_messages(self, count: int = 6) -> list[dict]:
        """获取最近的消息"""
        return self.conversation_history[-count:]
    
    def get_preferences(self) -> str:
        """获取用户偏好描述"""
        if not self.preferences:
            return "无历史偏好"
        return f"偏好平台: {self.preferences.get('platform', '无')}, 偏好类型: {self.preferences.get('type', '无')}"
    
    def update_preference(self, key: str, value: str):
        """更新用户偏好"""
        self.preferences[key] = value
