# Checkpoint 从 memory 升级到 Redis 迁移指南

## 1. 适用场景

当前使用 `CHECKPOINT_BACKEND=memory`，出现以下情况建议升级 Redis：

- 多实例下会话经常丢失
- 对话需要跨重启保留
- 需要更稳定的多轮上下文

## 2. 变更原则

- 只改环境变量，尽量不改业务代码
- 灰度发布，先 Preview 再 Production
- 保留回滚开关（可快速切回 memory）

## 3. 环境变量调整

将以下变量配置到 Vercel：

```env
ENABLE_CHECKPOINT=true
CHECKPOINT_BACKEND=redis
REDIS_URL=redis://<host>:6379/0
CHECKPOINT_KEY_PREFIX=langgraph:
CHECKPOINT_TTL=86400
```

## 4. 依赖确认

项目需安装 Redis checkpointer 依赖（若未安装）：

```bash
pip install langgraph-checkpoint-redis
```

并同步到 `requirements.txt`。

## 5. 发布步骤

1. 在 Preview 环境配置 Redis 变量并部署。
2. 执行接口验证：
   - `/health/detail` 查看 `checkpoint_backend=redis`
   - 同一 `thread_id` 连续三轮对话，确认上下文连续
3. 观察错误率和延迟后，再推广到 Production。

## 6. 回滚策略

若 Redis 不稳定，立即切回：

```env
CHECKPOINT_BACKEND=memory
```

重新部署后恢复当前行为（短期记忆，可能丢失）。

