"""内存版 Checkpointer - 用于开发和测试

使用 LangGraph 的 InMemorySaver 实现，适合：
- 开发调试
- 单实例部署
- 小规模应用

注意：生产环境建议使用 RedisCheckpointer
"""

import logging
from typing import Optional, Any, Dict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)


class MemoryCheckpointer:
    """内存版 Checkpointer 封装类
    
    提供更友好的 API 和配置选项
    """
    
    def __init__(
        self,
        serde: Optional[Any] = None,
        max_history: int = 50
    ):
        """
        Args:
            serde: 序列化器（可选）
            max_history: 最大历史记录数（用于内存管理）
        """
        self.max_history = max_history
        self._saver: Optional[BaseCheckpointSaver] = None
        self._serde = serde
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            if self._serde:
                self._saver = InMemorySaver(serde=self._serde)
            else:
                self._saver = InMemorySaver()
            self._initialized = True
            logger.info("✅ MemoryCheckpointer 初始化完成")
    
    @property
    def saver(self) -> BaseCheckpointSaver:
        """获取 LangGraph 兼容的 Saver"""
        self._ensure_initialized()
        return self._saver
    
    def get_checkpointer(self) -> BaseCheckpointSaver:
        """获取 Checkpointer（兼容旧接口）"""
        return self.saver
    
    def clear_thread(self, thread_id: str):
        """清除指定线程的历史记录"""
        if self._saver:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._saver.adelete(thread_id))
                else:
                    loop.run_until_complete(self._saver.adelete(thread_id))
            except Exception as e:
                logger.warning(f"清除线程历史失败: {e}")
    
    def list_threads(self) -> list:
        """列出所有线程（仅用于调试）"""
        # InMemorySaver 不支持直接列出所有线程
        # 这里返回空列表
        return []


# 全局实例
_memory_checkpointer: Optional[MemoryCheckpointer] = None


def get_memory_checkpointer() -> MemoryCheckpointer:
    """获取全局 MemoryCheckpointer 实例"""
    global _memory_checkpointer
    if _memory_checkpointer is None:
        _memory_checkpointer = MemoryCheckpointer()
    return _memory_checkpointer


def get_memory_saver() -> BaseCheckpointSaver:
    """获取 LangGraph 兼容的 InMemorySaver（便捷函数）"""
    return get_memory_checkpointer().saver
