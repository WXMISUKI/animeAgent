# main.py
"""FastAPI 入口 - 使用 LangChain Agent 实现真正的AI智能体"""

import json
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入新的 LangChain Agent（真正的AI智能体）
from src.agent.agent import run_agent, run_agent_streaming, get_agent
from src.utils.logger import chat_logger

# 导入异常定义（新增）
try:
    from src.core.exceptions import (
        AnimeAgentException,
        DataSourceException,
        IntentParseException,
        ValidationException,
    )
    EXCEPTIONS_AVAILABLE = True
except ImportError:
    EXCEPTIONS_AVAILABLE = False

# 配置标准日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

# 设置各个模块的日志级别
logging.getLogger("DataSourceRouter").setLevel(logging.DEBUG)
logging.getLogger("BilibiliAPI").setLevel(logging.DEBUG)
logging.getLogger("BangumiAPI").setLevel(logging.DEBUG)
logging.getLogger("JikanAPI").setLevel(logging.DEBUG)
logging.getLogger("AniListAPI").setLevel(logging.DEBUG)
logging.getLogger("AnimeAgent").setLevel(logging.DEBUG)

api_logger = logging.getLogger("API")

# 创建 FastAPI 应用
app = FastAPI(
    title="番剧信息获取智能体",
    description="基于 MiniMax M2.5 的番剧查询智能体",
    version="0.1.0"
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    user_id: str = "default"
    session_id: str | None = None  # 会话 ID，支持多轮对话


class QueryResponse(BaseModel):
    """查询响应"""
    response: str
    data: list = []
    error: str | None = None


@app.get("/")
async def root():
    """根路径"""
    return {"message": "番剧信息获取智能体 API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# 兼容路由 /chat → /api/chat (已废弃，请使用 /api/chat)
@app.post("/chat")
async def chat_compat(request: QueryRequest):
    """对话接口 - 兼容旧版路径 [已废弃，请使用 /api/chat]"""
    return await chat(request)


# 兼容路由 /chat/stream → /api/chat/stream (已废弃，请使用 /api/chat/stream)
@app.post("/chat/stream")
async def chat_stream_compat(request: QueryRequest):
    """流式对话接口 - 兼容旧版路径 [已废弃，请使用 /api/chat/stream]"""
    return await chat_stream(request)


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """番剧查询接口（兼容旧版）"""
    
    try:
        # 执行新的 LangChain Agent
        result = run_agent(request.query)
        
        return QueryResponse(
            response=result,
            data=[],
            error=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: QueryRequest):
    """对话接口 - 使用 LangChain Agent
    
    支持多轮对话，通过 session_id 保持会话上下文
    """
    try:
        result = run_agent(
            user_input=request.query,
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        return {
            "response": result,
            "session_id": request.session_id,  # 返回 session_id 供客户端保存
            "error": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: QueryRequest):
    """流式对话接口（SSE）- 增量流式输出
    
    支持多轮对话，通过 session_id 保持会话上下文
    """
    
    # 记录请求开始
    api_logger.info(f"📥 收到请求 | 用户: {request.query} | 会话: {request.session_id}")
    
    # 记录用户发送的消息
    chat_logger.log_user_query(request.query)

    async def generate():
        chunk_count = 0
        # 首次返回 session_id
        yield f"data: {json.dumps({'type': 'session', 'session_id': request.session_id}, ensure_ascii=False)}\n\n"
        
        try:
            async for chunk in run_agent_streaming(
                user_input=request.query,
                session_id=request.session_id,
                user_id=request.user_id
            ):
                chunk_count += 1
                chunk_type = chunk.get("type", "unknown")
                chunk_status = chunk.get("status", "")
                
                # 记录每个chunk
                api_logger.info(f"📤 发送chunk {chunk_count}: type={chunk_type}, status={chunk_status}")
                
                # 直接转发所有增量数据
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
                # 记录关键节点日志
                if chunk_type == "intent" and chunk_status == "done":
                    intent = chunk.get("intent", "")
                    params = chunk.get("params", {})
                    api_logger.info(f"🎯 意图解析完成: {intent} | 参数: {params}")
                    chat_logger.log_intent(intent, params)
                
                elif chunk_type == "plan" and chunk_status == "done":
                    plan = chunk.get("plan", [])
                    api_logger.info(f"📋 执行计划完成: {plan}")
                
                elif chunk_type == "execution" and chunk_status == "done":
                    results = chunk.get("results", [])
                    success_count = sum(1 for r in results if r.get("success"))
                    api_logger.info(f"⚡ 工具执行完成: {success_count}/{len(results)} 成功")
                
                elif chunk_type == "output" and chunk_status == "done":
                    content = chunk.get("content", "")
                    chat_logger.log_response(content)
                    api_logger.info(f"✅ 对话完成 | 共发送 {chunk_count} 个chunk")

            api_logger.info(f"📊 流式响应结束 | 共 {chunk_count} 个chunk")

        except Exception as e:
            api_logger.error(f"❌ 对话异常: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== 全局异常处理器 ====================

if EXCEPTIONS_AVAILABLE:
    @app.exception_handler(AnimeAgentException)
    async def anime_agent_exception_handler(request: Request, exc: AnimeAgentException):
        """处理自定义业务异常"""
        api_logger.warning(f"业务异常: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "error_type": exc.code,
                "data": None
            }
        )
    
    @app.exception_handler(DataSourceException)
    async def data_source_exception_handler(request: Request, exc: DataSourceException):
        """处理数据源异常"""
        api_logger.error(f"数据源异常: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "error_type": "DATA_SOURCE_ERROR",
                "data": None
            }
        )
    
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """处理参数验证异常"""
        api_logger.warning(f"参数验证异常: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "error_type": "VALIDATION_ERROR",
                "data": None
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理未捕获的全局异常"""
    api_logger.error(f"未捕获的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "error_type": "INTERNAL_ERROR",
            "data": None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
