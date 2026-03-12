# agent/agent.py
"""ReAct 动态规划 Agent - 真正的AI智能体

使用 ReAct (Reasoning + Acting) 模式：
1. thought: LLM 思考当前状态
2. action: 下一步要做什么
3. action_input: 行动参数
4. observation: 执行结果
5. 重复直到 finished=true

支持多平台查询和结果评估重试机制
"""

import os
import json
import re
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .tools import create_tools
from ..llm.prompts import SYSTEM_PROMPT

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AnimeAgent")


class ReActAgent:
    """ReAct 动态规划 Agent
    
    工作流程：
    1. 意图分析：判断用户问题是否与番剧相关
    2. 工具选择：选择合适的工具和参数
    3. 执行评估：检查结果质量
    4. 重试优化：根据评估调整策略
    5. 回复生成：基于满意结果生成回复
    """
    
    # 系统提示词（ReAct 模式）- 增强版
    REACT_SYSTEM_PROMPT = """## 角色
你是一个专业的番剧智能助手，负责回答用户关于番剧的问题。

## 数据源（重要！）
你有以下数据源：
1. **Jikan API** - 基于 MyAnimeList，全球最大的动漫数据库
   - 英文名称为主，支持关键词搜索
   - 数据全面，评分权威
   - **使用 keyword 参数搜索特定番剧**
   - 平台标识: "Jikan"

2. **Bangumi API** - 番组计划，中文社区
   - 中文名称为主
   - 有中文用户评分
   - 平台标识: "Bangumi"

3. **Web Search** - 百度搜索（最后的 fallback）
   - 当数据库无法找到结果时使用
   - 可以搜索互联网获取信息

**重要**：你现在使用 platform 参数来选择数据源：
- platform="jikan": 只查询 Jikan
- platform="bangumi": 只查询 Bangumi  
- platform="all": 同时查询两个数据源（默认）

## 可用工具

### 1. query_anime（番剧查询）- 最重要！
用于查询番剧列表：
- time_range: 时间范围，支持格式：
  - "2025-01" 或 "2025年1月" → 查询2025年冬季番剧
  - "2025夏" / "2025夏季" → 查询2025年夏季番剧
  - "2025" → 查询2025年所有番剧
  - "本月" 或 "最新" → 查询当前季度番剧
- platform: 平台选择 - **关键参数！**
  - "jikan": 只查 Jikan (MyAnimeList)
  - "bangumi": 只查 Bangumi
  - "all": 同时查询两个平台（**默认**）
- anime_type: 类型，如 "日漫"、"国漫"、"all"（默认）
- sort_by: 排序，如 "latest"（最新）、"hot"（热门）、"rating"（评分）
- **keyword**: 关键词搜索，如番剧名称 "違国日記"、"葬送的芙莉莲"
  - **当用户询问特定番剧时，必须使用 keyword 参数！**

### 2. get_anime_detail（番剧详情）
用于获取特定番剧的详细信息：
- anime_id: 番剧ID（从查询结果中获取）

### 3. get_anime_ranking（排行榜）
用于获取番剧排行榜：
- time_range: 时间范围
- platform: 平台
- anime_type: 类型
- sort_by: 排序方式（rating/hot）

### 4. web_search（网页搜索）- **最后的 fallback！**
当数据库查询失败或结果不满意时使用：
- query: 搜索关键词，如 "違国日記 剧情介绍"
- 这是最后手段，先尝试 query_anime！

## 工作流程

### 第一步：尝试数据库查询
- 用户询问特定番剧 → 使用 query_anime + keyword 参数
- 用户询问时间范围 → 使用 query_anime + time_range 参数
- 优先查询 "all" 平台

### 第二步：评估结果
- 如果数据库返回空或不匹配：
  - 尝试切换 platform（如从 all 切换到 jikan）
  - 尝试调整 keyword 或 time_range
- **如果所有数据库尝试都失败**，进入第三步

### 第三步：使用 Web Search（最后 fallback）
- 当数据库无法找到答案时
- 使用 web_search 搜索互联网
- 从搜索结果中提取信息回答用户

## 输出格式

```json
{
  "thought": "分析用户问题和当前状态，包括对上次结果/错误的分析",
  "action": "工具名称或 'respond'",
  "action_input": {"参数名": "参数值"},
  "observation": "上一步的执行结果摘要",
  "finished": false或true,
  "response": "最终回复（finished为true时）"
}
```

## 重要规则

1. **关键词搜索优先**：当用户询问特定番剧时（如"《xxx》讲了什么"），必须使用 keyword 参数！

2. **fallback 策略**：
   - 先尝试 query_anime（所有平台）
   - 如果失败，尝试调整参数
   - 最后才使用 web_search

3. **数据源说明**：
   - 返回结果中可以看到数据来自哪个平台
   - Jikan 数据通常有英文名，Bangumi 有中文名
   - 评分可能不同，这是正常的

4. **禁止事项**：
   - 禁止编造番剧信息
   - 数据库查询失败时，必须尝试 web_search 作为 fallback

开始解决问题吧！"""
    
    def __init__(self, verbose: bool = True, max_iterations: int = 5):
        """初始化 Agent
        
        Args:
            verbose: 是否输出详细日志
            max_iterations: 最大迭代次数
        """
        self.verbose = verbose
        self.max_iterations = max_iterations  # 降低最大迭代次数
        
        # 创建 LLM（MiniMax 兼容 OpenAI 接口）
        self.llm = ChatOpenAI(
            model=os.getenv("ORCH_MODEL", "MiniMax/MiniMax-M2.5"),
            temperature=0.7,
            max_tokens=2000,
            streaming=True,
            base_url=os.getenv("ORCH_API_BASE"),
            api_key=os.getenv("ORCH_API_KEY")
        )
        
        # 创建 Tools
        self.tools = create_tools()
        
        # 创建工具名称到工具的映射
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 系统消息
        self.system_message = SystemMessage(content=self.REACT_SYSTEM_PROMPT)
        
        # 记录思考过程
        self.thought_history = []
        
        if self.verbose:
            logger.info("🤖 ReAct Agent 初始化完成")
            logger.info(f"可用工具: {list(self.tool_map.keys())}")
            logger.info(f"最大迭代次数: {self.max_iterations}")
    
    def _log(self, message: str, level: str = "info"):
        """输出日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        if self.verbose:
            print(f"[Agent] {message}")
        getattr(logger, level)(message)
    
    def _parse_react_output(self, content: str) -> dict:
        """解析 ReAct 格式的输出"""
        
        # 清理内容
        content = content.strip()
        
        # 尝试直接解析
        try:
            result = json.loads(content)
            if "thought" in result or "action" in result:
                return result
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                result = json.loads(json_str)
                if "thought" in result or "action" in result:
                    return result
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 返回默认格式（认为不需要工具）
        return {
            "thought": content[:100] if content else "无法解析响应",
            "action": "respond",
            "action_input": {},
            "observation": "",
            "finished": True,
            "response": content
        }
    
    def _evaluate_result(self, result: str, params: dict, user_input: str) -> dict:
        """评估工具返回结果的质量
        
        Returns:
            dict: {
                "count": 结果数量,
                "time_match": 是否时间匹配,
                "platforms": 涉及的平台列表,
                "needs_retry": 是否需要重试,
                "retry_reason": 重试原因,
                "suggested_params": 建议的重试参数
            }
        """
        
        quality = {
            "count": 0,
            "time_match": True,
            "platforms": [],
            "needs_retry": False,
            "retry_reason": "",
            "suggested_params": dict(params)
        }
        
        # 解析结果
        try:
            data = json.loads(result)
            if isinstance(data, list):
                items = data
                quality["count"] = len(items)
                
                # 分析平台
                platforms = set()
                time_set = set()
                for item in items:
                    anime_id = item.get("id", "")
                    if anime_id.startswith("bilibili_"):
                        platforms.add("bilibili")
                    elif anime_id.startswith("bgm_"):
                        platforms.add("bangumi")
                    
                    # 检查时间
                    air_date = item.get("播出时间", item.get("air_date", ""))
                    if air_date:
                        time_set.add(air_date[:7])  # 取年月
                
                quality["platforms"] = list(platforms)
                
                # 检查时间匹配
                user_time = params.get("time_range", "")
                if user_time and len(user_time) >= 4:  # 有年份信息
                    # 用户指定了时间
                    user_time_clean = user_time.replace("-", "").replace("年", "").replace("月", "")
                    if len(user_time_clean) >= 6:
                        user_year_month = user_time_clean[:6]
                        if user_year_month not in time_set:
                            quality["time_match"] = False
                
                # 评估是否需要重试
                if quality["count"] < 1:  # 要求至少1条结果
                    quality["needs_retry"] = True
                    quality["retry_reason"] = f"结果为空（{quality['count']}条），尝试其他平台或调整参数"
                    
                    # 建议重试参数
                    current_platform = params.get("platform", "all")
                    if current_platform == "all":
                        # 尝试 Bilibili
                        quality["suggested_params"]["platform"] = "bilibili"
                    elif current_platform == "bilibili":
                        # 尝试 Bangumi
                        quality["suggested_params"]["platform"] = "bangumi"
                    elif current_platform == "bangumi":
                        # 尝试不指定平台（all）
                        quality["suggested_params"]["platform"] = "all"
                    else:
                        quality["suggested_params"]["platform"] = "all"
                        
                elif not quality["time_match"]:
                    quality["needs_retry"] = True
                    quality["retry_reason"] = "时间不匹配，尝试查找相近时间的番剧"
                    # 保持原参数，让AI决定如何调整
                    
        except json.JSONDecodeError:
            # 无法解析，假设需要重试
            quality["needs_retry"] = True
            quality["retry_reason"] = "无法解析结果，可能查询失败"
        
        return quality
    
    def _build_context(self, user_input: str) -> str:
        """构建上下文信息"""
        
        context_parts = []
        
        # 添加思考历史
        if self.thought_history:
            context_parts.append("## 思考历史\n")
            for i, thought in enumerate(self.thought_history):
                context_parts.append(f"### 步骤 {i+1}")
                context_parts.append(f"- thought: {thought.get('thought', '')}")
                context_parts.append(f"- action: {thought.get('action', '')}")
                context_parts.append(f"- action_input: {thought.get('action_input', {})}")
                context_parts.append(f"- observation: {thought.get('observation', '')}")
                context_parts.append("")
        
        # 添加当前问题
        context_parts.append(f"## 当前问题\n{user_input}\n")
        
        return "\n".join(context_parts)
    
    async def run_streaming(self, user_input: str, chat_history: list = None):
        """运行 Agent（流式输出）- ReAct 模式
        
        Args:
            user_input: 用户输入
            chat_history: 对话历史
            
        Yields:
            流式输出的内容块，包含类型信息
        """
        
        # 重置思考历史
        self.thought_history = []
        
        max_iterations = self.max_iterations  # 使用实例变量
        iteration = 0
        
        self._log(f"🎯 开始处理用户问题: {user_input}")
        
        # 首先进行意图分析
        intent_analysis = f"""请分析以下用户问题是否与番剧相关：

用户问题: {user_input}

如果是番剧相关问题，请继续规划查询步骤。
如果不是，请直接回复，说明您只能回答番剧相关问题。

请输出 JSON 格式的思考结果："""
        
        messages = [
            self.system_message,
            HumanMessage(content=intent_analysis)
        ]
        
        # 获取意图分析结果
        intent_content = ""
        try:
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    intent_content += chunk.content
        except Exception as e:
            self._log(f"❌ 意图分析出错: {str(e)}", "error")
            yield {"type": "error", "content": f"意图分析出错: {str(e)}"}
            return
        
        # 解析意图分析
        intent_result = self._parse_react_output(intent_content)
        
        if "番剧" not in intent_content and "动漫" not in intent_content and "动画" not in intent_content:
            # 简单检查是否为非番剧问题
            if not any(keyword in user_input for keyword in ["番剧", "动漫", "动画", "日本", "新番", "动画片", "动漫片"]):
                self._log(f"🚫 非番剧相关问题，直接回复限制说明")
                yield {
                    "type": "output", 
                    "content": "抱歉，我只能回答与番剧（动漫/动画）相关的问题。您问的是关于番剧的问题吗？"
                }
        
        while iteration < max_iterations:
            iteration += 1
            
            self._log(f"📝 第 {iteration} 步思考...")
            
            # 构建提示词
            context = self._build_context(user_input)
            prompt = f"""请分析以下问题，并决定下一步行动：

{context}

请输出 JSON 格式的思考结果："""
            
            messages = [
                self.system_message,
                HumanMessage(content=prompt)
            ]
            
            # 获取 LLM 响应
            thought_content = ""
            try:
                async for chunk in self.llm.astream(messages):
                    if chunk.content:
                        thought_content += chunk.content
            except Exception as e:
                self._log(f"❌ LLM 调用出错: {str(e)}", "error")
                yield {"type": "error", "content": f"思考过程出错: {str(e)}"}
                return
            
            # 解析响应
            react_result = self._parse_react_output(thought_content)
            
            # 记录思考历史
            self.thought_history.append(react_result)
            
            # 输出思考过程
            thought = react_result.get("thought", "")
            action = react_result.get("action", "respond")
            action_input = react_result.get("action_input", {})
            observation = react_result.get("observation", "")
            finished = react_result.get("finished", False)
            final_response = react_result.get("response", "")
            
            self._log(f"💭 thought: {thought[:100]}...")
            self._log(f"⚡ action: {action}")
            self._log(f"📥 action_input: {action_input}")
            
            # 输出思考过程到前端
            yield {
                "type": "thinking",
                "content": {
                    "step": iteration,
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "observation": observation[:200] + "..." if len(observation) > 200 else observation
                }
            }
            
            # 检查是否完成
            if finished:
                self._log(f"✅ 问题已解决")
                if final_response:
                    yield {"type": "output", "content": "\n" + final_response}
                break
            
            # 执行行动
            if action == "respond":
                # 直接回复
                self._log(f"✅ 问题已解决（直接回复）")
                yield {"type": "output", "content": "\n" + thought}
                break
            
            elif action in self.tool_map:
                # 调用工具
                tool = self.tool_map[action]
                tool_name = action
                
                self._log(f"🔧 执行工具: {tool_name}")
                self._log(f"📋 参数: {action_input}")
                
                # 通知正在执行
                yield {"type": "tool", "content": f"🔧 正在调用 {tool_name}..."}
                
                try:
                    # 执行工具
                    if hasattr(tool, '_arun'):
                        result = await tool._arun(**action_input)
                    else:
                        result = tool._run(**action_input)
                    
                    # 记录原始结果
                    original_result = result
                    
                    self._log(f"📊 工具返回结果: {result[:200]}..." if len(result) > 200 else f"📊 工具返回结果: {result}")
                    
                    # ========== 自动结果评估 ==========
                    quality = self._evaluate_result(result, action_input, user_input)
                    
                    self._log(f"📈 结果评估: 数量={quality['count']}, 时间匹配={quality['time_match']}, 平台={quality['platforms']}")
                    
                    # 更新观察结果（供 LLM 参考，但由 LLM 自主决定下一步）
                    react_result["observation"] = result
                    react_result["result_quality"] = quality
                    self.thought_history[-1] = react_result
                    
                    # 输出工具结果
                    yield {"type": "tool_result", "content": result[:500] + "..." if len(result) > 500 else result}
                    
                    # 注意：移除自动重试逻辑，由 LLM 自主决定下一步行动
                    # LLM 会根据 result_quality 和观察到的结果自主规划重试策略
                    
                except Exception as e:
                    error_msg = f"❌ 工具执行出错: {str(e)}"
                    self._log(error_msg, "error")
                    yield {"type": "error", "content": error_msg}
                    
                    # 记录错误
                    react_result["observation"] = f"执行出错: {str(e)}"
                    self.thought_history[-1] = react_result
            else:
                # 未知行动
                self._log(f"⚠️ 未知行动: {action}", "warning")
                yield {"type": "thinking", "content": {"thought": f"未知行动: {action}，将直接回复"}}
                yield {"type": "output", "content": "\n" + thought}
                break
        
        if iteration >= max_iterations:
            self._log(f"⚠️ 达到最大迭代次数 {max_iterations}", "warning")
            yield {
                "type": "output", 
                "content": "\n抱歉，我已经尽力了，但暂时无法找到您想要的番剧信息。您可以尝试换个时间范围或番剧类型查询。"
            }
    
    def run(self, user_input: str, chat_history: list = None) -> str:
        """运行 Agent（非流式）- 收集所有输出"""
        
        # 收集所有输出
        outputs = []
        
        async def collect():
            async for chunk in self.run_streaming(user_input, chat_history):
                if chunk.get("type") == "output":
                    outputs.append(chunk.get("content", ""))
                elif chunk.get("type") == "thinking":
                    # 处理思考过程
                    pass
                elif chunk.get("type") == "tool_result":
                    # 处理工具结果
                    pass
        
        import asyncio
        asyncio.run(collect())
        
        return "".join(outputs)


# 兼容旧接口
class AnimeAgent(ReActAgent):
    """AnimeAgent - 兼容旧接口"""
    pass


# 全局 Agent 实例
_agent = None

def get_agent(verbose: bool = True) -> ReActAgent:
    """获取全局 Agent 实例
    
    Args:
        verbose: 是否输出详细日志
    """
    global _agent
    if _agent is None:
        _agent = ReActAgent(verbose=verbose)
    return _agent


def run_agent(user_input: str, chat_history: list = None) -> str:
    """运行 Agent（非流式）"""
    agent = get_agent()
    return agent.run(user_input, chat_history)


async def run_agent_streaming(user_input: str, chat_history: list = None):
    """运行 Agent（流式输出）"""
    agent = get_agent()
    async for chunk in agent.run_streaming(user_input, chat_history):
        yield chunk
        """初始化 Agent
        
        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        
        # 创建 LLM（MiniMax 兼容 OpenAI 接口）
        self.llm = ChatOpenAI(
            model=os.getenv("ORCH_MODEL", "MiniMax/MiniMax-M2.5"),
            temperature=0.7,
            max_tokens=2000,
            streaming=True,
            base_url=os.getenv("ORCH_API_BASE"),
            api_key=os.getenv("ORCH_API_KEY")
        )
        
        # 创建 Tools
        self.tools = create_tools()
        
        # 创建工具名称到工具的映射
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 系统消息
        self.system_message = SystemMessage(content=self.REACT_SYSTEM_PROMPT)
        
        # 记录思考过程
        self.thought_history = []
        
        if self.verbose:
            logger.info("🤖 ReAct Agent 初始化完成")
            logger.info(f"可用工具: {list(self.tool_map.keys())}")
    
    def _log(self, message: str, level: str = "info"):
        """输出日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        if self.verbose:
            print(f"[Agent] {message}")
        getattr(logger, level)(message)
    
    def _parse_react_output(self, content: str) -> dict:
        """解析 ReAct 格式的输出"""
        
        # 清理内容
        content = content.strip()
        
        # 尝试直接解析
        try:
            result = json.loads(content)
            if "thought" in result or "action" in result:
                return result
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                result = json.loads(json_str)
                if "thought" in result or "action" in result:
                    return result
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 返回默认格式（认为不需要工具）
        return {
            "thought": content[:100] if content else "无法解析响应",
            "action": "respond",
            "action_input": {},
            "observation": "",
            "finished": True,
            "response": content
        }
    
    def _evaluate_result(self, result: str, params: dict, user_input: str) -> dict:
        """评估工具返回结果的质量
        
        Returns:
            dict: {
                "count": 结果数量,
                "time_match": 是否时间匹配,
                "platforms": 涉及的平台列表,
                "needs_retry": 是否需要重试,
                "retry_reason": 重试原因,
                "suggested_params": 建议的重试参数
            }
        """
        
        quality = {
            "count": 0,
            "time_match": True,
            "platforms": [],
            "needs_retry": False,
            "retry_reason": "",
            "suggested_params": dict(params)
        }
        
        # 解析结果
        try:
            data = json.loads(result)
            if isinstance(data, list):
                items = data
                quality["count"] = len(items)
                
                # 分析平台
                platforms = set()
                time_set = set()
                for item in items:
                    anime_id = item.get("id", "")
                    if anime_id.startswith("bilibili_"):
                        platforms.add("bilibili")
                    elif anime_id.startswith("bgm_"):
                        platforms.add("bangumi")
                    
                    # 检查时间
                    air_date = item.get("播出时间", item.get("air_date", ""))
                    if air_date:
                        time_set.add(air_date[:7])  # 取年月
                
                quality["platforms"] = list(platforms)
                
                # 检查时间匹配
                user_time = params.get("time_range", "")
                if user_time and len(user_time) >= 4:  # 有年份信息
                    # 用户指定了时间
                    user_time_clean = user_time.replace("-", "").replace("年", "").replace("月", "")
                    if len(user_time_clean) >= 6:
                        user_year_month = user_time_clean[:6]
                        if user_year_month not in time_set:
                            quality["time_match"] = False
                
                # 评估是否需要重试
                if quality["count"] < 1:  # 要求至少1条结果
                    quality["needs_retry"] = True
                    quality["retry_reason"] = f"结果为空（{quality['count']}条），尝试其他平台或调整参数"
                    
                    # 建议重试参数
                    current_platform = params.get("platform", "all")
                    if current_platform == "all":
                        # 尝试 Bilibili
                        quality["suggested_params"]["platform"] = "bilibili"
                    elif current_platform == "bilibili":
                        # 尝试 Bangumi
                        quality["suggested_params"]["platform"] = "bangumi"
                    elif current_platform == "bangumi":
                        # 尝试不指定平台（all）
                        quality["suggested_params"]["platform"] = "all"
                    else:
                        quality["suggested_params"]["platform"] = "all"
                        
                elif not quality["time_match"]:
                    quality["needs_retry"] = True
                    quality["retry_reason"] = "时间不匹配，尝试查找相近时间的番剧"
                    # 保持原参数，让AI决定如何调整
                    
        except json.JSONDecodeError:
            # 无法解析，假设需要重试
            quality["needs_retry"] = True
            quality["retry_reason"] = "无法解析结果，可能查询失败"
        
        return quality
    
    def _build_context(self, user_input: str) -> str:
        """构建上下文信息"""
        
        context_parts = []
        
        # 添加思考历史
        if self.thought_history:
            context_parts.append("## 思考历史\n")
            for i, thought in enumerate(self.thought_history):
                context_parts.append(f"### 步骤 {i+1}")
                context_parts.append(f"- thought: {thought.get('thought', '')}")
                context_parts.append(f"- action: {thought.get('action', '')}")
                context_parts.append(f"- action_input: {thought.get('action_input', {})}")
                context_parts.append(f"- observation: {thought.get('observation', '')}")
                context_parts.append("")
        
        # 添加当前问题
        context_parts.append(f"## 当前问题\n{user_input}\n")
        
        return "\n".join(context_parts)
    
    async def run_streaming(self, user_input: str, chat_history: list = None):
        """运行 Agent（流式输出）- ReAct 模式
        
        Args:
            user_input: 用户输入
            chat_history: 对话历史
            
        Yields:
            流式输出的内容块，包含类型信息
        """
        
        # 重置思考历史
        self.thought_history = []
        
        max_iterations = 10  # 最大迭代次数
        iteration = 0
        
        self._log(f"🎯 开始处理用户问题: {user_input}")
        
        while iteration < max_iterations:
            iteration += 1
            
            self._log(f"📝 第 {iteration} 步思考...")
            
            # 构建提示词
            context = self._build_context(user_input)
            prompt = f"""请分析以下问题，并决定下一步行动：

{context}

请输出 JSON 格式的思考结果："""
            
            messages = [
                self.system_message,
                HumanMessage(content=prompt)
            ]
            
            # 获取 LLM 响应
            thought_content = ""
            try:
                async for chunk in self.llm.astream(messages):
                    if chunk.content:
                        thought_content += chunk.content
            except Exception as e:
                self._log(f"❌ LLM 调用出错: {str(e)}", "error")
                yield {"type": "error", "content": f"思考过程出错: {str(e)}"}
                return
            
            # 解析响应
            react_result = self._parse_react_output(thought_content)
            
            # 记录思考历史
            self.thought_history.append(react_result)
            
            # 输出思考过程
            thought = react_result.get("thought", "")
            action = react_result.get("action", "respond")
            action_input = react_result.get("action_input", {})
            observation = react_result.get("observation", "")
            finished = react_result.get("finished", False)
            final_response = react_result.get("response", "")
            
            self._log(f"💭 thought: {thought[:100]}...")
            self._log(f"⚡ action: {action}")
            self._log(f"📥 action_input: {action_input}")
            
            # 输出思考过程到前端
            yield {
                "type": "thinking",
                "content": {
                    "step": iteration,
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "observation": observation[:200] + "..." if len(observation) > 200 else observation
                }
            }
            
            # 检查是否完成
            if finished:
                self._log(f"✅ 问题已解决")
                if final_response:
                    yield {"type": "output", "content": "\n" + final_response}
                break
            
            # 执行行动
            if action == "respond":
                # 直接回复
                self._log(f"✅ 问题已解决（直接回复）")
                yield {"type": "output", "content": "\n" + thought}
                break
            
            elif action in self.tool_map:
                # 调用工具
                tool = self.tool_map[action]
                tool_name = action
                
                self._log(f"🔧 执行工具: {tool_name}")
                self._log(f"📋 参数: {action_input}")
                
                # 通知正在执行
                yield {"type": "tool", "content": f"🔧 正在调用 {tool_name}..."}
                
                try:
                    # 执行工具
                    if hasattr(tool, '_arun'):
                        result = await tool._arun(**action_input)
                    else:
                        result = tool._run(**action_input)
                    
                    # 记录原始结果
                    original_result = result
                    
                    self._log(f"📊 工具返回结果: {result[:200]}..." if len(result) > 200 else f"📊 工具返回结果: {result}")
                    
                    # ========== 自动结果评估 ==========
                    quality = self._evaluate_result(result, action_input, user_input)
                    
                    self._log(f"📈 结果评估: 数量={quality['count']}, 时间匹配={quality['time_match']}, 平台={quality['platforms']}")
                    
                    # 更新观察结果
                    react_result["observation"] = result
                    react_result["result_quality"] = quality
                    self.thought_history[-1] = react_result
                    
                    # 输出工具结果
                    yield {"type": "tool_result", "content": result[:500] + "..." if len(result) > 500 else result}
                    
                    # 注意：移除自动重试逻辑，由 LLM 自主决定下一步行动
                    
                except Exception as e:
                    error_msg = f"❌ 工具执行出错: {str(e)}"
                    self._log(error_msg, "error")
                    yield {"type": "error", "content": error_msg}
                    
                    # 记录错误
                    react_result["observation"] = f"执行出错: {str(e)}"
                    self.thought_history[-1] = react_result
            else:
                # 未知行动
                self._log(f"⚠️ 未知行动: {action}", "warning")
                yield {"type": "thinking", "content": {"thought": f"未知行动: {action}，将直接回复"}}
                yield {"type": "output", "content": "\n" + thought}
                break
        
        if iteration >= max_iterations:
            self._log(f"⚠️ 达到最大迭代次数 {max_iterations}", "warning")
            yield {"type": "output", "content": "\n抱歉，我已经尽力了，但问题比较复杂，我们可以换个话题试试？"}
    
    def run(self, user_input: str, chat_history: list = None) -> str:
        """运行 Agent（非流式）- 收集所有输出"""
        
        # 收集所有输出
        outputs = []
        
        async def collect():
            async for chunk in self.run_streaming(user_input, chat_history):
                if chunk.get("type") == "output":
                    outputs.append(chunk.get("content", ""))
                elif chunk.get("type") == "thinking":
                    # 处理思考过程
                    pass
                elif chunk.get("type") == "tool_result":
                    # 处理工具结果
                    pass
        
        import asyncio
        asyncio.run(collect())
        
        return "".join(outputs)


# 兼容旧接口
class AnimeAgent(ReActAgent):
    """AnimeAgent - 兼容旧接口"""
    pass


# 全局 Agent 实例
_agent = None

def get_agent(verbose: bool = True) -> ReActAgent:
    """获取全局 Agent 实例
    
    Args:
        verbose: 是否输出详细日志
    """
    global _agent
    if _agent is None:
        _agent = ReActAgent(verbose=verbose)
    return _agent


def run_agent(user_input: str, chat_history: list = None) -> str:
    """运行 Agent（非流式）"""
    agent = get_agent()
    return agent.run(user_input, chat_history)


async def run_agent_streaming(user_input: str, chat_history: list = None):
    """运行 Agent（流式输出）"""
    agent = get_agent()
    async for chunk in agent.run_streaming(user_input, chat_history):
        yield chunk