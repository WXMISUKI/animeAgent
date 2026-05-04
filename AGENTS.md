# AGENTS.md - 番剧智能体项目开发指南

## 项目概述

这是一个基于 MiniMax M2.5 模型的企业级番剧信息查询智能体，提供 Web 界面和 API 接口。项目采用 ReAct 模式 + LangChain Tools 架构，支持多数据源查询、流式输出、多轮对话和完整的监控追踪体系。

### 核心功能

- 番剧信息查询（时间、类型、平台筛选）
- 番剧详情获取
- 热门排行榜
- 关键词搜索
- 多数据源并行查询 + 百度搜索 Fallback
- 流式输出实时响应
- **多轮对话支持**（通过 LangGraph Checkpoint 实现短期记忆）
- **监控指标采集**（Prometheus 兼容）
- **分布式链路追踪**（请求全链路可视化）
- **企业级异常处理体系**

### 技术栈

| 组件 | 技术 |
|------|------|
| LLM | MiniMax M2.5 (通过阿里云 DashScope) |
| 后端框架 | FastAPI + LangGraph/LangChain |
| 前端 | HTML + CSS + JavaScript |
| 数据源 | Jikan API + AniList API + Bangumi API + Bilibili API + 百度搜索 |
| 状态管理 | LangGraph Checkpoint (内存/Redis) |
| 监控指标 | Prometheus Client |
| 缓存 | Redis |
| 日志 | Loguru |
| 测试框架 | Pytest + Pytest-Asyncio |

---

## 项目结构

```
minimaxtest/
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
├── quickstart.md                  # 快速启动指南
├── agent.md                       # Agent 架构文档
├── minimax使用手册.md              # MiniMax 使用手册
├── docs/                          # 项目文档
│   ├── 百度搜索api调用说明手册.md
│   ├── 短期记忆增强（多轮对话优化）实现说明.md
│   ├── 番剧智能体监控指标与参数追踪完善方案.md
│   └── ...
├── src/                           # 后端源码
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置管理
│   ├── core/                      # 核心模块
│   │   ├── config.py              # 核心配置
│   │   └── exceptions.py          # 全局异常定义
│   ├── agent/                     # Agent 核心模块
│   │   ├── agent.py               # Agent 入口
│   │   ├── graph.py               # LangGraph 流程定义（支持 Checkpoint）
│   │   ├── nodes.py               # LangGraph 节点
│   │   ├── state.py               # Agent 状态定义
│   │   ├── tools.py               # LangChain Tools 定义
│   │   ├── executor.py            # 执行器
│   │   ├── planner.py             # 计划生成器
│   │   ├── response.py            # 响应生成器
│   │   └── intent/                # 意图识别模块（增强版）
│   │       ├── agent.py           # 意图识别 Agent
│   │       ├── parser.py          # 参数解析器
│   │       ├── prompts.py         # Prompt 模板
│   │       ├── slots.py           # 意图槽位定义
│   │       └── types.py           # 意图类型定义
│   ├── skills/                    # 技能模块
│   │   ├── base.py                # Skill 基类
│   │   ├── query.py               # 查询 Skill
│   │   ├── detail.py              # 详情 Skill
│   │   └── ranking.py             # 排行榜 Skill
│   ├── llm/                       # LLM 客户端
│   │   ├── client.py              # MiniMax 客户端封装
│   │   └── prompts.py             # Prompt 模板
│   ├── data_sources/              # 数据源适配器
│   │   ├── base.py                # 数据源接口
│   │   ├── router.py              # 数据源路由器
│   │   ├── jikan.py               # Jikan API (MyAnimeList)
│   │   ├── anilist.py             # AniList API
│   │   ├── bangumi.py             # Bangumi API
│   │   ├── bilibili.py            # Bilibili API
│   │   ├── bilibili_sdk.py        # Bilibili SDK
│   │   ├── baidu_search.py        # 百度搜索 API
│   │   └── utils/                 # 数据源工具
│   ├── models/                    # 数据模型
│   │   ├── query_params.py        # 查询参数模型
│   │   ├── anime_info.py          # 番剧信息模型
│   │   └── context.py             # 上下文模型
│   ├── infrastructure/            # 企业级基础设施
│   │   ├── checkpoint/            # Checkpoint（短期记忆）
│   │   │   ├── config.py          # Checkpoint 配置
│   │   │   ├── memory_checkpointer.py    # 内存 Checkpointer
│   │   │   └── redis_checkpointer.py     # Redis Checkpointer
│   │   ├── cache/                 # 缓存基础设施
│   │   ├── metrics/               # 监控指标
│   │   │   ├── collector.py       # 指标收集器
│   │   │   ├── business_metrics.py    # 业务指标
│   │   │   ├── counters.py        # 计数器
│   │   │   ├── gauges.py          # 仪表盘
│   │   │   └── histograms.py      # 直方图
│   │   └── tracing/               # 链路追踪
│   │       ├── tracer.py          # 追踪器
│   │       ├── context.py         # 追踪上下文
│   │       └── parameter_tracker.py    # 参数追踪
│   └── utils/                     # 工具模块
│       ├── cache.py               # 缓存工具
│       ├── logger.py              # 日志工具
│       └── error_handler.py       # 错误处理
├── frontend/                      # 前端页面
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── tests/                        # 测试代码
    ├── conftest.py
    ├── test_intent.py
    ├── test_intent_parser.py
    ├── test_tools.py
    ├── test_data_sources.py
    ├── test_data_sources_integration.py
    ├── test_metrics.py
    ├── test_parameter_flow.py
    └── test_tracing.py
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
| `src/core/` | 核心配置和全局异常定义 |
| `src/agent/` | Agent 核心逻辑（意图解析、计划生成、执行器、响应生成） |
| `src/agent/intent/` | 意图识别增强版（包含意图分类、参数解析、槽位填充） |
| `src/skills/` | 业务技能封装 |
| `src/data_sources/` | 外部 API 适配器 |
| `src/llm/` | LLM 调用封装 |
| `src/models/` | 数据模型定义 |
| `src/infrastructure/` | 企业级基础设施 |
| `src/infrastructure/checkpoint/` | LangGraph Checkpoint 支持（内存/Redis） |
| `src/infrastructure/metrics/` | Prometheus 监控指标 |
| `src/infrastructure/tracing/` | 分布式链路追踪 |
| `src/infrastructure/cache/` | 缓存基础设施 |
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

### Agent 架构 (`src/agent/`)

采用 LangGraph 状态机架构，支持多轮对话和短期记忆：

```
用户输入 → classify_intent → parse_intent → execute_skill → format_response → 最终回复
              ↓               ↓              ↓              ↓
          意图分类      参数解析        工具执行       响应生成
              ↓
          [条件分支]
              ├─ direct_reply → 直接回复（打招呼等）
              └─ skill → 继续解析参数并执行
```

#### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `LangGraph 流程` | `graph.py` | 定义 Agent 状态机流程，支持 Checkpoint |
| `意图分类` | `nodes.py` | 识别用户意图类型（查询、详情、排行、打招呼等） |
| `参数解析` | `nodes.py` | 根据意图类型提取查询参数 |
| `技能执行` | `nodes.py` | 执行相应的 Skill（查询、详情、排行） |
| `响应格式化` | `nodes.py` | 将执行结果转换为自然语言回复 |
| `状态管理` | `state.py` | 定义 Agent 状态数据结构 |

#### 意图识别系统 (`src/agent/intent/`)

增强版意图识别，支持 11 种意图类型：

| 意图类型 | 说明 | 需要数据 |
|----------|------|----------|
| `greeting` | 打招呼 | ❌ |
| `description` | 询问身份 | ❌ |
| `capability` | 询问能力 | ❌ |
| `query` | 番剧查询 | ✅ |
| `detail` | 番剧详情 | ✅ |
| `ranking` | 排行榜 | ✅ |
| `recommend` | 推荐 | ✅ |
| `compare` | 对比 | ✅ |
| `thanks` | 感谢 | ❌ |
| `chat` | 闲聊 | ❌ |
| `unknown` | 无法理解 | ❌ |

### LangChain Tools (`src/agent/tools.py`)

- `query_anime` - 番剧查询（支持多数据源并行）
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

支持的数据源：Jikan API (MyAnimeList)、AniList API、Bangumi API、Bilibili API、百度搜索

---

## 企业级基础设施

### 多轮对话与短期记忆 (`src/infrastructure/checkpoint/`)

基于 LangGraph Checkpoint 实现多轮对话状态持久化：

#### 支持的存储后端

| 后端 | 配置 | 适用场景 |
|------|------|----------|
| **内存** | `CHECKPOINT_BACKEND=memory` | 单机开发、测试 |
| **Redis** | `CHECKPOINT_BACKEND=redis` | 生产环境、分布式部署 |

#### 使用方式

```python
# 请求时传递 thread_id（用于恢复对话状态）
request = {
    "query": "那第二季呢？",
    "session_id": "user_123",
    "thread_id": "conv_456"  # 用于 Checkpoint 恢复
}
```

#### 配置环境变量

```env
# 启用 Checkpoint
CHECKPOINT_ENABLE=true
CHECKPOINT_BACKEND=redis

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=anime_agent:
REDIS_TTL=86400  # 对话状态保留 24 小时
```

### 监控指标 (`src/infrastructure/metrics/`)

基于 Prometheus Client 的监控指标采集：

#### 指标类型

| 指标类型 | 说明 | 示例 |
|----------|------|------|
| **Counters** | 单调递增计数器 | 请求总数、错误总数 |
| **Gauges** | 可增减的数值 | 当前活跃连接数、队列长度 |
| **Histograms** | 分布统计 | 请求耗时、数据源响应时间 |

#### 业务指标

- `anime_agent_requests_total` - 请求总数
- `anime_agent_errors_total` - 错误总数
- `anime_agent_request_duration_seconds` - 请求耗时分布
- `anime_agent_intent_parse_duration_seconds` - 意图解析耗时
- `anime_agent_data_source_duration_seconds` - 数据源响应时间
- `anime_agent_cache_hit_ratio` - 缓存命中率

#### 访问指标端点

```
GET /metrics
```

返回 Prometheus 格式的指标数据。

### 链路追踪 (`src/infrastructure/tracing/`)

分布式链路追踪，用于请求全链路可视化：

#### 追踪信息

每个请求生成唯一的 `trace_id`，记录：

- 用户查询内容
- 意图解析结果
- 参数提取结果
- 工具调用过程
- 数据源查询时间
- 最终响应内容

#### 使用方式

系统自动生成并追踪所有请求，流式响应中会返回 `trace_id`：

```json
{
  "type": "session",
  "session_id": "user_123",
  "trace_id": "trace_789",
  "thread_id": "conv_456"
}
```

### 异常处理体系 (`src/core/exceptions.py`)

完善的异常类型定义：

| 异常类型 | 说明 | HTTP 状态码 |
|----------|------|-------------|
| `AnimeAgentException` | 智能体基础异常 | 500 |
| `DataSourceException` | 数据源异常 | 503 |
| `IntentParseException` | 意图解析异常 | 400 |
| `ToolExecutionException` | 工具执行异常 | 500 |
| `SessionException` | 会话管理异常 | 500 |
| `ValidationException` | 参数验证异常 | 400 |

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

# 运行异步测试
pytest tests/ -v --asyncio-mode=auto
```

### 测试结构

| 文件 | 覆盖范围 |
|------|----------|
| `test_intent.py` | 意图分类、直接回复 |
| `test_intent_parser.py` | 意图解析器功能 |
| `test_tools.py` | LangChain Tools 功能 |
| `test_data_sources.py` | 数据源查询 |
| `test_data_sources_integration.py` | 数据源集成测试 |
| `test_metrics.py` | 监控指标采集 |
| `test_parameter_flow.py` | 参数流转测试 |
| `test_tracing.py` | 链路追踪功能 |

---

## API 接口说明

### 基础端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API 根路径，返回版本信息 |
| `/health` | GET | 健康检查 |
| `/metrics` | GET | Prometheus 监控指标 |

### 对话接口

#### 1. 非流式对话

```bash
POST /api/chat
Content-Type: application/json

{
  "query": "2026年4月有什么新番？",
  "user_id": "user_123",
  "session_id": "session_456",
  "thread_id": "thread_789"  // 可选，用于 Checkpoint 恢复
}
```

**响应：**
```json
{
  "response": "根据查询结果，2026年4月有以下新番...",
  "session_id": "session_456",
  "error": null
}
```

#### 2. 流式对话（SSE）

```bash
POST /api/chat/stream
Content-Type: application/json

{
  "query": "介绍一下葬送的芙莉莲",
  "user_id": "user_123",
  "session_id": "session_456",
  "thread_id": "thread_789"  // 可选，用于 Checkpoint 恢复
}
```

**流式响应格式：**

1. 会话信息（第一个 chunk）：
```json
{
  "type": "session",
  "session_id": "session_456",
  "trace_id": "trace_abc123",
  "thread_id": "thread_789"
}
```

2. 意图解析：
```json
{
  "type": "intent",
  "status": "done",
  "intent": "detail",
  "params": {
    "keyword": "葬送的芙莉莲"
  }
}
```

3. 执行计划：
```json
{
  "type": "plan",
  "status": "done",
  "plan": ["get_anime_detail"]
}
```

4. 工具执行：
```json
{
  "type": "execution",
  "status": "done",
  "results": [
    {
      "tool": "get_anime_detail",
      "success": true,
      "data": {...}
    }
  ]
}
```

5. 增量输出：
```json
{
  "type": "output",
  "status": "streaming",
  "delta": "《葬送的芙莉莲》是..."
}
```

6. 完成信号：
```json
{
  "type": "done",
  "chunk_count": 15
}
```

### 请求参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 用户查询内容 |
| `user_id` | string | ❌ | 用户 ID，默认 "default" |
| `session_id` | string | ❌ | 会话 ID，用于 SessionManager |
| `thread_id` | string | ❌ | 线程 ID，用于 LangGraph Checkpoint 恢复对话状态 |

### 错误响应格式

```json
{
  "code": 500,
  "message": "服务器内部错误，请稍后重试",
  "error_type": "INTERNAL_ERROR",
  "data": null
}
```

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

### Q4: 如何启用多轮对话？

多轮对话功能通过 LangGraph Checkpoint 实现，需要配置存储后端：

```env
# .env 配置
CHECKPOINT_ENABLE=true
CHECKPOINT_BACKEND=redis  # 或 memory

# Redis 配置（如果使用 Redis）
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=anime_agent:
REDIS_TTL=86400
```

然后在请求中传递 `thread_id` 参数：

```javascript
// 前端示例
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: userMessage,
    session_id: sessionId,
    thread_id: threadId  // 保存并复用此 ID
  })
});
```

### Q5: Redis Checkpoint 连接失败

如果 Redis Checkpoint 初始化失败，系统会自动回退到内存存储。检查：

1. Redis 服务是否运行：`redis-cli ping`
2. Redis URL 配置是否正确：`REDIS_URL=redis://localhost:6379/0`
3. 网络连接是否正常

### Q6: 如何查看监控指标？

访问指标端点：

```bash
curl http://localhost:8000/metrics
```

或使用 Prometheus 抓取：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'anime_agent'
    static_configs:
      - targets: ['localhost:8000']
```

### Q7: 如何追踪请求链路？

每个请求会生成唯一的 `trace_id`，流式响应的第一个 chunk 会返回：

```json
{
  "type": "session",
  "trace_id": "trace_abc123"
}
```

使用此 `trace_id` 可以在日志中查找完整的请求链路记录。

---

## 相关文档

### 快速开始
- [快速启动指南](./quickstart.md)
- [Agent 架构文档](./agent.md)
- [MiniMax 使用手册](./minimax使用手册.md)

### 开发指南
- [智能体开发流程指南](./docs/智能体开发流程指南.md)
- [垂域智能体标准化开发流程文档](./docs/垂域智能体标准化开发流程文档.md)

### 功能说明
- [短期记忆增强（多轮对话优化）实现说明](./docs/短期记忆增强（多轮对话优化）实现说明.md)
- [番剧智能体监控指标与参数追踪完善方案](./docs/番剧智能体监控指标与参数追踪完善方案.md)
- [番剧智能体意图识别修改方案](./docs/番剧智能体意图识别修改方案.md)
- [前端渲染和短期记忆问题分析与解决方案](./docs/前端渲染和短期记忆问题分析与解决方案.md)

### 数据源相关
- [番剧信息来源说明文档](./docs/番剧信息来源说明文档.md)
- [百度搜索 API 调用说明手册](./docs/百度搜索api调用说明手册.md)
- [企业级番剧数据源服务设计方案](./docs/企业级番剧数据源服务设计方案.md)

### 企业级规划
- [番剧智能体企业级完善规划方案](./docs/番剧智能体企业级完善规划方案.md)
