# data_sources/utils/logger.py
"""数据源日志工具

提供详细的请求/响应日志，便于调试和问题溯源
"""

import json
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from functools import wraps

# 配置日志
logger = logging.getLogger("DataSource")
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)

# 避免重复添加 handler
if not logger.handlers:
    logger.addHandler(handler)


class DataSourceLogger:
    """数据源日志记录器"""
    
    @staticmethod
    def log_request(
        source: str,
        action: str,
        url: str,
        params: Dict[str, Any],
        anime_type: str = None,
        time_range: str = None,
        keyword: str = None
    ):
        """记录请求信息"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "action": action,
            "request": {
                "url": url,
                "params": params,
                "filters": {
                    "anime_type": anime_type,
                    "time_range": time_range,
                    "keyword": keyword
                }
            }
        }
        logger.info(f"🔍 [{source}] 请求: {action}")
        logger.debug(f"📤 请求详情: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
        return log_data
    
    @staticmethod
    def log_response(
        source: str,
        action: str,
        status: int,
        data_count: int = 0,
        raw_data: Any = None,
        error: str = None
    ):
        """记录响应信息"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "action": action,
            "response": {
                "status": status,
                "data_count": data_count,
                "raw_data": raw_data
            },
            "error": error
        }
        
        if error:
            logger.warning(f"❌ [{source}] 错误: {error}")
        else:
            logger.info(f"✅ [{source}] 响应: {status}, 数据条数: {data_count}")
        
        logger.debug(f"📥 响应详情: {json.dumps(log_data, ensure_ascii=False, indent=2)[:2000]}...")
        return log_data
    
    @staticmethod
    def log_parse_result(
        source: str,
        action: str,
        items: list,
        sample_data: list = None
    ):
        """记录解析结果"""
        sample = sample_data or []
        if items and sample:
            logger.info(f"📊 [{source}] 解析成功: {len(items)} 条数据")
            logger.debug(f"📝 示例数据: {json.dumps(sample[:2], ensure_ascii=False, indent=2)}")
        else:
            logger.warning(f"⚠️ [{source}] 解析结果为空")


def log_async_method(source: str):
    """异步方法日志装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method_name = func.__name__
            start_time = time.time()
            
            # 提取参数
            params = kwargs.get('params', args[1] if len(args) > 1 else None)
            anime_type = params.anime_type if params else None
            time_range = params.time_range if params else None
            keyword = params.keyword if params else None
            
            # 记录开始
            logger.info(f"🚀 [{source}] 开始 {method_name}")
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # 记录成功
                DataSourceLogger.log_response(
                    source=source,
                    action=method_name,
                    status=200,
                    data_count=len(result) if result else 0
                )
                
                logger.info(f"🏁 [{source}] 完成 {method_name}, 耗时: {elapsed:.2f}s")
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"💥 [{source}] 异常 {method_name}: {str(e)}, 耗时: {elapsed:.2f}s")
                raise
        
        return wrapper
    return decorator


def log_method_call(source: str):
    """方法调用日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            method_name = func.__name__
            logger.info(f"📞 [{source}] 调用 {method_name}")
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"❌ [{source}] {method_name} 失败: {str(e)}")
                raise
        
        return wrapper
    return decorator
