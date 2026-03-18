"""全局异常定义"""

from fastapi import HTTPException, status


class AnimeAgentException(HTTPException):
    """智能体基础异常"""
    
    def __init__(
        self, 
        detail: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_ERROR"
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class DataSourceException(AnimeAgentException):
    """数据源异常"""
    
    def __init__(self, detail: str, source: str = "unknown"):
        super().__init__(
            detail=f"数据源 [{source}] 查询失败: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATA_SOURCE_ERROR"
        )
        self.source = source


class IntentParseException(AnimeAgentException):
    """意图解析异常"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=f"意图解析失败: {detail}",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INTENT_PARSE_ERROR"
        )


class ToolExecutionException(AnimeAgentException):
    """工具执行异常"""
    
    def __init__(self, tool_name: str, detail: str):
        super().__init__(
            detail=f"工具 [{tool_name}] 执行失败: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TOOL_EXECUTION_ERROR"
        )
        self.tool_name = tool_name


class SessionException(AnimeAgentException):
    """会话管理异常"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=f"会话管理错误: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SESSION_ERROR"
        )


class ValidationException(AnimeAgentException):
    """参数验证异常"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=f"参数验证失败: {detail}",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR"
        )
