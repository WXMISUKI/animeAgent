# AGENTS.md - 番剧智能体项目开发指南

## 项目概述

这是一个基于 MiniMax M2.5 模型的番剧信息查询智能体，提供 Web 界面和 API 接口。项目采用 ReAct 模式 + LangChain Tools 架构，支持多数据源查询和流式输出。

### 核心功能

- 番剧信息查询（时间、类型、平台筛选）
- 番剧详情获取
- 热门排行榜
- 关键词搜索
- 多数据源并行查询 + 百度搜索 Fallback
- 流式输出实时响应

### 技术栈

| 组件 | 技术 |
|------|------|
| LLM | MiniMax M2.5 (通过阿里云 DashScope) |
| 后端框架 | FastAPI + LangGraph/LangChain |
| 前端 | HTML + CSS + JavaScript |
| 数据源 | Jikan API + AniList API + Bangumi API + 百度搜索 |

---

## 项目结构

```
minimaxtest/
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── quickstart.md            # 快速启动指南
├── agent.md                 # Agent 架构文档
├── minimax使用手册.md        # MiniMax 使用手册
├── src/                     # 后端源码
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 配置管理
│   ├── agent/              # Agent 核心模块
│   │   ├── agent.py        # 智能体主类 (IntentParser, Planner, Executor, ResponseGenerator)
│   │   ├── graph.py        # LangGraph 流程定义
│   │   ├── nodes.py        # LangGraph 节点
│   │   ├── state.py        # Agent 状态定义
│   │   └── tools.py        # LangChain Tools 定义
│   ├── skills/             # 技能模块
│   │   ├── base.py         # Skill 基类
│   │   ├── query.py        # 查询 Skill
│   │   ├── detail.py       # 详情 Skill
│   │   └── ranking.py      # 排行榜 Skill
│   ├── llm/                # LLM 客户端
│   │   ├── client.py       # MiniMax 客户端封装
│   │   └── prompts.py      # Prompt 模板
│   ├── data_sources/       # 数据源适配器
│   │   ├── base.py         # 数据源接口
│   │   ├── router.py       # 数据源路由器
│   │   ├── jikan.py        # Jikan API (MyAnimeList)
│   │   ├── anilist.py      # AniList API
│   │   ├── bangumi.py      # Bangumi API
│   │   ├── bilibili.py     # Bilibili API
│   │   ├── bilibili_sdk.py # Bilibili SDK
│   │   └── baidu_search.py # 百度搜索 API
│   ├── models/             # 数据模型
│   │   ├── query_params.py # 查询参数模型
│   │   ├── anime_info.py   # 番剧信息模型
│   │   └── context.py      # 上下文模型
│   └── utils/              # 工具模块
│       ├── cache.py        # 缓存工具
│       ├── logger.py       # 日志工具
│       └── error_handler.py # 错误处理
├── frontend/               # 前端页面
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── tests/                 # 测试代码
    ├── conftest.py
    ├── test_intent.py
    ├── test_tools.py
    └── test_data_sources.py
```

---

## 环境配置与启动

### 1. 环境要求

- Python 3.10+
- MiniMax API Key（通过阿里云 DashScope 获取）

### 2. 安装依赖

```bash
# 使用 conda 创建环境（推荐）
conda create -n anime-agent python=3.11 -y
conda activate anime-agent

# 安装依赖（国内镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env
```

编辑 `.env` 文件：

```env
# MiniMax 配置（必需）
ORCH_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
ORCH_MODEL=MiniMax/MiniMax-M2.5
ORCH_API_KEY=sk-your-api-key-here

# 日志配置（可选）
LOG_LEVEL=INFO
CACHE_TTL=3600
```

### 4. 启动服务

**后端（终端1）：**

```bash
conda activate anime-agent
cd D:\AI\AIcode\minimaxtest
uvicorn src.main:app --reload
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

**前端（终端2）：**

```bash
cd D:\AI\AIcode\minimaxtest\frontend
python -m http.server 8080
```

访问：http://localhost:8080

---

## 开发约定

### 代码风格

- **Python**：遵循 PEP 8，使用 Black 格式化
- **类型标注**：使用 Pydantic models 和 dataclasses
- **异步编程**：使用 `async/await`，优先使用 aiohttp

### 目录规范

| 目录 | 职责 |
|------|------|
| `src/agent/` | Agent 核心逻辑（意图解析、计划生成、执行器、响应生成） |
| `src/skills/` | 业务技能封装 |
| `src/data_sources/` | 外部 API 适配器 |
| `src/llm/` | LLM 调用封装 |
| `src/models/` | 数据模型定义 |
| `src/utils/` | 通用工具 |

### 日志规范

使用 `loguru` 和自定义 `chat_logger`：

```python
from src.utils.logger import chat_logger

# 记录用户查询
chat_logger.log_user_query("query")

# 记录意图解析
chat_logger.log_intent("query", {"time_range": "2026-03"})

# 记录工具调用
chat_logger.log_tool_call("query_anime", params, result)

# 记录响应
chat_logger.log_response("response content")
```

---

## 核心模块说明

### Agent 架构 (`src/agent/agent.py`)

```
用户输入 → IntentParser → Planner → Executor → ResponseGenerator → 最终回复
              ↓            ↓          ↓            ↓
          意图识别      执行计划    工具执行     响应生成
```

| 类 | 职责 |
|----|------|
| `IntentParser` | 解析用户意图，提取查询参数 |
| `Planner` | 根据意图生成执行计划 |
| `Executor` | 执行 LangChain Tools |
| `ResponseGenerator` | 将工具结果转换为自然语言 |

### LangChain Tools (`src/agent/tools.py`)

- `query_anime` - 番剧查询
- `get_anime_detail` - 番剧详情
- `get_anime_ranking` - 排行榜
- `web_search` - 百度搜索（Fallback）

### 数据源路由 (`src/data_sources/router.py`)

多数据源并行查询，失败时自动 fallback 到百度搜索：

```python
PLATFORM_MAP = {
    "jikan": ["Jikan"],
    "anilist": ["AniList"],
    "bangumi": ["Bangumi"],
    "all": ["Jikan", "AniList"],
}
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_intent.py -v

# 运行测试并显示日志
pytest tests/ -v --log-cli-level=INFO
```

### 测试结构

| 文件 | 覆盖范围 |
|------|----------|
| `test_intent.py` | 意图分类、直接回复 |
| `test_tools.py` | LangChain Tools 功能 |
| `test_data_sources.py` | 数据源查询 |

---

## 常见问题

### Q1: API 调用失败

```bash
# 验证环境变量
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ORCH_API_KEY'))"
```

### Q2: 前端无法连接后端

确保后端服务正在运行，端口 8000 可访问。

### Q3: 响应时间过长

- 启用缓存：`CACHE_TTL=3600`
- 检查网络连接
- 考虑优化 LLM 调用次数

---

## 相关文档

- [快速启动指南](./quickstart.md)
- [Agent 架构文档](./agent.md)
- [MiniMax 使用手册](./minimax使用手册.md)
