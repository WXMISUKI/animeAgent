# 番剧智能体 - 快速启动指南

## 项目简介

基于 MiniMax M2.5 模型的番剧信息查询智能体，提供 Web 界面和 API 接口。

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | MiniMax M2.5 (通过阿里云 DashScope) |
| 后端框架 | FastAPI + LangGraph |
| 前端 | HTML + CSS + JavaScript |
| 数据源 | Bangumi API (模拟数据) |

## 快速启动

### 1. 环境准备

```bash
# 创建 conda 环境
conda create -n anime-agent python=3.11 -y
conda activate anime-agent

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# MiniMax 配置（必需）
ORCH_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
ORCH_MODEL=MiniMax/MiniMax-M2.5
ORCH_API_KEY=sk-your-api-key-here

# 日志配置（可选）
LOG_LEVEL=INFO
CACHE_TTL=3600
```

### 3. 启动服务

#### 终端1：启动后端 API

```bash
cd D:\AI\AIcode\minimaxtest
uvicorn src.main:app --reload
```

后端启动成功后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

#### 终端2：启动前端

```bash
cd D:\AI\AIcode\minimaxtest\frontend
python -m http.server 8080
```

前端启动成功后访问：**http://localhost:8080**

## 使用方式

### 方式一：Web 界面

打开浏览器访问 http://localhost:8080

功能：
- 快捷按钮：最新番剧、热门排行、评分最高、日漫、国漫、剧场版
- 输入框：自由提问

### 方式二：API 接口

```bash
# 查询番剧
curl -X POST http://localhost:8000/api/query ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"2026年3月最新番剧有哪些？\"}"

# 健康检查
curl http://localhost:8000/health
```

### API 文档

访问 http://localhost:8000/docs 查看完整 API 文档（Swagger UI）

## 项目结构

```
anime-agent/
├── .env                    # 环境变量配置
├── requirements.txt         # Python 依赖
├── src/                    # 后端源码
│   ├── main.py            # FastAPI 入口
│   ├── agent/             # Agent 编排
│   ├── skills/            # 技能模块
│   ├── llm/               # LLM 客户端
│   ├── data_sources/      # 数据源
│   └── models/            # 数据模型
├── frontend/              # 前端页面
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── tests/                 # 测试代码
```

## 常见问题

### Q1: API 调用失败

**检查 .env 文件是否正确配置：**
```bash
# 验证环境变量
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ORCH_API_KEY'))"
```

### Q2: 前端无法连接后端

确保后端服务正在运行，端口 8000 可访问。

### Q3: 如何获取 MiniMax API Key

1. 访问阿里云 DashScope：https://dashscope.console.aliyun.com/
2. 注册/登录账号
3. 创建 API Key
4. 将 Key 填入 .env 文件

## 技术支持

- MiniMax 文档：https://platform.minimax.chat/document
- FastAPI 文档：https://fastapi.tiangolo.com/zh/
- LangGraph 文档：https://langchain-ai.github.io/langgraph/

---

**版本**: v2.1
**更新日期**: 2026-03-10
