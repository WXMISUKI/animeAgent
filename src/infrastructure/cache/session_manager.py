"""会话管理器 - 支持多轮对话上下文"""

import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationMessage:
    """对话消息"""
    
    def __init__(
        self, 
        role: str, 
        content: str,
        timestamp: Optional[float] = None
    ):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp or datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp")
        )


class Session:
    """会话数据"""
    
    def __init__(
        self,
        session_id: str,
        user_id: str = "default",
        context: Optional[List[Dict]] = None,
        slots: Optional[Dict] = None,
        preferences: Optional[Dict] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.context: List[ConversationMessage] = [
            ConversationMessage.from_dict(m) if isinstance(m, dict) else m
            for m in (context or [])
        ]
        self.slots = slots or {}  # 槽位信息
        self.preferences = preferences or {}  # 用户偏好
        self.created_at = created_at or datetime.now().timestamp()
        self.updated_at = updated_at or datetime.now().timestamp()
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.context.append(ConversationMessage(role, content))
        self.updated_at = datetime.now().timestamp()
    
    def get_context_text(self, max_turns: int = 5) -> str:
        """获取上下文文本（最近 N 轮）"""
        messages = self.context[-max_turns * 2:]  # 每轮2条消息
        return "\n".join([
            f"{'用户' if m.role == 'user' else '助手'}: {m.content}"
            for m in messages
        ])
    
    def get_recent_messages(self, n: int = 6) -> List[ConversationMessage]:
        """获取最近 N 条消息"""
        return self.context[-n:]
    
    def clear_context(self):
        """清空上下文"""
        self.context.clear()
        self.updated_at = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "context": [m.to_dict() for m in self.context],
            "slots": self.slots,
            "preferences": self.preferences,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        context = data.get("context", [])
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id", "default"),
            context=[ConversationMessage.from_dict(m) for m in context] if context else [],
            slots=data.get("slots", {}),
            preferences=data.get("preferences", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class SessionManager:
    """会话管理器 - 支持内存和 Redis 两种存储"""
    
    def __init__(self, redis_cache=None, session_ttl: int = 86400):
        self._memory_store: Dict[str, Session] = {}
        self.redis_cache = redis_cache
        self.session_ttl = session_ttl
    
    def create_session(self, user_id: str = "default") -> Session:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, user_id=user_id)
        
        # 尝试存储到 Redis
        if self.redis_cache and self.redis_cache.enabled:
            self.redis_cache.set_session(session_id, session.to_dict(), self.session_ttl)
        else:
            self._memory_store[session_id] = session
        
        logger.info(f"创建新会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        # 优先从 Redis 获取
        if self.redis_cache and self.redis_cache.enabled:
            data = self.redis_cache.get_session(session_id)
            if data:
                # 刷新 TTL
                self.redis_cache.set_session(session_id, data, self.session_ttl)
                return Session.from_dict(data)
            return None
        
        # 从内存获取
        return self._memory_store.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str], user_id: str = "default") -> Session:
        """获取或创建会话"""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(user_id)
    
    def update_session(self, session: Session):
        """更新会话"""
        session_id = session.session_id
        session.updated_at = datetime.now().timestamp()
        
        if self.redis_cache and self.redis_cache.enabled:
            self.redis_cache.set_session(session_id, session.to_dict(), self.session_ttl)
        else:
            self._memory_store[session_id] = session
    
    def delete_session(self, session_id: str):
        """删除会话"""
        if self.redis_cache and self.redis_cache.enabled:
            self.redis_cache.delete_session(session_id)
        else:
            self._memory_store.pop(session_id, None)
        
        logger.info(f"删除会话: {session_id}")
    
    def add_user_message(self, session_id: str, content: str):
        """添加用户消息"""
        session = self.get_session(session_id)
        if session:
            session.add_message("user", content)
            self.update_session(session)
    
    def add_assistant_message(self, session_id: str, content: str):
        """添加助手消息"""
        session = self.get_session(session_id)
        if session:
            session.add_message("assistant", content)
            self.update_session(session)
    
    def update_slots(self, session_id: str, slots: dict):
        """更新槽位"""
        session = self.get_session(session_id)
        if session:
            session.slots.update(slots)
            self.update_session(session)
    
    def get_slots(self, session_id: str) -> dict:
        """获取槽位"""
        session = self.get_session(session_id)
        return session.slots if session else {}
    
    def get_context_text(self, session_id: str, max_turns: int = 5) -> str:
        """获取上下文文本"""
        session = self.get_session(session_id)
        return session.get_context_text(max_turns) if session else ""


# 全局会话管理器实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器"""
    global _session_manager
    if _session_manager is None:
        from ..infrastructure.cache.redis_cache import get_redis_cache
        redis_cache = get_redis_cache()
        from ..core.config import settings
        _session_manager = SessionManager(
            redis_cache=redis_cache,
            session_ttl=settings.session_ttl
        )
    return _session_manager