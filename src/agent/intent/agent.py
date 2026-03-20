"""
意图识别智能体 (Intent Agent)

专门负责意图识别的子智能体，类似于市面上成熟智能体的架构：
- 角色定义
- Few-Shot 示例
- 思考链 (Chain of Thought)
- 置信度评估
- 自反思机制

这种设计的优势：
1. 职责分离 - 意图识别独立为一个智能体
2. 可维护性 - Prompt模板集中管理
3. 可扩展性 - 容易添加新的意图类型
4. 可靠性 - 置信度评估和自反思提高准确率
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .types import IntentType, IntentTypeConfig
from .slots import SlotDefinition
from .prompts import IntentPrompts

logger = logging.getLogger("IntentAgent")


class ConfidenceLevel(Enum):
    """意图识别置信度级别"""
    HIGH = "high"      # 高置信度 (>0.9)
    MEDIUM = "medium"  # 中置信度 (0.7-0.9)
    LOW = "low"        # 低置信度 (<0.7)


class IntentAgent:
    """意图识别智能体
    
    这是一个专门的子智能体，负责：
    1. 理解用户输入的真实意图
    2. 提取关键查询参数
    3. 评估识别结果的置信度
    4. 自反思和二次校验
    
    设计理念：
    - 模仿人类思考过程：理解 → 分析 → 确认
    - Few-Shot + Chain of Thought 提高准确性
    - 置信度机制提供可靠性保障
    """
    
    def __init__(self, llm: ChatOpenAI):
        """初始化意图识别智能体
        
        Args:
            llm: LLM客户端实例
        """
        self.llm = llm
        
        # 意图关键词映射（兜底用）
        self._intent_keywords = IntentTypeConfig.INTENT_KEYWORDS
    
    # ==================== 公开接口 ====================
    
    async def recognize(self, user_input: str, context_text: str = "") -> Dict[str, Any]:
        """识别用户意图（主入口）
        
        采用多轮校验策略：
        1. LLM智能识别（主要方式）
        2. 置信度评估
        3. 自反思校验（可选）
        4. 规则兜底
        
        Args:
            user_input: 用户输入
            context_text: 历史上下文
            
        Returns:
            {
                "intent": "query",
                "confidence": "high",
                "reasoning": "用户提到了'推荐'关键词...",
                "params": {...},
                "needs_data": True,
                "direct_response": None
            }
        """
        logger.info(f"🎯 [IntentAgent] 开始识别意图: {user_input}")
        
        # 步骤1: LLM意图识别（带思考链）
        intent, reasoning = await self._llm_recognize(user_input, context_text)
        
        # 步骤2: 置信度评估
        confidence = self._evaluate_confidence(intent, reasoning, user_input)
        logger.info(f"🧠 [IntentAgent] 识别结果: intent={intent}, confidence={confidence}")
        
        # 步骤3: 如果置信度低，进行自反思
        if confidence == ConfidenceLevel.LOW:
            logger.info(f"🔄 [IntentAgent] 置信度低，进行自反思校验...")
            refined_intent, refined_reasoning = await self._self_reflect(
                user_input, intent, reasoning, context_text
            )
            if refined_intent != intent:
                intent = refined_intent
                reasoning = refined_reasoning
                logger.info(f"✅ [IntentAgent] 自反思后修正意图: {intent}")
        
        # 步骤4: 如果是直接回复类型，直接返回
        if intent in IntentTypeConfig.DIRECT_REPLY:
            return {
                "intent": intent,
                "confidence": confidence.value,
                "reasoning": reasoning,
                "params": {},
                "needs_data": False,
                "direct_response": IntentPrompts.get_direct_response(intent)
            }
        
        # 步骤5: 参数提取
        params = await self._extract_params(user_input, intent, context_text)
        
        # 步骤6: 规则兜底（如果LLM提取失败）
        if not params or not params.get("anime_type") or params.get("anime_type") == "all":
            rule_params = self._rule_based_extract(user_input)
            params = self._merge_params(params, rule_params)
        
        # 步骤7: 参数校验和纠正
        params = self._validate_and_correct_params(params)
        
        logger.info(f"📦 [IntentAgent] 最终参数: {params}")
        
        # 步骤8: 判断是否需要数据
        needs_data = intent in IntentType.NEEDS_DATA
        
        return {
            "intent": intent,
            "confidence": confidence.value,
            "reasoning": reasoning,
            "params": params,
            "needs_data": needs_data,
            "direct_response": None
        }
    
    async def recognize_stream(self, user_input: str, context_text: str = ""):
        """流式识别（用于实时反馈）
        
        Yields:
            识别过程中的增量结果
        """
        # 1. 快速意图预判（关键词匹配）
        quick_intent = self._quick_match(user_input)
        yield {"type": "intent_preview", "intent": quick_intent}
        
        # 2. 如果是直接回复类型
        if quick_intent in IntentTypeConfig.DIRECT_REPLY:
            yield {
                "type": "done",
                "result": {
                    "intent": quick_intent,
                    "confidence": "high",
                    "params": {},
                    "needs_data": False,
                    "direct_response": IntentPrompts.get_direct_response(quick_intent)
                }
            }
            return
        
        # 3. LLM正式识别
        intent, reasoning = await self._llm_recognize(user_input, context_text)
        yield {"type": "intent_confirmed", "intent": intent, "reasoning": reasoning}
        
        # 4. 参数提取（流式）
        async for param_chunk in self._stream_extract_params(user_input, intent, context_text):
            yield {"type": "params_chunk", "content": param_chunk}
    
    # ==================== 私有方法：意图识别 ====================
    
    async def _llm_recognize(
        self, 
        user_input: str, 
        context_text: str = ""
    ) -> Tuple[str, str]:
        """LLM意图识别（带思考链）
        
        Args:
            user_input: 用户输入
            context_text: 历史上下文
            
        Returns:
            (意图类型, 思考过程)
        """
        prompt = IntentPrompts.get_agent_intent_prompt(user_input, context_text)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ]
        
        try:
            response = await self.llm.agenerate([messages])
            content = response.generations[0][0].text.strip()
            
            logger.info(f"🧠 [IntentAgent] LLM原始输出: {content[:200]}...")
            
            # 解析输出
            intent, reasoning = self._parse_llm_output(content)
            
            if intent:
                return intent, reasoning
            
        except Exception as e:
            logger.warning(f"⚠️ [IntentAgent] LLM识别失败: {e}")
        
        # 兜底：关键词匹配
        quick_intent = self._quick_match(user_input)
        return quick_intent, "关键词兜底匹配"
    
    async def _self_reflect(
        self,
        user_input: str,
        current_intent: str,
        reasoning: str,
        context_text: str = ""
    ) -> Tuple[str, str]:
        """自反思机制 - 二次校验意图
        
        当置信度低时，强制LLM重新思考：
        1. 当前意图是否正确？
        2. 是否有其他更合适的意图？
        3. 用户可能的真实意图是什么？
        
        Args:
            user_input: 用户输入
            current_intent: 当前识别的意图
            reasoning: 当前推理过程
            context_text: 历史上下文
            
        Returns:
            (修正后的意图, 修正后的推理)
        """
        prompt = IntentPrompts.get_self_reflect_prompt(
            user_input, current_intent, reasoning, context_text
        )
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"请重新评估这个用户问题: {user_input}")
        ]
        
        try:
            response = await self.llm.agenerate([messages])
            content = response.generations[0][0].text.strip()
            
            # 尝试解析修正后的意图
            refined_intent, refined_reasoning = self._parse_llm_output(content)
            
            if refined_intent and refined_intent != current_intent:
                return refined_intent, f"{reasoning} → 自反思修正: {refined_reasoning}"
            
        except Exception as e:
            logger.warning(f"⚠️ [IntentAgent] 自反思失败: {e}")
        
        return current_intent, reasoning
    
    def _evaluate_confidence(
        self, 
        intent: str, 
        reasoning: str, 
        user_input: str
    ) -> ConfidenceLevel:
        """评估意图识别置信度
        
        置信度评估策略：
        1. 意图类型明确（直接回复类、详情类） → HIGH
        2. 包含明确的意图关键词 → HIGH
        3. 意图与输入高度匹配 → HIGH
        4. 模糊/歧义输入 → MEDIUM/LOW
        5. 兜底匹配 → LOW
        
        Args:
            intent: 识别的意图
            reasoning: 推理过程
            user_input: 用户输入
            
        Returns:
            置信度级别
        """
        # 规则1: 直接回复类意图通常是明确的
        if intent in IntentTypeConfig.DIRECT_REPLY:
            # 检查是否有明确的触发词
            keywords = self._intent_keywords.get(IntentType(intent), [])
            if any(kw in user_input for kw in keywords):
                return ConfidenceLevel.HIGH
            return ConfidenceLevel.MEDIUM
        
        # 规则2: 包含番剧名称（带书名号）通常是详情意图
        if "《" in user_input and "》" in user_input:
            if intent in [IntentType.DETAIL.value, IntentType.QUERY.value]:
                return ConfidenceLevel.HIGH
        
        # 规则3: 明确的动作词（如"推荐"、"排行"）是高置信度
        high_confidence_keywords = ["推荐", "排行", "评分", "详情", "介绍", "查询"]
        if any(kw in user_input for kw in high_confidence_keywords):
            return ConfidenceLevel.HIGH
        
        # 规则4: 兜底匹配是低置信度
        if "关键词兜底" in reasoning or "规则兜底" in reasoning:
            return ConfidenceLevel.LOW
        
        # 规则5: 检查是否有歧义（如同时包含多种意图）
        intent_count = sum(1 for kw_list in self._intent_keywords.values() 
                          if any(kw in user_input for kw in kw_list))
        if intent_count > 2:
            return ConfidenceLevel.MEDIUM
        
        return ConfidenceLevel.MEDIUM
    
    def _parse_llm_output(self, content: str) -> Tuple[Optional[str], str]:
        """解析LLM输出
        
        期望格式:
        ```json
        {
            "intent": "query",
            "reasoning": "用户提到了..."
        }
        ```
        
        Args:
            content: LLM原始输出
            
        Returns:
            (意图类型, 推理过程)
        """
        # 尝试JSON解析
        try:
            # 查找JSON块
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                intent = data.get("intent", "").lower()
                reasoning = data.get("reasoning", "")
                
                if intent in IntentTypeConfig.get_all_values():
                    return intent, reasoning
        except:
            pass
        
        # 尝试直接提取意图
        content_lower = content.lower().strip()
        for intent_type in IntentTypeConfig.get_all_values():
            if intent_type in content_lower:
                # 尝试提取推理过程
                reasoning_match = re.search(r'reasoning[：:]\s*(.+)', content, re.IGNORECASE)
                reasoning = reasoning_match.group(1) if reasoning_match else "LLM识别"
                return intent_type, reasoning
        
        return None, ""
    
    def _quick_match(self, user_input: str) -> str:
        """快速关键词匹配（兜底方案）"""
        query_lower = user_input.lower()
        
        for intent_type, keywords in self._intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent_type.value
        
        return IntentType.QUERY.value
    
    # ==================== 私有方法：参数提取 ====================
    
    async def _extract_params(
        self,
        user_input: str,
        intent: str,
        context_text: str = ""
    ) -> Dict[str, Any]:
        """使用LLM提取查询参数（带Few-Shot）"""
        prompt = IntentPrompts.get_agent_params_prompt(user_input, intent, context_text)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ]
        
        try:
            response = await self.llm.agenerate([messages])
            content = response.generations[0][0].text
            
            logger.info(f"📝 [IntentAgent] 参数提取原始输出: {content[:200]}...")
            
            params = self._parse_json_params(content)
            return params if params else {}
            
        except Exception as e:
            logger.warning(f"⚠️ [IntentAgent] 参数提取失败: {e}")
            return {}
    
    async def _stream_extract_params(
        self,
        user_input: str,
        intent: str,
        context_text: str = ""
    ):
        """流式参数提取"""
        prompt = IntentPrompts.get_agent_params_prompt(user_input, intent, context_text)
        
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
            
            params = self._parse_json_params(full_content)
            if params:
                yield json.dumps(params, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ [IntentAgent] 流式参数提取失败: {e}")
            yield f"[解析失败: {e}]"
    
    def _parse_json_params(self, content: str) -> Dict[str, Any]:
        """解析JSON参数字符串"""
        try:
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
    
    def _rule_based_extract(self, user_input: str) -> Dict[str, Any]:
        """基于规则的参数提取（兜底方案）"""
        params = {
            "anime_type": "all",
            "time_range": "",
            "platform": "all",
            "sort_by": "rating",
            "keyword": ""
        }
        
        # 检测番剧类型
        for type_name, synonyms in SlotDefinition.ANIME_TYPE_KEYWORDS.items():
            if any(kw in user_input for kw in synonyms):
                params["anime_type"] = type_name
                break
        
        # 检测时间范围
        time_patterns = [
            (r"(\d{4})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r"(\d{4})年(\d{1,2})月", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}"),
        ]
        
        for pattern, extractor in time_patterns:
            match = re.search(pattern, user_input)
            if match:
                params["time_range"] = extractor(match)
                break
        
        # 检测排序
        for sort_name, synonyms in SlotDefinition.SORT_BY_KEYWORDS.items():
            if any(kw in user_input for kw in synonyms):
                params["sort_by"] = sort_name
                break
        
        # 检测平台
        if "bangumi" in user_input.lower() or "番组" in user_input:
            params["platform"] = "bangumi"
        elif "b站" in user_input or "bilibili" in user_input.lower():
            params["platform"] = "bilibili"
        
        return params
    
    def _merge_params(self, llm_params: Dict, rule_params: Dict) -> Dict:
        """合并LLM参数和规则参数（LLM优先）"""
        if not llm_params:
            return rule_params
        
        merged = rule_params.copy()
        for key, value in llm_params.items():
            if value and value != "all":
                merged[key] = value
        
        return merged
    
    def _validate_and_correct_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """参数校验和纠正"""
        if not params:
            return params
        
        # 类型纠正映射
        type_correction_map = {
            "电影": "剧场版",
            "动漫电影": "剧场版",
            "动画": "all",
            "番": "all",
            "番剧": "all",
            "日本": "日漫",
            "国产": "国漫",
        }
        
        # anime_type 纠正
        current_type = params.get("anime_type", "")
        if current_type in type_correction_map:
            params["anime_type"] = type_correction_map[current_type]
        
        # time_range 格式归一化
        time_str = params.get("time_range", "")
        if time_str:
            year_month_match = re.match(r"(\d{4})年(\d{1,2})月", time_str)
            if year_month_match:
                params["time_range"] = f"{year_month_match.group(1)}-{int(year_month_match.group(2)):02d}"
        
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


# ==================== 便捷函数 ====================

async def create_intent_agent(llm: ChatOpenAI) -> IntentAgent:
    """创建意图识别智能体实例
    
    Args:
        llm: LLM客户端
        
    Returns:
        IntentAgent实例
    """
    return IntentAgent(llm)
