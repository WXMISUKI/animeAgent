# 番剧智能体 - 快速启动指南

当前项目开发环境我们有自己的开发环境，直接执行 `conda activate myenv`

## 项目简介

基于豆包大模型的番剧信息查询智能体，提供 Web 界面和 API 接口。

## 部署到 Vercel

请优先参考文档：[docs/vercel部署说明.md](./docs/vercel部署说明.md)
Redis 升级参考：[docs/checkpoint从memory升级redis迁移指南.md](./docs/checkpoint从memory升级redis迁移指南.md)

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | 豆包大模型 (火山引擎 Ark) |
| 后端框架 | FastAPI + LangGraph |
| 前端 | HTML + CSS + JavaScript |
| 数据源 | Jikan + AniList + Bangumi + Bilibili + 百度搜索 |

## 快速启动

### 1. 环境准备

```bash
# 使用已有 conda 环境
conda activate myenv

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
# 豆包配置（必需）
ORCH_API_BASE=https://ark.cn-beijing.volces.com/api/v3
ORCH_MODEL=your-doubao-endpoint-id
ORCH_API_KEY=your-ark-api-key

# 日志配置（可选）
LOG_LEVEL=INFO
CACHE_TTL=3600
```

### 3. 启动服务

#### 终端1：启动后端 API

```bash
conda activate myenv
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
├── index.py                # Vercel Python 入口
├── pyproject.toml           # 依赖声明（Vercel uv 构建用）
├── uv.lock                  # 依赖锁定文件
├── vercel.json              # Vercel 路由配置
├── requirements.txt         # Python 依赖（本地 pip 用）
├── src/                    # 后端源码
│   ├── main.py            # FastAPI 入口
│   ├── agent/             # Agent 编排
│   ├── skills/            # 技能模块
│   ├── llm/               # LLM 客户端
│   ├── data_sources/      # 数据源
│   └── models/            # 数据模型
├── public/                # 前端页面（Vercel 部署用，自动托管）
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── frontend/              # 前端页面（本地开发用）
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── tests/                 # 测试代码
```

## 常见问题

### Q1: API 调用失败

**检查 .env 文件是否正确配置：**
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ORCH_API_KEY'))"
```

### Q2: 前端无法连接后端

确保后端在 8000 端口运行。前端本地开发时自动将 API 请求指向 `http://localhost:8000`。

### Q3: 如何获取豆包 API Key

1. 访问火山引擎 Ark：https://console.volcengine.com/ark
2. 注册/登录账号
3. 创建模型接入点，获取 Endpoint ID 和 API Key
4. 将 Endpoint ID 填入 `ORCH_MODEL`，API Key 填入 `ORCH_API_KEY`

## 技术支持

- 火山引擎 Ark 文档：https://www.volcengine.com/docs/82379
- FastAPI 文档：https://fastapi.tiangolo.com/zh/
- LangGraph 文档：https://langchain-ai.github.io/langgraph/

---

**版本**: v3.0
**更新日期**: 2026-05-04
