# main.py
"""FastAPI 入口 - 使用 LangChain Agent 实现真正的AI智能体"""

import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入新的 LangChain Agent（真正的AI智能体）
from src.agent.agent import run_agent, run_agent_streaming, get_agent

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
    """对话接口 - 使用 LangChain Agent"""

    try:
        result = run_agent(request.query)
        
        return {
            "response": result,
            "error": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: QueryRequest):
    """流式对话接口（SSE）- 使用 ReAct Agent 动态规划
    
    这个接口会：
    1. 接收用户输入
    2. LLM 自主规划每一步（thought → action → observation）
    3. 执行工具并获取结果
    4. 根据结果动态调整下一步行动
    5. 流式输出思考过程和最终回复
    """

    async def generate():
        try:
            # 使用 ReAct Agent 流式输出
            # 支持多种类型：thinking（思考过程）、tool（工具调用）、tool_result（结果）、output（最终回复）
            
            async for chunk in run_agent_streaming(request.query, []):
                chunk_type = chunk.get("type")
                
                if chunk_type == "thinking":
                    # 思考过程 - 显示 LLM 的推理
                    content = chunk.get("content", {})
                    thinking_data = {
                        "type": "thinking",
                        "step": content.get("step"),
                        "thought": content.get("thought"),
                        "action": content.get("action"),
                        "action_input": content.get("action_input"),
                        "observation": content.get("observation")
                    }
                    yield f"data: {json.dumps(thinking_data, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "tool":
                    # 工具调用通知
                    yield f"data: {json.dumps({'type': 'tool', 'content': chunk.get('content')}, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "tool_result":
                    # 工具返回结果
                    yield f"data: {json.dumps({'type': 'tool_result', 'content': chunk.get('content')}, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "output":
                    # 最终回复
                    content = chunk.get("content", "")
                    if content:
                        yield f"data: {json.dumps({'type': 'output', 'content': content}, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "error":
                    # 错误信息
                    yield f"data: {json.dumps({'type': 'error', 'content': chunk.get('content')}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
