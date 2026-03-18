# utils/logger.py
"""日志工具 - 支持会话日志和审计日志

特点：
- 每次启动生成新的日志文件（带时间戳）
- 启动时自动清理旧日志
- 同时输出到控制台和文件
- 记录完整对话流程
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
import logging


class ChatLogger:
    """会话日志 - 记录完整对话流程
    
    每次启动生成新日志文件，日志文件命名格式：
    chat_YYYY-MM-DD_HH-MM-SS.log
    
    日志保留策略：每次启动时删除旧日志
    """
    
    _instance: Optional["ChatLogger"] = None
    _initialized: bool = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志系统"""
        if self._initialized:
            return
        
        # 配置参数
        self.log_dir = os.getenv("LOG_DIR", "logs")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.session_id = uuid.uuid4().hex[:8]
        self.session_start = datetime.now()
        
        # 生成会话日志文件名
        self.timestamp = self.session_start.strftime("%Y-%m-%d_%H-%M-%S")
        self.chat_log_file = os.path.join(self.log_dir, f"chat_{self.timestamp}.log")
        self.audit_log_file = os.path.join(self.log_dir, f"audit_{self.timestamp}.log")
        
        # 初始化
        self._setup_directories()
        self._cleanup_old_logs()
        self._setup_loguru()
        
        # 写入会话开始标记
        self._log_session_start()
        
        ChatLogger._initialized = True
    
    def _setup_directories(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
    
    def _cleanup_old_logs(self):
        """清理旧日志 - 每次启动时删除之前的日志"""
        if not os.path.exists(self.log_dir):
            return
        
        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith(("chat_", "audit_")) and filename.endswith(".log"):
                    old_file = os.path.join(self.log_dir, filename)
                    try:
                        os.remove(old_file)
                        logger.info(f"已删除旧日志: {filename}")
                    except Exception as e:
                        logger.warning(f"删除旧日志失败: {filename}, {e}")
        except Exception as e:
            logger.warning(f"清理旧日志时出错: {e}")
    
    def _setup_loguru(self):
        """配置loguru日志器"""
        # 移除默认处理器
        logger.remove()
        
        # 控制台输出（带颜色）
        console_format = (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stdout,
            level=self.log_level,
            format=console_format,
            colorize=True
        )
        
        # 文件输出（JSON格式，便于程序解析）
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - {message}"
        )
        
        logger.add(
            self.chat_log_file,
            level="DEBUG",
            format=file_format,
            rotation="100 MB",  # 单个文件最大100MB
            retention="1 day",  # 保留1天
            encoding="utf-8"
        )
    
    def _log_session_start(self):
        """写入会话开始标记"""
        session_info = {
            "event": "session_start",
            "session_id": self.session_id,
            "timestamp": self.session_start.isoformat(),
            "message": f"会话开始 - Session ID: {self.session_id}"
        }
        
        # 写入控制台
        logger.info(f"🆕 会话开始 | Session ID: {self.session_id} | Time: {self.timestamp}")
        
        # 写入日志文件
        self._write_to_file(session_info, "session")
    
    def _write_to_file(self, data: Dict[str, Any], event_type: str = "log"):
        """写入JSON格式日志到文件"""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "event": event_type,
                **data
            }
            
            with open(self.chat_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"写入日志失败: {e}")
    
    # ==================== 对话日志方法 ====================
    
    def log_user_query(self, query: str, user_id: str = "default"):
        """记录用户查询"""
        data = {
            "event": "user_query",
            "query": query,
            "user_id": user_id
        }
        
        logger.info(f"👤 用户: {query}")
        self._write_to_file(data, "user_query")
    
    def log_intent(self, intent: str, params: Dict[str, Any] = None):
        """记录意图识别结果"""
        data = {
            "event": "intent_classify",
            "intent": intent,
            "params": params or {}
        }
        
        logger.info(f"🎯 意图: {intent}")
        self._write_to_file(data, "intent_classify")
    
    def log_tool_call(self, tool_name: str, params: Dict[str, Any], result: Any = None):
        """记录工具调用"""
        data = {
            "event": "tool_call",
            "tool": tool_name,
            "params": params,
            "result_preview": str(result)[:200] if result else None
        }
        
        logger.info(f"🔧 工具: {tool_name} | 参数: {params}")
        self._write_to_file(data, "tool_call")
    
    def log_tool_result(self, tool_name: str, success: bool, result: Any = None, error: str = None):
        """记录工具执行结果"""
        data = {
            "event": "tool_result",
            "tool": tool_name,
            "success": success,
            "result_preview": str(result)[:500] if result else None,
            "error": error
        }
        
        status = "✅" if success else "❌"
        logger.info(f"{status} 工具结果: {tool_name} | 成功: {success}")
        self._write_to_file(data, "tool_result")
    
    def log_llm_call(self, prompt_type: str, input_preview: str, output_preview: str = None):
        """记录LLM调用"""
        data = {
            "event": "llm_call",
            "prompt_type": prompt_type,
            "input_preview": input_preview[:200],
            "output_preview": output_preview[:200] if output_preview else None
        }
        
        logger.debug(f"🤖 LLM: {prompt_type}")
        self._write_to_file(data, "llm_call")
    
    def log_response(self, response: str):
        """记录Agent回复"""
        data = {
            "event": "agent_response",
            "response": response
        }
        
        logger.info(f"🤖 回复: {response[:100]}...")
        self._write_to_file(data, "agent_response")
    
    def log_error(self, error: str, context: Dict[str, Any] = None):
        """记录错误"""
        data = {
            "event": "error",
            "error": error,
            "context": context or {}
        }
        
        logger.error(f"❌ 错误: {error}")
        self._write_to_file(data, "error")
    
    def log_session_end(self):
        """记录会话结束"""
        session_info = {
            "event": "session_end",
            "session_id": self.session_id,
            "duration_seconds": (datetime.now() - self.session_start).total_seconds()
        }
        
        logger.info(f"🏁 会话结束 | Session ID: {self.session_id}")
        self._write_to_file(session_info, "session_end")
    
    @property
    def session_id_short(self) -> str:
        """获取短会话ID"""
        return self.session_id


# ==================== 审计日志（兼容旧接口） ====================

class AuditLogger:
    """审计日志 - 记录关键操作（兼容旧接口）"""
    
    def __init__(self, log_file: str = None):
        # 使用ChatLogger的会话日志文件
        chat_logger = ChatLogger()
        self.log_file = log_file or chat_logger.chat_log_file.replace("chat_", "audit_")
    
    def log(
        self,
        event_type: str,
        user_query: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        duration_ms: Optional[float] = None
    ):
        """记录审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_query": user_query,
            "success": success,
            "duration_ms": duration_ms,
            "details": details or {}
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"审计日志写入失败: {e}")
    
    def log_tool_call(self, **kwargs):
        """记录工具调用"""
        # 兼容旧接口
        pass
    
    def log_intent_classify(self, **kwargs):
        """记录意图分类"""
        # 兼容旧接口
        pass


# ==================== 便捷函数 ====================

def setup_logger():
    """配置日志（兼容旧接口）"""
    return ChatLogger()


# 创建全局实例 - 使用loguru的logger作为基础
chat_logger = ChatLogger()

# 导出 - 同时导出loguru的logger以保持兼容性
__all__ = ["logger", "chat_logger", "ChatLogger", "AuditLogger", "audit_logger"]

# 保持旧接口兼容 - 使用loguru的logger
# 注意：这里引用的是模块级别导入的loguru logger
audit_logger = chat_logger  # 兼容旧接口
