"""意图解析器 - 核心实现"""

import json
import re
import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .types import IntentType
from .slots import SlotDefinition
from .prompts import IntentPrompts

logger = logging.getLogger("IntentParser")


class IntentParser:
    """意图解析器 - 增强版
    
    负责分析用户问题，提取关键信息：
    - 意图类型
    - 查询参数（时间、平台、类型、关键词等）
    
    特性：
    - Few-Shot Prompt 示例
    - 规则兜底机制
    - 参数自动校验纠正
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
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    # ==================== 公开方法 ====================
    
    async def parse(self, user_input: str, context_text: str = "") -> Dict[str, Any]:
        """解析用户意图（增强版 - 带规则兜底）
        
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
        # 1. 快速关键词匹配
        intent = self._quick_match(user_input)
        
        # 2. 如果是直接回复类型，直接返回
        if intent in IntentType.DIRECT_REPLY:
            return {
                "intent": intent,
                "params": {},
                "needs_data": False,
                "direct_response": IntentPrompts.get_direct_response(intent)
            }
        
        # 3. 使用LLM提取查询参数（增强版 - 带Few-Shot）
        params = await self._extract_params(user_input, intent, context_text)
        
        # 4. 规则兜底：如果LLM提取失败或anime_type为空，使用规则匹配
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
        if intent in IntentType.DIRECT_REPLY:
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
