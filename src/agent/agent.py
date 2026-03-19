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

class Planner:
        """解析用户意图（增强版 - 带规则兜底）
        
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
        """使用LLM提取查询参数（增强版 - 带Few-Shot）
        
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
        
        # 增强版Prompt - 包含Few-Shot示例
        prompt = f"""分析用户问题，提取查询参数。

## 意图类型
- query: 查询番剧列表，如"最近有什么番剧推荐"
- detail: 获取番剧详情，如"这部番剧讲了什么"
- ranking: 查看排行榜，如"评分最高的番剧有哪些"

## 参数提取规则
### anime_type（番剧类型）- 必填参数！
- "国漫"、"国产动画"、"国产动漫" → 设置为 "国漫"
- "日漫"、"日本动画" → 设置为 "日漫"
- "剧场版"、"电影版"、"动画电影" → 设置为 "剧场版"
- "OVA"、"OAD" → 设置为 "OVA"
- 没有提到任何类型 → 设置为 "all"

### time_range（时间范围）
- "2026-03"、"2026年3月" → "2026-03"
- "本月"、"这个月" → "本月"
- "最新"、"最近" → "最新"
- "2026春"、"春季" → "2026春"

### sort_by（排序方式）
- "最热"、"热门"、"火" → "hot"
- "最新"、"新番" → "latest"
- "评分"、"高分"、"推荐" → "rating"

## Few-Shot示例
【示例1】
输入: "推荐几部国漫"
思考: 用户明确提到"国漫"，anime_type必须设为"国漫"
输出: {{"anime_type": "国漫", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例2】
输入: "2024年7月有哪些日漫"
思考: 用户提到"2024年7月"表示时间，"日漫"表示类型
输出: {{"anime_type": "日漫", "time_range": "2024-07", "sort_by": "rating", "platform": "all", "keyword": ""}}

【示例3】
输入: "剧场版电影有哪些"
思考: 用户提到"剧场版"和"电影"
输出: {{"anime_type": "剧场版", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例4】
输入: "有什么番剧推荐"
思考: 用户没有提到任何类型，使用默认值
输出: {{"anime_type": "all", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例5】
输入: "本月最新的热门番剧"
思考: 用户提到"本月"和时间，"热门"表示sort_by为hot
输出: {{"anime_type": "all", "time_range": "本月", "sort_by": "hot", "platform": "all", "keyword": ""}}

【示例6 - 模糊场景】
输入: "最近火的国产动画"
思考: "国产动画"=国漫，"最近"=最新，"火"=hot
输出: {{"anime_type": "国漫", "time_range": "最新", "sort_by": "hot", "platform": "all", "keyword": ""}}

## Few-Shot示例（反例 - 常见错误请避免）
【反例1】
输入: "我想看动漫电影"
思考: "电影"应纠正为"剧场版"，不是"电影"
错误输出: {{"anime_type": "电影", ...}}
正确输出: {{"anime_type": "剧场版", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【反例2】
输入: "2024年的新番"
思考: "新番"需要结合当前时间判断具体季度，"2024年"只是年份
错误输出: {{"time_range": "2024", ...}}
正确输出: {{"anime_type": "all", "sort_by": "latest", "platform": "all", "time_range": "2024", "keyword": ""}}

【反例3】
输入: "日本动漫"
思考: "日本动漫"应该识别为"日漫"
错误输出: {{"anime_type": "日本动漫", ...}}
正确输出: {{"anime_type": "日漫", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

## 用户问题
{user_input}
意图类型: {intent}{context_hint}

## 输出要求
只输出JSON格式，不要其他任何内容："""
        
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
        """使用LLM流式提取查询参数 - 每次 LLM 输出 chunk 时立即 yield（增强版）
        
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
        
        # 增强版Prompt - 包含Few-Shot示例
        prompt = f"""分析用户问题，提取查询参数。

## 意图类型
- query: 查询番剧列表，如"最近有什么番剧推荐"
- detail: 获取番剧详情，如"这部番剧讲了什么"
- ranking: 查看排行榜，如"评分最高的番剧有哪些"

## 参数提取规则
### anime_type（番剧类型）- 必填参数！
- "国漫"、"国产动画"、"国产动漫" → 设置为 "国漫"
- "日漫"、"日本动画" → 设置为 "日漫"
- "剧场版"、"电影版"、"动画电影" → 设置为 "剧场版"
- "OVA"、"OAD" → 设置为 "OVA"
- 没有提到任何类型 → 设置为 "all"

### time_range（时间范围）
- "2026-03"、"2026年3月" → "2026-03"
- "本月"、"这个月" → "本月"
- "最新"、"最近" → "最新"
- "2026春"、"春季" → "2026春"

### sort_by（排序方式）
- "最热"、"热门"、"火" → "hot"
- "最新"、"新番" → "latest"
- "评分"、"高分"、"推荐" → "rating"

## Few-Shot示例
【示例1】
输入: "推荐几部国漫"
思考: 用户明确提到"国漫"，anime_type必须设为"国漫"
输出: {{"anime_type": "国漫", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例2】
输入: "2024年7月有哪些日漫"
思考: 用户提到"2024年7月"表示时间，"日漫"表示类型
输出: {{"anime_type": "日漫", "time_range": "2024-07", "sort_by": "rating", "platform": "all", "keyword": ""}}

【示例3】
输入: "剧场版电影有哪些"
思考: 用户提到"剧场版"和"电影"
输出: {{"anime_type": "剧场版", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例4】
输入: "有什么番剧推荐"
思考: 用户没有提到任何类型，使用默认值
输出: {{"anime_type": "all", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例5】
输入: "本月最新的热门番剧"
思考: 用户提到"本月"和时间，"热门"表示sort_by为hot
输出: {{"anime_type": "all", "time_range": "本月", "sort_by": "hot", "platform": "all", "keyword": ""}}

【示例6 - 模糊场景】
输入: "最近火的国产动画"
思考: "国产动画"=国漫，"最近"=最新，"火"=hot
输出: {{"anime_type": "国漫", "time_range": "最新", "sort_by": "hot", "platform": "all", "keyword": ""}}

## Few-Shot示例（反例 - 常见错误请避免）
【反例1】
输入: "我想看动漫电影"
思考: "电影"应纠正为"剧场版"，不是"电影"
错误输出: {{"anime_type": "电影", ...}}
正确输出: {{"anime_type": "剧场版", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【反例2】
输入: "2024年的新番"
思考: "新番"需要结合当前时间判断具体季度
错误输出: {{"time_range": "2024", ...}}
正确输出: {{"anime_type": "all", "sort_by": "latest", "platform": "all", "time_range": "2024", "keyword": ""}}

【反例3】
输入: "日本动漫"
思考: "日本动漫"应该识别为"日漫"
错误输出: {{"anime_type": "日本动漫", ...}}
正确输出: {{"anime_type": "日漫", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

## 用户问题
{user_input}
意图类型: {intent}{context_hint}

## 输出要求
只输出JSON格式，不要其他任何内容："""
        
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
    
    def _rule_based_extract(self, user_input: str) -> Dict[str, Any]:
        """基于规则的参数提取（兜底方案）
        
        当LLM提取失败时，使用关键词匹配作为兜底
        支持同义词映射和自动纠正
        """
        params = {
            "anime_type": "all",
            "time_range": "",
            "platform": "all",
            "sort_by": "rating",
            "keyword": ""
        }
        
        # ========== 同义词映射表 ==========
        # 番剧类型同义词
        anime_type_synonyms = {
            "国漫": ["国漫", "国产", "国创", "中国动画", "国产动漫", "国产番", "国动"],
            "日漫": ["日漫", "日本动画", "日本动漫", "日本番", "日番", "日本动画"],
            "剧场版": ["剧场版", "电影版", "动画电影", "动漫电影", "电影", "动漫电影"],
            "OVA": ["OVA", "OAD", "OVA动画"]
        }
        
        # 排序方式同义词
        sort_by_synonyms = {
            "hot": ["最热", "热门", "火", "热度", "最火", "人气", "火爆"],
            "latest": ["最新", "新番", "刚出", "上新", "最近", "最近更新"],
            "rating": ["评分", "高分", "推荐", "评分高", "口碑好", "评价好", "最高分"]
        }
        
        # 时间范围同义词
        time_synonyms = {
            "本月": ["本月", "这个月", "当月"],
            "最新": ["最新", "最近", "新番", "刚出", "刚更新"],
            "春": ["春季", "春番", "春天", "2026春"],
            "夏": ["夏季", "夏番", "夏天", "2026夏"],
            "秋": ["秋季", "秋番", "秋天", "2026秋"],
            "冬": ["冬季", "冬番", "冬天", "2026冬"]
        }
        
        # 检测番剧类型关键词（同义词匹配）
        for type_name, synonyms in anime_type_synonyms.items():
            if any(kw in user_input for kw in synonyms):
                params["anime_type"] = type_name
                logger.info(f"📝 [IntentParser] 规则兜底检测到类型: {type_name}")
                break
        
        # 检测时间范围关键词（同义词匹配）
        import re
        time_patterns = [
            # 精确格式：2026-03, 2024年7月
            (r"(\d{4})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r"(\d{4})年(\d{1,2})月", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}"),
        ]
        
        # 先匹配精确时间格式
        for pattern, extractor in time_patterns:
            match = re.search(pattern, user_input)
            if match:
                params["time_range"] = extractor(match)
                logger.info(f"📝 [IntentParser] 规则兜底检测到时间: {params['time_range']}")
                break
        
        # 如果没有精确匹配，尝试同义词
        if not params["time_range"]:
            for time_name, synonyms in time_synonyms.items():
                if any(kw in user_input for kw in synonyms):
                    # 尝试提取年份
                    year_match = re.search(r"(\d{4})", user_input)
                    if year_match:
                        params["time_range"] = f"{year_match.group(1)}{time_name}"
                    else:
                        params["time_range"] = time_name
                    logger.info(f"📝 [IntentParser] 规则兜底检测到时间: {params['time_range']}")
                    break
        
        # 检测排序关键词（同义词匹配）
        for sort_name, synonyms in sort_by_synonyms.items():
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
        """参数校验和纠正（增强版）
        
        确保参数值在合法范围内，防止非法值传播
        支持自动纠正：将用户口语化表述自动转换为标准参数值
        """
        if not params:
            return params
        
        # 枚举值定义
        valid_platforms = ["jikan", "anilist", "bangumi", "bilibili", "all"]
        valid_types = ["日漫", "国漫", "剧场版", "OVA", "all"]
        valid_sorts = ["rating", "hot", "latest"]
        
        # ========== 自动纠正逻辑 ==========
        # anime_type 自动纠正映射
        type_correction_map = {
            "电影": "剧场版",
            "动漫电影": "剧场版",
            "动画": "all",
            "番": "all",
            "番剧": "all",
            "日本": "日漫",
            "国产": "国漫",
        }
        
        # 检测 anime_type 是否需要自动纠正
        current_type = params.get("anime_type", "")
        if current_type in type_correction_map:
            old_value = current_type
            params["anime_type"] = type_correction_map[current_type]
            logger.info(f"🔧 [IntentParser] anime_type 自动纠正: '{old_value}' → '{params['anime_type']}'")
        
        # time_range 格式归一化
        time_str = params.get("time_range", "")
        if time_str:
            # 处理 "2024年7月" -> "2024-07" 格式
            import re
            year_month_match = re.match(r"(\d{4})年(\d{1,2})月", time_str)
            if year_month_match:
                params["time_range"] = f"{year_month_match.group(1)}-{int(year_month_match.group(2)):02d}"
                logger.info(f"🔧 [IntentParser] time_range 格式归一化: {time_str} → {params['time_range']}")
        
        # ========== 枚举值校验 ==========
        # 校验并纠正 anime_type
        if params.get("anime_type") not in valid_types:
            old_value = params.get("anime_type")
            params["anime_type"] = "all"
            logger.warning(f"⚠️ [IntentParser] anime_type 非法值 '{old_value}' 已纠正为 'all'")
        
        # 校验并纠正 platform
        if params.get("platform") not in valid_platforms:
            old_value = params.get("platform")
            params["platform"] = "all"
            logger.warning(f"⚠️ [IntentParser] platform 非法值 '{old_value}' 已纠正为 'all'")
        
        # 校验并纠正 sort_by
        if params.get("sort_by") not in valid_sorts:
            old_value = params.get("sort_by")
            params["sort_by"] = "rating"
            logger.warning(f"⚠️ [IntentParser] sort_by 非法值 '{old_value}' 已纠正为 'rating'")
        
        return params
    
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
