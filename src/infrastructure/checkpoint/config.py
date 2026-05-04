"""Checkpoint 配置模块"""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CheckpointBackend(str, Enum):
    """Checkpoint 存储后端"""
    MEMORY = "memory"      # 内存存储（开发/测试）
    REDIS = "redis"       # Redis 存储（生产）


@dataclass
class CheckpointConfig:
    """Checkpoint 配置"""
    backend: CheckpointBackend = CheckpointBackend.MEMORY
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379"
    redis_key_prefix: str = "langgraph:"
    redis_ttl: int = 86400  # 24 小时
    
    # 内存配置
    max_history: int = 50
    
    # 通用配置
    enable_checkpoint: bool = True
    checkpoint_threshold: int = 3  # 多少轮对话后开始 checkpoint


def get_checkpoint_config() -> CheckpointConfig:
    """从环境变量加载 Checkpoint 配置"""
    
    # 读取后端类型
    backend_str = os.getenv("CHECKPOINT_BACKEND", "memory").lower()
    backend = CheckpointBackend.MEMORY
    if backend_str == "redis":
        backend = CheckpointBackend.REDIS
    
    config = CheckpointConfig(
        backend=backend,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        redis_key_prefix=os.getenv("CHECKPOINT_KEY_PREFIX", "langgraph:"),
        redis_ttl=int(os.getenv("CHECKPOINT_TTL", "86400")),
        max_history=int(os.getenv("CHECKPOINT_MAX_HISTORY", "50")),
        enable_checkpoint=os.getenv("ENABLE_CHECKPOINT", "true").lower() == "true",
        checkpoint_threshold=int(os.getenv("CHECKPOINT_THRESHOLD", "3"))
    )
    
    logger.info(f"Checkpoint 配置: backend={config.backend}, enable={config.enable_checkpoint}")
    return config


# 全局配置实例
_checkpoint_config: Optional[CheckpointConfig] = None


def get_checkpoint_config_global() -> CheckpointConfig:
    """获取全局 Checkpoint 配置"""
    global _checkpoint_config
    if _checkpoint_config is None:
        _checkpoint_config = get_checkpoint_config()
    return _checkpoint_config
