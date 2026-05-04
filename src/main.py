# main.py
"""FastAPI 入口 - 使用 LangChain Agent 实现真正的AI智能体"""

import json
import asyncio
import logging
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入新的 LangChain Agent（真正的AI智能体）
from src.agent.agent import run_agent, run_agent_streaming, get_agent
from src.utils.logger import chat_logger

# 导入监控指标模块
from src.infrastructure.metrics import get_metrics_collector

# 导入追踪模块
from src.infrastructure.tracing import generate_trace_id, get_tracer, create_tracing_context

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
    description="基于豆包大模型的番剧查询智能体",
    version="0.2.0"
)

IS_VERCEL = bool(os.environ.get("VERCEL"))

# 前端目录（Vercel 用 public/，本地用 frontend/）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_DIR = os.path.join(_BASE_DIR, "public" if IS_VERCEL else "frontend")

# ---------- CORS 配置（通过环境变量控制） ----------
_cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- API Key 鉴权中间件 ----------
_api_auth_enabled = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
_api_auth_key = os.getenv("API_AUTH_KEY", "")
_api_auth_header = os.getenv("API_AUTH_HEADER", "x-api-key")

_PROTECTED_PREFIXES = ("/api/", "/chat")

if _api_auth_enabled and _api_auth_key:
    from starlette.middleware.base import BaseHTTPMiddleware

    class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            if any(path.startswith(p) for p in _PROTECTED_PREFIXES):
                token = request.headers.get(_api_auth_header, "")
                if token != _api_auth_key:
                    return JSONResponse(
                        status_code=401,
                        content={"code": 401, "message": "Unauthorized", "error_type": "AUTH_ERROR", "data": None},
                    )
            return await call_next(request)

    app.add_middleware(ApiKeyAuthMiddleware)
    api_logger.info(f"API 鉴权已启用，保护路径: {_PROTECTED_PREFIXES}")


class QueryRequest(BaseModel):
    """查询请求
    
    字段说明：
    - query: 用户查询内容
    - user_id: 用户 ID
    - session_id: 会话 ID（用于 SessionManager）
    - thread_id: 线程 ID（用于 LangGraph Checkpoint，多轮对话状态持久化）
    """
    query: str
    user_id: str = "default"
    session_id: str | None = None  # 会话 ID（SessionManager）
    thread_id: str | None = None   # 线程 ID（LangGraph Checkpoint）


class QueryResponse(BaseModel):
    """查询响应"""
    response: str
    data: list = []
    error: str | None = None


@app.get("/")
async def root():
    """根路径 - Vercel 返回前端页面，本地返回 API 信息"""
    if IS_VERCEL:
        index_path = os.path.join(_FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
    return {
        "message": "番剧信息获取智能体 API",
        "version": "0.2.0",
        "deployment": "vercel" if IS_VERCEL else "local",
        "checkpoint_backend": "memory"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/health/detail")
async def health_detail():
    """详细健康检查（适合部署后巡检）"""
    required_envs = ["ORCH_API_BASE", "ORCH_MODEL", "ORCH_API_KEY"]
    env_status = {
        key: bool(os.getenv(key)) for key in required_envs
    }
    checkpoint_backend = os.getenv("CHECKPOINT_BACKEND", "memory")
    checkpoint_enabled = os.getenv("ENABLE_CHECKPOINT", "true").lower() == "true"

    return {
        "status": "ok",
        "deployment": "vercel" if IS_VERCEL else "local",
        "runtime": {
            "python": os.getenv("PYTHON_VERSION", "unknown"),
            "vercel": IS_VERCEL
        },
        "config": {
            "checkpoint_enabled": checkpoint_enabled,
            "checkpoint_backend": checkpoint_backend,
            "cache_ttl": os.getenv("CACHE_TTL", "3600")
        },
        "env": {
            "required": env_status,
            "all_required_ready": all(env_status.values())
        },
        "limitations": [
            "CHECKPOINT_BACKEND=memory 时会话状态在实例重启后可能丢失",
            "Serverless 场景下 SSE 可能受平台超时策略影响"
        ]
    }


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    collector = get_metrics_collector()
    return Response(
        content=collector.get_metrics(),
        media_type=collector.get_content_type()
    )


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
    
    支持多轮对话：
    - session_id: 使用 SessionManager 管理会话
    - thread_id: 使用 LangGraph Checkpoint 持久化状态（支持断点恢复）
    
    错误处理策略：
    1. 每个步骤都有独立的 try-except
    2. 任何异常都会发送错误消息给前端
    3. 确保流式响应不会因异常而中断
    """
    
    # 生成 Trace ID 用于追踪
    trace_id = generate_trace_id()
    
    # 使用 thread_id 作为 Checkpoint 标识，如果没有提供则使用 session_id
    thread_id = request.thread_id or request.session_id
    
    # 创建追踪上下文
    tracer = get_tracer()
    tracer.start_trace(trace_id)
    create_tracing_context(
        trace_id=trace_id,
        user_query=request.query,
        user_id=request.user_id,
        session_id=request.session_id
    )
    
    # 记录请求开始（包含 Trace ID 和 Thread ID）
    checkpoint_info = "Checkpoint" if request.thread_id else "无Checkpoint"
    api_logger.info(f"📥 收到请求 | Trace: {trace_id} | 用户: {request.query} | 会话: {request.session_id} | {checkpoint_info}")
    
    # 记录用户发送的消息
    chat_logger.log_user_query(request.query)

    async def generate():
        chunk_count = 0
        error_occurred = False
        
        # 首次返回 session_id、trace_id 和 thread_id
        session_info = {
            'type': 'session', 
            'session_id': request.session_id, 
            'trace_id': trace_id,
            'thread_id': thread_id  # 返回 thread_id 给客户端
        }
        yield f"data: {json.dumps(session_info, ensure_ascii=False)}\n\n"
        
        try:
            # 步骤0: 准备阶段
            yield f"data: {json.dumps({'type': 'status', 'status': 'preparing', 'delta': '正在准备...' }, ensure_ascii=False)}\n\n"
            
            async for chunk in run_agent_streaming(
                user_input=request.query,
                session_id=request.session_id,
                user_id=request.user_id,
                trace_id=trace_id,
                thread_id=thread_id
            ):
                chunk_count += 1
                chunk_type = chunk.get("type", "unknown")
                chunk_status = chunk.get("status", "")
                
                # 记录每个chunk
                api_logger.info(f"📤 发送chunk {chunk_count}: type={chunk_type}, status={chunk_status} | Trace: {trace_id}")
                
                try:
                    # 直接转发所有增量数据
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                except Exception as e:
                    api_logger.error(f"❌ 发送chunk失败: {e} | Trace: {trace_id}")
                    # 尝试发送错误消息
                    try:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'发送数据失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    except:
                        pass
                    continue
                
                # 记录关键节点日志
                if chunk_type == "intent" and chunk_status == "done":
                    intent = chunk.get("intent", "")
                    params = chunk.get("params", {})
                    api_logger.info(f"🎯 意图解析完成: {intent} | 参数: {params} | Trace: {trace_id}")
                    chat_logger.log_intent(intent, params)
                
                elif chunk_type == "plan" and chunk_status == "done":
                    plan = chunk.get("plan", [])
                    api_logger.info(f"📋 执行计划完成: {plan} | Trace: {trace_id}")
                
                elif chunk_type == "execution" and chunk_status == "done":
                    results = chunk.get("results", [])
                    success_count = sum(1 for r in results if r.get("success"))
                    api_logger.info(f"⚡ 工具执行完成: {success_count}/{len(results)} 成功 | Trace: {trace_id}")
                
                elif chunk_type == "output" and chunk_status == "done":
                    content = chunk.get("content", "")
                    chat_logger.log_response(content)
                    api_logger.info(f"✅ 对话完成 | 共发送 {chunk_count} 个chunk | Trace: {trace_id}")

            api_logger.info(f"📊 流式响应结束 | 共 {chunk_count} 个chunk | Trace: {trace_id}")

        except asyncio.CancelledError:
            # 用户主动断开连接
            api_logger.warning(f"⚠️ 流式响应被客户端取消")
            error_occurred = True
            try:
                yield f"data: {json.dumps({'type': 'error', 'content': '连接已断开'}, ensure_ascii=False)}\n\n"
            except:
                pass
                
        except Exception as e:
            api_logger.error(f"❌ 对话异常: {str(e)} | Trace: {trace_id}", exc_info=True)
            error_occurred = True
            try:
                # 发送友好的错误消息
                error_message = _get_user_friendly_error(str(e))
                yield f"data: {json.dumps({'type': 'error', 'content': error_message}, ensure_ascii=False)}\n\n"
            except Exception as e2:
                api_logger.error(f"❌ 发送错误消息也失败了: {e2} | Trace: {trace_id}")
        
        finally:
            # 发送完成信号
            if not error_occurred:
                try:
                    yield f"data: {json.dumps({'type': 'done', 'chunk_count': chunk_count}, ensure_ascii=False)}\n\n"
                except:
                    pass

    def _get_user_friendly_error(error_str: str) -> str:
        """将技术错误转换为用户友好的错误消息"""
        error_lower = error_str.lower()
        
        if "timeout" in error_lower or "timed out" in error_lower:
            return "请求超时了，请稍后重试。"
        elif "connection" in error_lower or "connect" in error_lower:
            return "网络连接不稳定，请检查网络后重试。"
        elif "api" in error_lower and "key" in error_lower:
            return "服务配置问题，请联系管理员。"
        elif "rate limit" in error_lower or "限流" in error_lower:
            return "请求过于频繁，请稍后再试。"
        elif "no such file" in error_lower or "not found" in error_lower:
            return "服务暂时不可用，请稍后重试。"
        else:
            return f"服务出现了一些问题，请稍后重试。"

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


# 挂载前端静态文件（放在所有路由之后，作为兜底）
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
