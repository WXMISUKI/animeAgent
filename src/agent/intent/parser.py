"""意图解析器 - 核心实现

支持两种模式：
1. Legacy 模式：原有的解析逻辑
2. Agent 模式：使用专门的 IntentAgent 智能体（推荐）

建议：生产环境使用 Agent 模式
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .types import IntentType, IntentTypeConfig
from .slots import SlotDefinition
from .prompts import IntentPrompts

logger = logging.getLogger("IntentParser")


class IntentParser:
    """意图解析器 - 增强版
    
    负责分析用户问题，提取关键信息：
    - 意图类型
    - 查询参数（时间、平台、类型、关键词等）
    
    特性：
    - 支持两种模式：Legacy（原有） / Agent（智能体模式）
    - Few-Shot Prompt 示例
    - 规则兜底机制
    - 参数自动校验纠正
    
    使用建议：
    - use_agent=True: 使用专门的 IntentAgent（企业级推荐）
    - use_agent=False: 使用原有解析逻辑（保持兼容）
    """
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        IntentType.GREETING: ["你好", "hi", "hello", "嗨", "早上好", "晚安", "在吗"],
        IntentType.DESCRIPTION: ["你是谁", "你叫什么", "介绍一下", "介绍自己", "你是什么", "身份"],
        IntentType.CAPABILITY: ["功能", "能做什么", "会什么", "你可以", "能干嘛", "有什么用"],
        IntentType.THANKS: ["谢谢", "感谢", "好的"],
        IntentType.QUERY: ["查询", "搜索", "找找", "有哪些", "有什么", "推荐"],
        IntentType.RANKING: ["排行", "排名", "top", "最火", "最热", "最高分"],
        IntentType.DETAIL: ["详情", "介绍", "讲什么", "剧情", "怎么样"]
    }
    
    # 注意：不再使用正则匹配判断无意义输入
    # 完全由LLM判断意图，包括"无法理解"的情况
    
    def __init__(self, llm: ChatOpenAI, use_agent: bool = True):
        """初始化意图解析器
        
        Args:
            llm: LLM客户端实例
            use_agent: 是否使用 IntentAgent 智能体模式（推荐设置为True）
        """
        self.llm = llm
        self.use_agent = use_agent
        
        # 延迟导入 IntentAgent，避免循环依赖
        self._intent_agent = None
        
        if use_agent:
            try:
                from .agent import IntentAgent
                self._intent_agent = IntentAgent(llm)
                logger.info("✅ [IntentParser] 使用 IntentAgent 智能体模式")
            except ImportError as e:
                logger.warning(f"⚠️ [IntentParser] 无法导入 IntentAgent，回退到 Legacy 模式: {e}")
                self.use_agent = False
    
    @property
    def intent_agent(self):
        """获取 IntentAgent 实例（延迟加载）"""
        if self._intent_agent is None and self.use_agent:
            from .agent import IntentAgent
            self._intent_agent = IntentAgent(self.llm)
        return self._intent_agent
    
    # ==================== 公开方法 ====================
    
    async def parse(self, user_input: str, context_text: str = "") -> Dict[str, Any]:
        """解析用户意图（主入口）
        
        根据配置选择解析模式：
        - Agent模式（推荐）：使用专门的 IntentAgent 智能体
          - 置信度评估
          - 自反思机制
          - 更准确的意图识别
        - Legacy模式：使用原有的解析逻辑
        
        Args:
            user_input: 用户输入
            context_text: 会话上下文文本
            
        Returns:
            {
                "intent": "query",
                "params": {...},
                "needs_data": True,
                "direct_response": None,
                "confidence": "high"  # 仅Agent模式有
            }
        """
        # Agent模式：使用专门的意图识别智能体
        if self.use_agent and self.intent_agent:
            return await self.intent_agent.recognize(user_input, context_text)
        
        # Legacy模式：使用原有解析逻辑
        return await self._legacy_parse(user_input, context_text)
    
    async def _legacy_parse(self, user_input: str, context_text: str = "") -> Dict[str, Any]:
        """Legacy解析模式（原有逻辑，保持兼容）
        
        采用分层策略：
        1. LLM意图识别（主要方式）
        2. 关键词兜底（LLM失败时）
        3. 参数提取
        
        Args:
            user_input: 用户输入
            context_text: 会话上下文文本
            
        Returns:
            {
                "intent": "query",
                "params": {...},
                "needs_data": True,
                "direct_response": None
            }
        """
        # ========== 步骤1: LLM意图识别（主方式）==========
        intent = await self._recognize_intent(user_input, context_text)
        
        # ========== 步骤2: 如果是直接回复类型，直接返回 ==========
        if intent in IntentTypeConfig.DIRECT_REPLY:
            return {
                "intent": intent,
                "params": {},
                "needs_data": False,
                "direct_response": IntentPrompts.get_direct_response(intent)
            }
        
        # ========== 步骤3: 使用LLM提取查询参数 ==========
        params = await self._extract_params(user_input, intent, context_text)
        
        # ========== 步骤4: 规则兜底：如果LLM提取失败或anime_type为空 ==========
        if not params or not params.get("anime_type") or params.get("anime_type") == "all":
            logger.info(f"⚠️ [IntentParser] LLM参数提取不完整，使用规则兜底")
            rule_params = self._rule_based_extract(user_input)
            # 合并参数：LLM结果优先，但用规则结果补充缺失字段
            if params:
                for key, value in rule_params.items():
                    if not params.get(key) or params.get(key) == "all":
                        params[key] = value
            else:
                params = rule_params
        
        # 5. 参数校验和纠正
        params = self._validate_and_correct_params(params)
        
        logger.info(f"🎯 [IntentParser] 最终参数: {params}")
        
        # 6. 判断是否需要获取数据
        needs_data = intent in IntentType.NEEDS_DATA
        
        return {
            "intent": intent,
            "params": params,
            "needs_data": needs_data,
            "direct_response": None
        }
    
    async def astream_parse(self, user_input: str, context_text: str = ""):
        """流式解析用户意图
        
        Args:
            user_input: 用户输入
            context_text: 会话上下文
            
        Yields:
            解析过程中的增量结果
        """
        # 1. 快速关键词匹配
        intent = self._quick_match(user_input)
        yield {"type": "intent", "intent": intent}
        
        # 2. 如果是直接回复类型，直接返回
        if intent in IntentTypeConfig.DIRECT_REPLY:
            yield {
                "type": "done",
                "result": {
                    "intent": intent,
                    "params": {},
                    "needs_data": False,
                    "direct_response": IntentPrompts.get_direct_response(intent)
                }
            }
            return
        
        # 3. 流式LLM参数提取
        async for param_chunk in self._astream_extract_params(user_input, intent, context_text):
            yield {"type": "params_chunk", "content": param_chunk}
    
    # ==================== 私有方法 ====================
    
    def _quick_match(self, user_input: str) -> str:
        """快速关键词匹配（兜底方案）
        
        注意：这是兜底方案，主要意图识别由LLM负责
        """
        # 关键词匹配
        query_lower = user_input.lower()
        
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent_type
        
        return IntentType.QUERY  # 默认查询
    
    async def _recognize_intent(self, user_input: str, context_text: str = "") -> str:
        """LLM意图识别（主要方式）
        
        核心原则：完全信任LLM的判断能力
        关键词匹配只是兜底方案（当LLM失败时）
        
        Args:
            user_input: 用户输入
            context_text: 历史上下文
            
        Returns:
            IntentType 枚举值
        """
        # ========== 步骤1: LLM意图识别（主要方式）==========
        try:
            prompt = IntentPrompts.get_intent_recognition_prompt(user_input, context_text)
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            
            response = await self.llm.agenerate([messages])
            intent_result = response.generations[0][0].text.strip().lower()
            
            logger.info(f"🧠 [IntentParser] LLM识别意图: {intent_result}")
            
            # 校验意图是否有效
            valid_intents = [i.value for i in IntentType]
            if intent_result in valid_intents:
                return IntentType(intent_result)
            else:
                logger.warning(f"⚠️ [IntentParser] LLM返回无效意图 '{intent_result}'，使用关键词兜底")
                
        except Exception as e:
            logger.warning(f"⚠️ [IntentParser] LLM意图识别失败: {e}，使用关键词兜底")
        
        # ========== 步骤2: LLM失败时，使用关键词兜底 ==========
        quick_intent = self._quick_match(user_input)
        return quick_intent
    
    async def _extract_params(
        self, 
        user_input: str, 
        intent: str, 
        context_text: str = ""
    ) -> Dict[str, Any]:
        """使用LLM提取查询参数（增强版 - 带Few-Shot）"""
        
        prompt = IntentPrompts.get_param_extraction_prompt(user_input, intent, context_text)
        
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
    
    async def _astream_extract_params(
        self, 
        user_input: str, 
        intent: str,
        context_text: str = ""
    ):
        """流式提取参数"""
        
        prompt = IntentPrompts.get_param_extraction_prompt(user_input, intent, context_text)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ]
        
        full_content = ""
        try:
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
            return json.loads(content)
        except:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return {}
    
    def _rule_based_extract(self, user_input: str) -> Dict[str, Any]:
        """基于规则的参数提取（兜底方案）"""
        
        params = {
            "anime_type": "all",
            "time_range": "",
            "platform": "all",
            "sort_by": "rating",
            "keyword": ""
        }
        
        # 检测番剧类型关键词（同义词匹配）
        for type_name, synonyms in SlotDefinition.ANIME_TYPE_KEYWORDS.items():
            if any(kw in user_input for kw in synonyms):
                params["anime_type"] = type_name
                logger.info(f"📝 [IntentParser] 规则兜底检测到类型: {type_name}")
                break
        
        # 检测时间范围关键词
        time_patterns = [
            (r"(\d{4})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r"(\d{4})年(\d{1,2})月", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}"),
        ]
        
        for pattern, extractor in time_patterns:
            match = re.search(pattern, user_input)
            if match:
                params["time_range"] = extractor(match)
                logger.info(f"📝 [IntentParser] 规则兜底检测到时间: {params['time_range']}")
                break
        
        # 如果没有精确匹配，尝试同义词
        if not params["time_range"]:
            for time_name, synonyms in SlotDefinition.TIME_KEYWORDS.items():
                if any(kw in user_input for kw in synonyms):
                    year_match = re.search(r"(\d{4})", user_input)
                    if year_match:
                        params["time_range"] = f"{year_match.group(1)}{time_name}"
                    else:
                        params["time_range"] = time_name
                    logger.info(f"📝 [IntentParser] 规则兜底检测到时间: {params['time_range']}")
                    break
        
        # 检测排序关键词（同义词匹配）
        for sort_name, synonyms in SlotDefinition.SORT_BY_KEYWORDS.items():
            if any(kw in user_input for kw in synonyms):
                params["sort_by"] = sort_name
                logger.info(f"📝 [IntentParser] 规则兜底检测到排序: {sort_name}")
                break
        
        # 检测平台关键词
        if "bangumi" in user_input.lower() or "番组" in user_input:
            params["platform"] = "bangumi"
        elif "b站" in user_input or "bilibili" in user_input.lower():
            params["platform"] = "bilibili"
        
        logger.info(f"📝 [IntentParser] 规则兜底提取的参数: {params}")
        return params
    
    def _validate_and_correct_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """参数校验和纠正（增强版）"""
        
        if not params:
            return params
        
        # 自动纠正映射
        type_correction_map = {
            "电影": "剧场版",
            "动漫电影": "剧场版",
            "动画": "all",
            "番": "all",
            "番剧": "all",
            "日本": "日漫",
            "国产": "国漫",
        }
        
        # anime_type 自动纠正
        current_type = params.get("anime_type", "")
        if current_type in type_correction_map:
            old_value = current_type
            params["anime_type"] = type_correction_map[current_type]
            logger.info(f"🔧 [IntentParser] anime_type 自动纠正: '{old_value}' → '{params['anime_type']}'")
        
        # time_range 格式归一化
        time_str = params.get("time_range", "")
        if time_str:
            year_month_match = re.match(r"(\d{4})年(\d{1,2})月", time_str)
            if year_month_match:
                params["time_range"] = f"{year_month_match.group(1)}-{int(year_month_match.group(2)):02d}"
                logger.info(f"🔧 [IntentParser] time_range 格式归一化: {time_str} → {params['time_range']}")
        
        # 枚举值校验
        valid_platforms = ["jikan", "anilist", "bangumi", "bilibili", "all"]
        valid_types = ["日漫", "国漫", "剧场版", "OVA", "all"]
        valid_sorts = ["rating", "hot", "latest"]
        
        if params.get("anime_type") not in valid_types:
            params["anime_type"] = "all"
        
        if params.get("platform") not in valid_platforms:
            params["platform"] = "all"
        
        if params.get("sort_by") not in valid_sorts:
            params["sort_by"] = "rating"
        
        return params
    
    # ==================== 槽位校验（保留原有接口） ====================
    
    def validate_slots(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """校验槽位并返回校验结果"""
        errors = []
        missing_slots = []
        corrected_params = params.copy()
        
        required = SlotDefinition.get_required_slots(intent)
        
        for slot_name in required:
            if slot_name not in params or not params.get(slot_name):
                missing_slots.append(slot_name)
        
        for slot_name, value in params.items():
            if slot_name in SlotDefinition.DEFINITIONS:
                slot_def = SlotDefinition.DEFINITIONS[slot_name]
                
                if "enum" in slot_def and value:
                    if value not in slot_def["enum"]:
                        errors.append(f"{slot_def['description']} '{value}' 不在可选值 {slot_def['enum']} 中")
                        corrected_params[slot_name] = slot_def.get("default", "all")
        
        return {
            "valid": len(errors) == 0 and len(missing_slots) == 0,
            "errors": errors,
            "missing_slots": missing_slots,
            "corrected_params": corrected_params
        }
    
    def generate_clarification_question(self, missing_slots: List[str], params: Dict[str, Any]) -> str:
        """生成澄清问题"""
        return IntentPrompts.generate_clarification_question(missing_slots, params)
    
    def _get_direct_response(self, intent) -> str:
        """获取直接回复 - 分层策略
        
        策略说明：
        - greeting/thanks: 简单模板回复（快速响应）
        - description/capability: LLM生成回复（智能灵活）
        - unknown: LLM生成友好的引导
        
        注意：如果需要LLM生成回复，返回 None 触发外部调用
        """
        # 尝试从 IntentType 获取值
        intent_value = intent.value if hasattr(intent, 'value') else str(intent)
        
        # ========== 简单意图：使用预定义模板 ==========
        template_responses = {
            "greeting": "你好！我是番剧智能助手，专注于帮助你了解日本动画番剧的相关信息。有什么番剧想了解的吗？",
            "thanks": "不客气！很高兴能帮到你。还有什么想了解的吗？"
        }
        
        if intent_value in template_responses:
            return template_responses[intent_value]
        
        # ========== 复杂意图：需要LLM生成 ==========
        # description（自我介绍）、capability（询问能力）返回 None
        # 触发外部调用 LLM 生成更智能的回复
        complex_intents = ["description", "capability", "unknown"]
        
        if intent_value in complex_intents:
            # 返回特殊标记，让外部调用 LLM 生成
            return None
        
        # 默认回复
        return "你好！有什么可以帮你的？"
    
    async def _generate_complex_response(
        self, 
        intent: str, 
        user_input: str,
        context_text: str = ""
    ) -> str:
        """使用LLM生成复杂意图的回复
        
        用于 description、capability、unknown 等需要智能生成的回复
        
        Args:
            intent: 意图类型
            user_input: 用户原始输入
            context_text: 会话上下文
            
        Returns:
            生成的回复文本
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # 构建Prompt
        prompt = self._build_direct_response_prompt(intent, user_input, context_text)
        
        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            response = await self.llm.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.warning(f"LLM生成直接回复失败: {e}")
            # 降级到模板回复
            return self._get_fallback_response(intent)
    
    def _build_direct_response_prompt(self, intent: str, user_input: str, context_text: str = "") -> str:
        """构建直接回复的Prompt"""
        
        context_hint = f"\n\n## 历史上下文\n{context_text}" if context_text else ""
        
        prompts = {
            "description": f"""你是一个友好的番剧智能助手。用户问你关于你自己的身份问题。

## 你的身份
你是"番剧智能助手"，一个专注于日本动画番剧的AI助手。

## 你的能力
- 🎬 查询番剧信息 - 根据时间、类型、平台搜索番剧
- 📖 了解番剧详情 - 获取特定番剧的剧情介绍、评分、角色信息
- 🔥 发现热门番剧 - 查看当前最受欢迎的番剧排行榜
- ⭐ 个性化推荐 - 根据用户偏好推荐番剧
- 🔍 关键词搜索 - 搜索特定番剧信息

## 回答要求
1. 友好，自然，像朋友聊天
2. 简洁明了，不要太长
3. 可以适当加入 emoji 让回复更生动
4. 结尾可以引导用户提问

## 用户问题
{user_input}
{context_hint}

请直接回答，不要加任何前缀：""",
            
            "capability": f"""你是一个友好的番剧智能助手。用户询问你能做什么。

## 你的能力介绍
你可以帮助用户：
- 🎬 **查询番剧信息** - 根据时间、类型、平台搜索番剧
- 📖 **了解番剧详情** - 获取特定番剧的剧情介绍、评分、角色信息、声优阵容
- 🔥 **发现热门番剧** - 查看各类排行榜（评分最高、最受欢迎、近期热门等）
- ⭐ **个性化推荐** - 根据用户偏好推荐番剧
- 🔍 **关键词搜索** - 搜索特定番剧信息
- 💬 **对比分析** - 对比两部番剧的评分、风格等

## 数据来源
你可以查询多个数据源的信息，包括：
- Bilibili（哔哩哔哩）
- Jikan（MyAnimeList）
- Bangumi（番组计划）
- AniList

## 回答要求
1. 友好，自然，像朋友介绍自己的能力
2. 简洁明了，分点说明
3. 可以适当加入 emoji
4. 结尾可以引导用户尝试

## 用户问题
{user_input}
{context_hint}

请直接回答，不要加任何前缀：""",
            
            "unknown": f"""你是一个友好的番剧智能助手。用户的问题你无法理解，你需要友好地引导。

## 你的身份
你是"番剧智能助手"，专注于帮助用户查询日本动画番剧的信息。

## 回答要求
1. 友好、礼貌，不要让用户感到尴尬
2. 说明你是专门帮助查询番剧的
3. 提供几个示例问题帮助用户了解你的能力
4. 语气轻松自然

## 示例引导
你可以这样问：
- "推荐几部好看的日漫"
- "《进击的巨人》剧情介绍"
- "2024年评分最高的番剧有哪些"
- "最近有什么热门的新番"

## 用户问题
{user_input}
{context_hint}

请直接回答，不要加任何前缀："""
        }
        
        return prompts.get(intent, prompts["unknown"])
    
    def _get_fallback_response(self, intent: str) -> str:
        """降级回复（当LLM生成失败时）"""
        fallbacks = {
            "description": """你好！我是番剧智能助手，一个专注于日本动画番剧的AI助手。

我可以帮你：
🎬 查询番剧信息
📖 了解番剧详情
🔥 发现热门番剧
⭐ 获取推荐

有什么番剧想了解的吗？""",
            
            "capability": """我可以帮助你：
1. 📋 查询番剧信息 - 根据时间、类型、平台搜索番剧
2. 📖 了解番剧详情 - 获取特定番剧的剧情介绍
3. 🔥 查看热门排行 - 了解当前最受欢迎的番剧
4. 🔍 关键词搜索 - 搜索特定番剧信息

请告诉我你想了解什么？""",
            
            "unknown": """抱歉，我不太理解你的意思。我是番剧智能助手，专注于帮助你查询日本动画番剧的信息。

你可以这样问我：
- '推荐几部好看的日漫'
- '《进击的巨人》剧情介绍'
- '2024年评分最高的番剧有哪些'

请问有什么番剧想了解的吗？"""
        }
        return fallbacks.get(intent, "你好！有什么可以帮你的？")
