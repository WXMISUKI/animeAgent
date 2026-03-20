# agent/agent.py
"""智能体核心模块 - 支持意图解析和计划生成

架构：
1. IntentParser - 意图解析：分析用户问题，确定意图类型和参数
2. Planner - 计划生成：生成执行计划，决定使用哪些工具
3. Executor - 执行器：按计划执行工具
4. ResponseGenerator - 响应生成：生成最终回复
"""

import os
import json
import re
import logging
import asyncio
from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .tools import create_tools
from ..utils.logger import chat_logger

# 导入意图解析模块（解耦后的新模块）
from .intent import IntentParser, IntentType, SlotDefinition

# 导入会话管理（新增）
try:
    from ..infrastructure.cache import get_session_manager
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    logging.warning("会话管理器不可用，将使用无状态模式")

# 导入配置（新增）
try:
    from ..core.config import settings
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    settings = None

# 导入追踪模块
try:
    from ..infrastructure.tracing import get_tracer, create_tracing_context
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AnimeAgent")


# ==================== 意图解析器 ====================

# 注意：IntentParser 类已移至 src/agent/intent/parser.py
# 从模块导入: from .intent import IntentParser, IntentType, SlotDefinition


# ==================== 计划生成器 ====================

# ==================== 计划生成器 ====================

class Planner:
    """计划生成器
    
    根据意图生成执行计划：
    - 需要调用的工具
    - 工具调用顺序
    - 参数配置
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    async def plan(self, intent: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成执行计划
        
        Returns:
            [
                {"tool": "query_anime", "params": {...}},
                {"tool": "get_anime_detail", "params": {...}}
            ]
        """
        # 根据意图类型生成计划
        if intent == IntentType.QUERY:
            return [self._plan_query(params)]
        elif intent == IntentType.DETAIL:
            return [self._plan_detail(params)]
        elif intent == IntentType.RANKING:
            return [self._plan_ranking(params)]
        elif intent == IntentType.RECOMMEND:
            # 推荐意图也使用查询工具，sort_by 默认为 rating（推荐按评分）
            return [self._plan_recommend(params)]
        else:
            return []  # 无需工具
    
    def _plan_query(self, params: Dict) -> Dict:
        """查询计划"""
        return {
            "tool": "query_anime",
            "params": {
                "time_range": params.get("time_range"),
                "platform": params.get("platform", "all"),
                "anime_type": params.get("anime_type", "all"),
                "sort_by": params.get("sort_by", "rating"),
                "keyword": params.get("keyword")
            }
        }
    
    def _plan_detail(self, params: Dict) -> Dict:
        """详情计划"""
        # 如果有关键词，先查询获取ID
        if params.get("keyword"):
            return {
                "tool": "query_anime",
                "params": {
                    "keyword": params.get("keyword"),
                    "platform": params.get("platform", "all")
                }
            }
        else:
            return {
                "tool": "get_anime_detail",
                "params": {
                    "anime_id": params.get("anime_id", "")
                }
            }
    
    def _plan_ranking(self, params: Dict) -> Dict:
        """排行榜计划"""
        return {
            "tool": "get_anime_ranking",
            "params": {
                "time_range": params.get("time_range"),
                "platform": params.get("platform", "all"),
                "anime_type": params.get("anime_type", "all"),
                "sort_by": params.get("sort_by", "rating")
            }
        }
    
    def _plan_recommend(self, params: Dict) -> Dict:
        """推荐计划
        
        推荐意图本质上也是查询，使用 query_anime 工具
        但 sort_by 默认为 rating（按评分推荐）
        """
        return {
            "tool": "query_anime",
            "params": {
                "time_range": params.get("time_range") or "最新",  # 推荐近期番剧
                "platform": params.get("platform", "all"),
                "anime_type": params.get("anime_type", "all"),
                "sort_by": params.get("sort_by", "rating"),  # 按评分推荐
                "keyword": params.get("keyword")
            }
        }


# ==================== 执行器 ====================

class Executor:
    """执行器
    
    负责执行工具并返回结果
    """
    
    def __init__(self, tool_map: Dict):
        self.tool_map = tool_map
    
    async def execute(self, plan: List[Dict]) -> List[Dict]:
        """执行计划
        
        Returns:
            [
                {"tool": "query_anime", "success": True, "result": ...},
                {"tool": "get_anime_detail", "success": False, "error": ...}
            ]
        """
        results = []
        
        for step in plan:
            tool_name = step.get("tool")
            tool_params = step.get("params", {})
            
            if tool_name not in self.tool_map:
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": f"未知工具: {tool_name}"
                })
                continue
            
            tool = self.tool_map[tool_name]
            
            try:
                # 执行工具
                if hasattr(tool, '_arun'):
                    result = await tool._arun(**tool_params)
                else:
                    result = tool._run(**tool_params)
                
                results.append({
                    "tool": tool_name,
                    "success": True,
                    "result": result,
                    "params": tool_params
                })
                
                # 记录日志
                chat_logger.log_tool_call(tool_name, tool_params, result[:200] if result else "")
                
            except Exception as e:
                error_msg = str(e)
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": error_msg,
                    "params": tool_params
                })
                
                # 记录错误日志
                chat_logger.log_error(error_msg, {"tool": tool_name})
        
        return results


# ==================== 响应生成器 ====================

class ResponseStyle:
    """响应风格"""
    CONCISE = "concise"      # 简洁
    DETAILED = "detailed"   # 详细
    CASUAL = "casual"       # 口语化
    PROFESSIONAL = "professional"  # 专业


class ResponseGenerator:
    """响应生成器 - 增强版
    
    特性：
    - 多风格响应（简洁/详细/口语化/专业）
    - 结果聚合去重
    - 个性化响应（基于会话上下文）
    """
    
    # 风格对应的 prompt
    STYLE_PROMPTS = {
        ResponseStyle.CONCISE: """请用简洁的方式回答，包含：
- 番剧名称
- 评分（如有）
- 数据来源（如：Bilibili、Jikan、Bangumi）
- 一句话介绍

重要：每条结果必须标注数据来源！""",
        
        ResponseStyle.DETAILED: """请用详细的方式回答，每部番剧包含：
- 番剧名称（原名）
- 评分和评价人数
- 播出时间
- 剧情简介（50字内）
- 标签
- 数据来源（必须标注：如 Bilibili、Jikan、Bangumi）
使用清晰的分隔符分隔每部番剧。

重要：每条结果必须标注数据来源！""",
        
        ResponseStyle.CASUAL: """请用轻松、口语化的方式回答，像朋友推荐一样：
- 用 emoji 让内容更生动
- 适当加入个人感受
- 语气亲切自然
- 不要太正式

重要：每条结果必须标注数据来源（如：📺 数据来源：Bilibili）！""",
        
        ResponseStyle.PROFESSIONAL: """请用专业、客观的方式回答：
- 使用规范的术语
- 数据准确引用
- 结构化呈现
- 适当加入数据对比

重要：必须标注每条结果的数据来源（Bilibili/Jikan/Bangumi/AniList）"""
    }
    
    def __init__(self, llm: ChatOpenAI, default_style: str = ResponseStyle.CASUAL):
        self.llm = llm
        self.default_style = default_style
    
    async def generate(
        self, 
        user_input: str, 
        intent: str, 
        tool_results: List[Dict],
        style: str = None
    ) -> str:
        """生成响应文本（非流式）
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            tool_results: 工具执行结果
            style: 响应风格（concise/detailed/casual/professional）
        """
        
        # 如果没有工具结果
        if not tool_results:
            return "抱歉，我没有找到相关信息。你可以换个关键词试试？"
        
        # 检查是否有成功的结果
        success_results = [r for r in tool_results if r.get("success")]
        
        if not success_results:
            return "抱歉，查询过程中出现了问题。请稍后重试。"
        
        # 收集结果数据
        results_data = []
        for r in success_results:
            if r.get("result"):
                try:
                    data = json.loads(r["result"])
                    if isinstance(data, list):
                        results_data.extend(data)
                    else:
                        results_data.append(data)
                except:
                    results_data.append(r.get("result"))
        
        # 获取风格提示
        response_style = style or self.default_style
        style_prompt = self.STYLE_PROMPTS.get(response_style, self.STYLE_PROMPTS[ResponseStyle.CASUAL])
        
        # 使用LLM生成自然语言回复
        prompt = f"""用户问题: {user_input}

番剧查询结果:
{json.dumps(results_data[:10], ensure_ascii=False, indent=2)}

{style_prompt}

注意：只输出回复内容，不要输出其他解释。"""

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            response = await self.llm.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            return f"我找到了相关信息，但回复生成有点问题。请查看以下结果：\n\n{results_data[:5]}"

    async def astream_generate(
        self, 
        user_input: str, 
        intent: str, 
        tool_results: List[Dict],
        style: str = None
    ):
        """异步流式生成响应 - 每次 LLM 输出 chunk 时立即 yield
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            tool_results: 工具执行结果
            style: 响应风格（concise/detailed/casual/professional）
        """
        
        # 如果没有工具结果
        if not tool_results:
            yield "抱歉，我没有找到相关信息。你可以换个关键词试试？"
            return
        
        # 检查是否有成功的结果
        success_results = [r for r in tool_results if r.get("success")]
        
        if not success_results:
            yield "抱歉，查询过程中出现了问题。请稍后重试。"
            return
        
        # 收集结果数据
        results_data = []
        for r in success_results:
            if r.get("result"):
                try:
                    data = json.loads(r["result"])
                    if isinstance(data, list):
                        results_data.extend(data)
                    else:
                        results_data.append(data)
                except:
                    results_data.append(r.get("result"))
        
        # 获取风格提示
        response_style = style or self.default_style
        style_prompt = self.STYLE_PROMPTS.get(response_style, self.STYLE_PROMPTS[ResponseStyle.CASUAL])
        
        # 使用LLM生成自然语言回复
        prompt = f"""用户问题: {user_input}

番剧查询结果:
{json.dumps(results_data[:10], ensure_ascii=False, indent=2)}

{style_prompt}

注意：只输出回复内容，不要输出其他解释。"""

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            # 使用 astream 方法实现真正的流式输出
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            yield f"我找到了相关信息，但回复生成有点问题。请查看以下结果：\n\n{results_data[:5]}"


# ==================== 智能体主类 ====================

class AnimeAgent:
    """番剧智能助手 - 新架构（支持会话记忆）
    
    工作流程：
    1. IntentParser - 意图解析（支持上下文）
    2. Planner - 计划生成
    3. Executor - 工具执行
    4. ResponseGenerator - 响应生成
    
    会话管理：
    - 支持多轮对话上下文
    - 会话数据存储在 Redis（如果可用）或内存
    - 自动管理会话生命周期
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        
        # 获取配置
        if CONFIG_AVAILABLE and settings:
            api_base = settings.orch_api_base
            api_key = settings.orch_api_key
            model = settings.orch_model
        else:
            api_base = os.getenv("ORCH_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            api_key = os.getenv("ORCH_API_KEY", "")
            model = os.getenv("ORCH_MODEL", "MiniMax/MiniMax-M2.5")
        
        # 创建LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            max_tokens=2000,
            streaming=True,
            base_url=api_base,
            api_key=api_key
        )
        
        # 创建组件
        self.intent_parser = IntentParser(self.llm)
        self.planner = Planner(self.llm)
        self.executor = Executor({tool.name: tool for tool in create_tools()})
        self.response_generator = ResponseGenerator(self.llm)
        
        # 初始化会话管理器（新增）
        self._session_manager = None
        if SESSION_MANAGER_AVAILABLE:
            try:
                self._session_manager = get_session_manager()
                logger.info("✅ 会话管理器已集成")
            except Exception as e:
                logger.warning(f"会话管理器初始化失败: {e}")
        
        if self.verbose:
            logger.info("🤖 AnimeAgent 初始化完成")
            logger.info(f"可用工具: {list(self.executor.tool_map.keys())}")
            logger.info(f"会话管理: {'已启用' if self._session_manager else '未启用'}")
    
    @property
    def session_manager(self):
        """获取会话管理器"""
        return self._session_manager
    
    async def run_streaming(
        self, 
        user_input: str, 
        chat_history: list = None,
        session_id: str = None,
        user_id: str = "default",
        trace_id: str = None
    ):
        """运行智能体（增量流式输出）- 支持会话上下文
        
        错误处理策略：
        1. 每个步骤都有独立的 try-except
        2. 异常不会中断整个流程，而是发送错误消息后继续
        3. 重要步骤失败会发送错误消息给前端
        
        Args:
            user_input: 用户输入
            chat_history: 聊天历史（兼容旧接口）
            session_id: 会话 ID（可选）
            user_id: 用户 ID（可选）
            trace_id: 追踪 ID（用于链路追踪）
        """
        # 获取或创建会话
        session = None
        context_text = ""
        
        try:
            if self._session_manager and session_id:
                session = self._session_manager.get_session(session_id)
                if session:
                    # 获取会话上下文
                    max_turns = 5
                    if CONFIG_AVAILABLE and settings:
                        max_turns = settings.max_conversation_turns
                    context_text = session.get_context_text(max_turns)
                    logger.info(f"📜 会话上下文: {len(context_text)} 字符")
        except Exception as e:
            logger.warning(f"获取会话上下文失败: {e}")
        
        # 记录用户查询
        try:
            chat_logger.log_user_query(user_input)
        except Exception as e:
            logger.warning(f"记录用户查询失败: {e}")
        
        # 如果有会话，添加用户消息
        if session:
            try:
                self._session_manager.add_user_message(session.session_id, user_input)
            except Exception as e:
                logger.warning(f"添加用户消息失败: {e}")
        
        self._log(f"🎯 开始处理: {user_input}")
        
        # ========== 第一步：意图解析（带错误处理） ==========
        yield {"type": "intent", "status": "parsing", "delta": "分析用户意图..."}
        
        try:
            # LLM意图识别（主要方式）+ 关键词兜底
            intent = await self.intent_parser._recognize_intent(user_input, context_text)
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            yield {"type": "error", "content": f"意图识别失败: {str(e)}"}
            # 使用默认意图继续
            intent = IntentType.QUERY
            intent_str = intent.value if hasattr(intent, 'value') else str(intent)
            yield {"type": "intent", "status": "error", "intent": intent_str, "params": {}, "needs_data": True}
        
        # 转换为字符串（IntentType枚举不能直接JSON序列化）
        intent_str = intent.value if hasattr(intent, 'value') else str(intent)
        
        # 记录意图
        try:
            chat_logger.log_intent(intent_str, {})
        except Exception as e:
            logger.warning(f"记录意图失败: {e}")
        
        # 增量发送意图类型
        yield {"type": "intent", "status": "parsing", "intent_delta": intent_str}
        
        # 如果是直接回复类型，直接返回
        direct_reply_intents = [
            IntentType.GREETING.value, 
            IntentType.DESCRIPTION.value,
            IntentType.CAPABILITY.value, 
            IntentType.THANKS.value,
            IntentType.UNKNOWN.value  # 新增：无法理解的输入
        ]
        if intent_str in direct_reply_intents:
            # 获取回复内容（分层策略）
            direct_response = self.intent_parser._get_direct_response(intent)
            
            # 如果返回 None，说明需要 LLM 生成复杂回复
            if direct_response is None:
                yield {"type": "intent", "status": "generating", "delta": "生成回复中..."}
                direct_response = await self.intent_parser._generate_complex_response(
                    intent_str, user_input, context_text
                )
            
            yield {"type": "intent", "status": "done", "intent": intent_str, "params": {}, "needs_data": False}
            
            # 直接回复（流式输出回复内容）
            chat_logger.log_response(direct_response)
            for i in range(0, len(direct_response), 20):
                yield {"type": "output", "status": "streaming", "content_delta": direct_response[i:i+20]}
            yield {"type": "output", "status": "done", "content": direct_response}
            
            # 如果有会话，添加助手消息
            if session:
                self._session_manager.add_assistant_message(session.session_id, direct_response)
            
            return
        
        # 使用流式 LLM 提取参数（传入上下文）
        params = {}
        full_params_text = ""
        async for param_chunk in self.intent_parser._astream_extract_params(user_input, intent, context_text):
            full_params_text += param_chunk
            yield {"type": "intent", "status": "parsing", "params_delta": param_chunk}
        
        # 解析最终的 JSON 参数
        if full_params_text:
            try:
                json_match = re.search(r'\{.*\}', full_params_text, re.DOTALL)
                if json_match:
                    params = json.loads(json_match.group())
            except:
                pass
        
        # 规则兜底：如果LLM提取失败或anime_type为空，使用规则匹配
        if not params or not params.get("anime_type") or params.get("anime_type") == "all":
            logger.info(f"⚠️ [IntentParser] 流式LLM参数提取不完整，使用规则兜底")
            rule_params = self.intent_parser._rule_based_extract(user_input)
            # 合并参数
            if params:
                for key, value in rule_params.items():
                    if not params.get(key) or params.get(key) == "all":
                        params[key] = value
            else:
                params = rule_params
        
        # 参数校验和纠正
        params = self.intent_parser._validate_and_correct_params(params)
        
        # 意图转字符串（确保是字符串而不是枚举对象）
        intent_str = intent.value if hasattr(intent, 'value') else str(intent)
        
        self._log(f"🎯 意图识别: {intent_str}, 参数: {params}")
        
        # 记录意图
        chat_logger.log_intent(intent_str, params)
        
        # 更新会话槽位（如果有会话）
        if session and params:
            self._session_manager.update_slots(session.session_id, params)
        
        # 判断是否需要获取数据（必须在槽位校验之前定义）
        needs_data = intent in [IntentType.QUERY, IntentType.DETAIL, IntentType.RANKING]
        
        # ========== 槽位校验（新增）==========
        # 如果需要数据，校验槽位
        validation_result = None
        if needs_data:
            validation_result = self.intent_parser.validate_slots(intent, params)
            
            # 如果校验失败，返回澄清问题
            if not validation_result["valid"]:
                # 使用纠正后的参数
                params = validation_result["corrected_params"]
                
                # 如果有缺失的必需槽位，生成反问
                if validation_result["missing_slots"]:
                    question = self.intent_parser.generate_clarification_question(
                        validation_result["missing_slots"],
                        params
                    )
                    clarification = f"好的，请帮你确认一下，{question}？"
                    intent_str = intent.value if hasattr(intent, 'value') else str(intent)
                    yield {"type": "intent", "status": "done", "intent": intent_str, "params": params, "needs_data": False, "clarification": clarification}
                    
                    # 输出澄清问题
                    chat_logger.log_response(clarification)
                    for i in range(0, len(clarification), 20):
                        yield {"type": "output", "status": "streaming", "content_delta": clarification[i:i+20]}
                    yield {"type": "output", "status": "done", "content": clarification}
                    
                    # 记录到会话
                    if session:
                        self._session_manager.add_assistant_message(session.session_id, clarification)
                    return
                
                # 如果有错误但非必需槽位缺失，记录警告
                if validation_result["errors"]:
                    logger.warning(f"槽位校验警告: {validation_result['errors']}")
        
        # 意图完成（转换为字符串）
        intent_str = intent.value if hasattr(intent, 'value') else str(intent)
        yield {"type": "intent", "status": "done", "intent": intent_str, "params": params, "needs_data": needs_data}
        
        # ========== 第三步：生成计划（带错误处理） ==========
        yield {"type": "plan", "status": "planning", "delta": "生成执行计划..."}
        
        try:
            plan = await self.planner.plan(intent, params)
        except Exception as e:
            logger.error(f"计划生成失败: {e}")
            yield {"type": "error", "content": f"生成执行计划失败: {str(e)}"}
            plan = []  # 使用空计划继续
        
        self._log(f"📋 执行计划: {plan}")
        
        # 增量发送计划
        for step in plan:
            step_info = f"使用工具: {step.get('tool')}, 参数: {step.get('params')}"
            yield {"type": "plan", "status": "planning", "plan_delta": step_info}
        # 计划完成
        yield {"type": "plan", "status": "done", "plan": plan}
        
        # ========== 第四步：执行工具（带错误处理） ==========
        yield {"type": "execution", "status": "executing", "delta": "开始执行工具..."}
        
        try:
            results = await self.executor.execute(plan)
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            yield {"type": "error", "content": f"执行工具失败: {str(e)}"}
            results = []
        
        # 检查执行结果
        success_count = sum(1 for r in results if r.get("success"))
        self._log(f"✅ 工具执行完成: {success_count}/{len(results)} 成功")
        
        # 增量发送执行结果
        for i, result in enumerate(results):
            tool_name = result.get("tool", "unknown")
            if result.get("success"):
                result_preview = str(result.get("result", ""))[:100]
                yield {"type": "execution", "status": "executing", "exec_delta": f"✅ {tool_name} 执行成功: {result_preview}..."}
            else:
                error = result.get("error", "未知错误")
                yield {"type": "execution", "status": "executing", "exec_delta": f"❌ {tool_name} 执行失败: {error}"}
        
        # 执行完成
        yield {"type": "execution", "status": "done", "results": results}
        
        # ========== 第五步：生成响应（带错误处理） ==========
        # 使用 astream_generate 实现真正的流式输出
        # 每次 LLM 输出一个 chunk 就立即 yield 发送给前端
        full_response = ""
        
        try:
            async for chunk in self.response_generator.astream_generate(user_input, intent, results):
                full_response += chunk
                yield {"type": "output", "status": "streaming", "content_delta": chunk}
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            yield {"type": "error", "content": f"生成回复失败: {str(e)}"}
            # 尝试生成降级响应
            if results:
                full_response = "抱歉，回复生成出现了一些问题。以下是查询结果：\n\n"
                for r in results:
                    if r.get("success"):
                        full_response += f"- {r.get('result', '无结果')[:200]}\n"
            else:
                full_response = "抱歉，服务暂时不可用，请稍后重试。"
            yield {"type": "output", "status": "streaming", "content_delta": full_response}
        
        # 记录响应
        try:
            chat_logger.log_response(full_response)
        except Exception as e:
            logger.warning(f"记录响应失败: {e}")
        
        # 如果有会话，添加助手消息
        if session:
            try:
                self._session_manager.add_assistant_message(session.session_id, full_response)
            except Exception as e:
                logger.warning(f"添加助手消息失败: {e}")
        
        # 回复完成
        yield {"type": "output", "status": "done", "content": full_response}
    
    def run(
        self, 
        user_input: str, 
        chat_history: list = None,
        session_id: str = None,
        user_id: str = "default"
    ) -> str:
        """运行智能体（非流式）
        
        Args:
            user_input: 用户输入
            chat_history: 聊天历史（兼容旧接口）
            session_id: 会话 ID
            user_id: 用户 ID
        """
        
        outputs = []
        
        async def collect():
            async for chunk in self.run_streaming(user_input, chat_history, session_id, user_id):
                if chunk.get("type") == "output":
                    outputs.append(chunk.get("content", ""))
        
        asyncio.run(collect())
        
        return "".join(outputs)
    
    def _log(self, message: str):
        """日志输出"""
        if self.verbose:
            print(f"[Agent] {message}")
        logger.info(message)


# ==================== 便捷函数 ====================

_agent = None

def get_agent(verbose: bool = True) -> AnimeAgent:
    """获取全局Agent实例"""
    global _agent
    if _agent is None:
        _agent = AnimeAgent(verbose=verbose)
    return _agent


def run_agent(
    user_input: str, 
    chat_history: list = None,
    session_id: str = None,
    user_id: str = "default"
) -> str:
    """运行Agent（非流式）
    
    Args:
        user_input: 用户输入
        chat_history: 聊天历史（兼容旧接口）
        session_id: 会话 ID（支持多轮对话）
        user_id: 用户 ID
    """
    agent = get_agent()
    return agent.run(user_input, chat_history, session_id, user_id)


async def run_agent_streaming(
    user_input: str, 
    chat_history: list = None,
    session_id: str = None,
    user_id: str = "default",
    trace_id: str = None
):
    """运行Agent（流式输出）
    
    Args:
        user_input: 用户输入
        chat_history: 聊天历史（兼容旧接口）
        session_id: 会话 ID（支持多轮对话）
        user_id: 用户 ID
        trace_id: 追踪 ID（用于链路追踪）
    """
    agent = get_agent()
    async for chunk in agent.run_streaming(user_input, chat_history, session_id, user_id, trace_id):
        yield chunk


# 兼容旧接口
class ReActAgent(AnimeAgent):
    """ReActAgent - 兼容旧接口"""
    pass
