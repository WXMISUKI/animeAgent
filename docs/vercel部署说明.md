# Vercel 部署说明（前后端同项目）

## 1. 目标架构

- 单一 Vercel 项目部署
- `frontend/` 托管静态页面
- 根目录 `index.py` 承载 FastAPI（Serverless Function）
- API 通过同域路径访问：`/api/*`

## 2. 关键文件清单

| 文件 | 用途 |
|------|------|
| `index.py` | Vercel Python 入口，暴露 `src.main:app` |
| `.python-version` | 固定 Python 运行时版本为 `3.12` |
| `pyproject.toml` | Python 项目元数据与依赖声明（Vercel uv 构建必需） |
| `uv.lock` | 依赖锁定文件（Vercel uv 构建必需） |
| `vercel.json` | 路由规则配置 |
| `.vercelignore` | 排除不需要部署的文件 |
| `frontend/` | 前端静态资源 |
| `requirements.txt` | 传统依赖清单（本地开发 pip 安装用，保留兼容） |

## 3. Vercel 项目配置步骤

1. 在 Vercel 导入当前仓库（Root 保持仓库根目录）。
2. Framework Preset 选择 `Other`。
3. Build Command 留空（静态 + Serverless 无需额外构建）。
4. Output Directory 留空。

5. 在 Environment Variables 配置：

```env
# 必需
ORCH_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
ORCH_MODEL=MiniMax/MiniMax-M2.5
ORCH_API_KEY=你的密钥

# 可选
BAIDU_SEARCH_API_KEY=你的密钥
LOG_LEVEL=INFO
CACHE_TTL=3600

# CORS（填写你的 Vercel 域名）
CORS_ALLOW_ORIGINS=https://your-app.vercel.app

# API 鉴权（生产环境建议开启）
API_AUTH_ENABLED=true
API_AUTH_KEY=你的高强度密钥
API_AUTH_HEADER=x-api-key

# Checkpoint
ENABLE_CHECKPOINT=true
CHECKPOINT_BACKEND=memory
CHECKPOINT_THRESHOLD=1
CHECKPOINT_MAX_HISTORY=20
```

## 4. 技术说明

### Python 运行时

- Vercel 当前支持 Python 3.12 / 3.13 / 3.14。
- 通过 `.python-version` 指定版本为 `3.12`。
- Vercel 使用 `uv` 包管理器，构建时执行 `uv sync --locked`。
- 必须同时提供 `pyproject.toml` 和 `uv.lock`。

### 依赖变更维护流程

```bash
# 1. 编辑 pyproject.toml 中的 dependencies
# 2. 重新生成锁定文件
uv lock
# 3. 同步更新 requirements.txt（保持一致）
# 4. 提交 pyproject.toml、uv.lock、requirements.txt
```

## 5. 路由设计

| 路径 | 目标 |
|------|------|
| `/api/*` | `index.py`（FastAPI） |
| `/health` | `index.py` |
| `/health/detail` | `index.py` |
| `/metrics` | `index.py` |
| `/chat` | `index.py` |
| `/chat/stream` | `index.py` |
| 其他路径 | `frontend/*`（静态资源） |

前端使用 `window.location.origin` 作为 API Base，避免跨域。

## 6. API 鉴权

- `/api/*` 和 `/chat*` 路径受 API Key 中间件保护。
- 开启方式：`API_AUTH_ENABLED=true` 且配置 `API_AUTH_KEY`。
- 请求头默认 `x-api-key`，可通过 `API_AUTH_HEADER` 修改。
- 本地开发默认关闭（`API_AUTH_ENABLED=false`）。

## 7. 流式接口策略

- 优先调用 `/api/chat/stream`（SSE）。
- 若网络、超时或平台限制导致流式失败，前端自动回退到 `/api/chat`。
- Serverless `maxDuration` 默认 60 秒，控制单次请求复杂度避免超时。

## 8. 内存 Checkpoint 的限制（当前阶段）

- 会话状态不保证持久化。
- 函数实例重启、扩缩容后上下文可能丢失。
- 仅适合作为"无外部依赖"的上线过渡方案。

建议后续升级：接入 Redis（如 Upstash）后将 `CHECKPOINT_BACKEND` 切到 `redis`。

## 9. 生产注意事项

1. **日志**：Vercel 为无状态环境，本地持久化不可依赖。生产建议接入外部日志系统。
2. **CORS**：通过 `CORS_ALLOW_ORIGINS` 配置生产域名白名单，多个域名用逗号分隔。
3. **不要在 Vercel 使用本地地址**（如 `http://localhost:8000`）作为任何外部服务 URL。
4. `.env` 不会自动上传到 Vercel，必须在控制台配置环境变量。

## 10. 验证清单

1. 访问 `/health` 返回 `status=ok`
2. 访问 `/health/detail`，确认 `env.all_required_ready=true`
3. 访问 `/metrics` 可返回 Prometheus 文本
4. 首页可打开并发送消息
5. `/api/chat/stream` 正常输出，异常时自动降级到 `/api/chat`
6. 同一会话内短期多轮对话可用（允许偶发丢失）

## 11. 后续升级

如需稳定多轮记忆，请参考：

- [Checkpoint 从 memory 升级到 Redis 迁移指南](./checkpoint从memory升级redis迁移指南.md)
