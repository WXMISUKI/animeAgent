# main.py
"""FastAPI 入口"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from src.agent.graph import agent

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
    """番剧查询接口"""
    
    try:
        # 执行 Agent
        result = agent.invoke({
            "messages": [],
            "user_query": request.query
        })
        
        return QueryResponse(
            response=result.get("final_response", ""),
            data=result.get("anime_results", []),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: QueryRequest):
    """对话接口"""
    
    try:
        result = agent.invoke({
            "messages": [],
            "user_query": request.query
        })
        
        return {
            "response": result.get("final_response", ""),
            "error": result.get("error")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
