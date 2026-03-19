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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AnimeAgent")


# ==================== 意图类型定义 ====================

class IntentType:
    """意图类型常量"""
    GREETING = "greeting"           # 打招呼
    CAPABILITY = "capability"       # 询问能力
    QUERY = "query"                 # 番剧查询
    DETAIL = "detail"               # 番剧详情
    RANKING = "ranking"             # 排行榜
    RECOMMEND = "recommend"         # 推荐
    COMPARE = "compare"             # 对比
    THANKS = "thanks"               # 感谢
    CHAT = "chat"                   # 闲聊


# ==================== 槽位定义 ====================

class SlotDefinition:
    """槽位定义 - 用于参数校验和反问"""
    
    # 槽位定义字典
    DEFINITIONS = {
        "time_range": {
            "type": "string",
            "required": False,
            "description": "时间范围",
            "examples": ["2026-03", "本月", "最新", "2026春", "2024年7月"],
            "validate": lambda x: _validate_time_range(x) if x else True
        },
        "platform": {
            "type": "string",
            "required": False,
            "description": "平台",
            "enum": ["jikan", "anilist", "bangumi", "all"],
            "default": "all"
        },
        "anime_type": {
            "type": "string",
            "required": False,
            "description": "番剧类型",
            "enum": ["日漫", "国漫", "美漫", "剧场版", "all"],
            "default": "all"
        },
        "sort_by": {
            "type": "string",
            "required": False,
            "description": "排序方式",
            "enum": ["latest", "hot", "rating"],
            "default": "rating"
        },
        "keyword": {
            "type": "string",
            "required": False,
            "description": "关键词搜索"
        },
        "anime_id": {
            "type": "string",
            "required": False,
            "description": "番剧ID"
        }
    }
    
    # 意图必需的槽位
    REQUIRED_SLOTS = {
        IntentType.DETAIL: ["keyword", "anime_id"],  # 详情需要关键词或ID
        IntentType.QUERY: [],  # 查询可选
        IntentType.RANKING: [],  # 排行榜可选
    }


def _validate_time_range(value: str) -> bool:
    """验证时间范围格式"""
    import re
    # 简单验证：年份+月份、季节、本月、最新等
    patterns = [
        r"^\d{4}-\d{2}$",  # 2026-03
        r"^\d{4}年\d{1,2}月$",  # 2026年3月
        r"^\d{4}春|夏|秋|冬$",  # 2026春
        r"^本月$",
        r"^最新$",
        r"^最近$"
    ]
    return any(re.match(p, value) for p in patterns)


# ==================== 意图解析器 ====================

class IntentParser:
    """意图解析器
    
    负责分析用户问题，提取关键信息：
    - 意图类型
    - 查询参数（时间、平台、类型、关键词等）
    """
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        IntentType.GREETING: ["你好", "hi", "hello", "嗨", "早上好", "晚安", "在吗"],
        IntentType.CAPABILITY: ["功能", "能做什么", "有什么用", "你可以"],
        IntentType.THANKS: ["谢谢", "感谢", "好的"],
        IntentType.QUERY: ["查询", "搜索", "找找", "有哪些", "有什么", "推荐"],
        IntentType.RANKING: ["排行", "排名", "top", "最火", "最热", "最高分"],
        IntentType.DETAIL: ["详情", "介绍", "讲什么", "剧情", "怎么样"]
    }
    
    # 时间关键词映射
    TIME_KEYWORDS = {
        "本月": "本月",
        "最新": "最新",
        "最近": "最新",
        "春季": "春",
        "夏季": "夏",
        "秋季": "秋",
        "冬季": "冬"
    }
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def validate_slots(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """校验槽位并返回校验结果
        
        Returns:
            {
                "valid": True/False,
                "errors": ["错误信息"],
                "missing_slots": ["缺失的必需槽位"],
                "corrected_params": 纠正后的参数
            }
        """
        errors = []
        missing_slots = []
        corrected_params = params.copy()
        
        # 获取意图必需的槽位
        required = SlotDefinition.REQUIRED_SLOTS.get(intent, [])
        
        # 检查必需槽位
        for slot_name in required:
            if slot_name not in params or not params.get(slot_name):
                missing_slots.append(slot_name)
        
        # 校验各槽位
        for slot_name, value in params.items():
            if slot_name in SlotDefinition.DEFINITIONS:
                slot_def = SlotDefinition.DEFINITIONS[slot_name]
                
                # 枚举校验
                if "enum" in slot_def and value:
                    if value not in slot_def["enum"]:
                        errors.append(f"{slot_def['description']} '{value}' 不在可选值 {slot_def['enum']} 中")
                        # 纠正为默认值
                        corrected_params[slot_name] = slot_def.get("default", "all")
                
                # 自定义校验
                if "validate" in slot_def and value:
                    if not slot_def["validate"](value):
                        errors.append(f"{slot_def['description']} '{value}' 格式不正确")
        
        # 返回校验结果
        return {
            "valid": len(errors) == 0 and len(missing_slots) == 0,
            "errors": errors,
            "missing_slots": missing_slots,
            "corrected_params": corrected_params
        }
    
    def generate_clarification_question(self, missing_slots: List[str], params: Dict[str, Any]) -> str:
        """生成澄清问题
        
        根据缺失的槽位生成反问用户的问题
        """
        questions = []
        
        for slot in missing_slots:
            if slot == "keyword" or slot == "anime_id":
                questions.append("请告诉我你想查询的番剧名称")
            elif slot == "time_range":
                questions.append("你想查询哪个时间段的番剧？如2026年3月、本月、最新的等")
            elif slot == "platform":
                questions.append("你想在哪个平台查看？如B站、Bangumi等")
            elif slot == "anime_type":
                questions.append("你想看什么类型的番剧？如日漫、国漫、剧场版等")
        
        if questions:
            return "，" .join(questions)
        return ""
    
    async def parse(self, user_input: str, context_text: str = "") -> Dict[str, Any]:
        """解析用户意图
        
        Args:
            user_input: 用户输入
            context_text: 会话上下文文本
            
        Returns:
            {
                "intent": "query",
                "params": {
                    "time_range": "2026-03",
                    "platform": "all",
                    "anime_type": "all",
                    "keyword": "xxx"
                },
                "needs_data": True,
                "direct_response": None
            }
        """
        # 1. 快速关键词匹配
        intent = self._quick_match(user_input)
        
        # 2. 如果是直接回复类型，直接返回
        if intent in [IntentType.GREETING, IntentType.CAPABILITY, IntentType.THANKS]:
            return {
                "intent": intent,
                "params": {},
                "needs_data": False,
                "direct_response": self._get_direct_response(intent)
            }
        
        # 3. 使用LLM提取查询参数（传入上下文）
        params = await self._extract_params(user_input, intent, context_text)
        
        # 4. 判断是否需要获取数据
        needs_data = intent in [IntentType.QUERY, IntentType.DETAIL, IntentType.RANKING]
        
        return {
            "intent": intent,
            "params": params,
            "needs_data": needs_data,
            "direct_response": None
        }
    
    def _quick_match(self, user_input: str) -> str:
        """快速关键词匹配"""
        query_lower = user_input.lower()
        
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent_type
        
        return IntentType.QUERY  # 默认查询
    
    async def _extract_params(
        self, 
        user_input: str, 
        intent: str, 
        context_text: str = ""
    ) -> Dict[str, Any]:
        """使用LLM提取查询参数（非流式）
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            context_text: 会话上下文
        """
        # 构建上下文提示
        context_hint = ""
        if context_text:
            context_hint = f"""
## 历史上下文（参考）
{context_text}

注意：如果用户问题很简短（如"这些的评分呢？"），请结合历史上下文推断参数！"""
        
        prompt = f"""分析用户问题，提取查询参数。

用户问题: {user_input}
意图类型: {intent}{context_hint}

重要规则：
- 如果用户提到"国漫"、"国产动画"、"国产动漫"，必须设置 anime_type = "国漫"
- 如果用户提到"日漫"、"日本动画"，设置 anime_type = "日漫"
- 如果用户提到"剧场版"、"电影"，设置 anime_type = "剧场版"

请输出JSON格式的参数：
{{
    "time_range": "时间范围，如'2026-03'、'本月'、'最新'、'2026春'（可选）",
    "platform": "平台选择：'all'默认，'jikan'、'bangumi'、'bilibili'（可选）",
    "anime_type": "类型：必填！'all'默认，'日漫'、'国漫'、'剧场版'",
    "sort_by": "排序：'rating'评分，'hot'热门，'latest'最新（可选）",
    "keyword": "关键词搜索（可选）"
}}

只输出JSON，不要其他内容："""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ]
        
        try:
            response = await self.llm.agenerate([messages])
            content = response.generations[0][0].text
            
            logger.info(f"📝 [IntentParser] LLM返回的参数: {content}")
            
            # 解析JSON
            params = self._parse_json(content)
            
            if not params:
                logger.warning(f"⚠️ [IntentParser] 参数解析失败，返回空字典")
                logger.warning(f"   原始内容: {content[:200]}")
            
            logger.info(f"🎯 [IntentParser] 解析后的参数: {params}")
            return params if params else {}
        except Exception as e:
            logger.warning(f"参数提取失败: {e}")
            return {}

    async def astream_extract_params(
        self, 
        user_input: str, 
        intent: str,
        context_text: str = ""
    ):
        """使用LLM流式提取查询参数 - 每次 LLM 输出 chunk 时立即 yield
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            context_text: 会话上下文
        """
        # 构建上下文提示
        context_hint = ""
        if context_text:
            context_hint = f"""
## 历史上下文（参考）
{context_text}

注意：如果用户问题很简短（如"这些的评分呢？"），请结合历史上下文推断参数！"""
        
        prompt = f"""分析用户问题，提取查询参数。

用户问题: {user_input}
意图类型: {intent}{context_hint}

重要规则：
- 如果用户提到"国漫"、"国产动画"、"国产动漫"，必须设置 anime_type = "国漫"
- 如果用户提到"日漫"、"日本动画"，设置 anime_type = "日漫"
- 如果用户提到"剧场版"、"电影"，设置 anime_type = "剧场版"

请输出JSON格式的参数：
{{
    "time_range": "时间范围，如'2026-03'、'本月'、'最新'、'2026春'（可选）",
    "platform": "平台选择：'all'默认，'jikan'、'bangumi'、'bilibili'（可选）",
    "anime_type": "类型：必填！'all'默认，'日漫'、'国漫'、'剧场版'",
    "sort_by": "排序：'rating'评分，'hot'热门，'latest'最新（可选）",
    "keyword": "关键词搜索（可选）"
}}

只输出JSON，不要其他内容："""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ]
        
        full_content = ""
        try:
            # 使用 astream 实现真正的流式输出
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    full_content += chunk.content
                    yield chunk.content
            
            # 解析JSON
            params = self._parse_json(full_content)
            if params:
                yield json.dumps(params, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"参数提取失败: {e}")
            yield f"[解析失败: {e}]"
    
    def _parse_json(self, content: str) -> Dict:
        """解析JSON"""
        try:
            # 尝试直接解析
            return json.loads(content)
        except:
            # 尝试提取JSON块
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return {}
    
    def _get_direct_response(self, intent: str) -> str:
        """获取直接回复"""
        responses = {
            IntentType.GREETING: "你好！我是番剧智能助手，专注于帮助你了解日本动画番剧的相关信息。有什么番剧想了解的吗？",
            IntentType.CAPABILITY: """我可以帮助你：
1. 📋 查询番剧信息 - 根据时间、类型、平台搜索番剧
2. 📖 了解番剧详情 - 获取特定番剧的剧情介绍
3. 🔥 查看热门排行 - 了解当前最受欢迎的番剧
4. 🔍 关键词搜索 - 搜索特定番剧信息

请告诉我你想了解什么？""",
            IntentType.THANKS: "不客气！很高兴能帮到你。还有什么想了解的吗？"
        }
        return responses.get(intent, "你好！有什么可以帮你的？")


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
        user_id: str = "default"
    ):
        """运行智能体（增量流式输出）- 支持会话上下文
        
        Args:
            user_input: 用户输入
            chat_history: 聊天历史（兼容旧接口）
            session_id: 会话 ID（可选）
            user_id: 用户 ID（可选）
        """
        # 获取或创建会话
        session = None
        context_text = ""
        
        if self._session_manager and session_id:
            session = self._session_manager.get_session(session_id)
            if session:
                # 获取会话上下文
                max_turns = 5
                if CONFIG_AVAILABLE and settings:
                    max_turns = settings.max_conversation_turns
                context_text = session.get_context_text(max_turns)
                logger.info(f"📜 会话上下文: {len(context_text)} 字符")
        
        # 记录用户查询
        chat_logger.log_user_query(user_input)
        
        # 如果有会话，添加用户消息
        if session:
            self._session_manager.add_user_message(session.session_id, user_input)
        
        self._log(f"🎯 开始处理: {user_input}")
        
        # ========== 第一步：意图解析（真正流式） ==========
        yield {"type": "intent", "status": "parsing", "delta": "分析用户意图..."}
        
        # 快速关键词匹配意图
        intent = self.intent_parser._quick_match(user_input)
        
        # 记录意图
        chat_logger.log_intent(intent, {})
        
        # 增量发送意图类型
        yield {"type": "intent", "status": "parsing", "intent_delta": intent}
        
        # 如果是直接回复类型，直接返回
        if intent in [IntentType.GREETING, IntentType.CAPABILITY, IntentType.THANKS]:
            direct_response = self.intent_parser._get_direct_response(intent)
            yield {"type": "intent", "status": "done", "intent": intent, "params": {}, "needs_data": False}
            
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
        async for param_chunk in self.intent_parser.astream_extract_params(user_input, intent, context_text):
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
        
        self._log(f"🎯 意图识别: {intent}, 参数: {params}")
        
        # 记录意图
        chat_logger.log_intent(intent, params)
        
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
                    
                    yield {"type": "intent", "status": "done", "intent": intent, "params": params, "needs_data": False, "clarification": clarification}
                    
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
        
        # 意图完成
        yield {"type": "intent", "status": "done", "intent": intent, "params": params, "needs_data": needs_data}
        
        # ========== 第三步：生成计划（真正流式） ==========
        yield {"type": "plan", "status": "planning", "delta": "生成执行计划..."}
        
        plan = await self.planner.plan(intent, params)
        
        self._log(f"📋 执行计划: {plan}")
        
        # 增量发送计划
        for step in plan:
            step_info = f"使用工具: {step.get('tool')}, 参数: {step.get('params')}"
            yield {"type": "plan", "status": "planning", "plan_delta": step_info}
        # 计划完成
        yield {"type": "plan", "status": "done", "plan": plan}
        
        # ========== 第四步：执行工具（增量） ==========
        yield {"type": "execution", "status": "executing", "delta": "开始执行工具..."}
        
        results = await self.executor.execute(plan)
        
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
        
        # ========== 第五步：生成响应（真正流式） ==========
        # 使用 astream_generate 实现真正的流式输出
        # 每次 LLM 输出一个 chunk 就立即 yield 发送给前端
        full_response = ""
        async for chunk in self.response_generator.astream_generate(user_input, intent, results):
            full_response += chunk
            yield {"type": "output", "status": "streaming", "content_delta": chunk}
        
        # 记录响应
        chat_logger.log_response(full_response)
        
        # 如果有会话，添加助手消息
        if session:
            self._session_manager.add_assistant_message(session.session_id, full_response)
        
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
    user_id: str = "default"
):
    """运行Agent（流式输出）
    
    Args:
        user_input: 用户输入
        chat_history: 聊天历史（兼容旧接口）
        session_id: 会话 ID（支持多轮对话）
        user_id: 用户 ID
    """
    agent = get_agent()
    async for chunk in agent.run_streaming(user_input, chat_history, session_id, user_id):
        yield chunk


# 兼容旧接口
class ReActAgent(AnimeAgent):
    """ReActAgent - 兼容旧接口"""
    pass
