"""意图解析 Prompt 模板管理

将所有 Prompt 模板集中管理，便于维护和优化
"""


class IntentPrompts:
    """意图解析 Prompt 模板"""
    
    # ==================== 意图识别 Prompt ====================
    
    @staticmethod
    def get_intent_recognition_prompt(user_input: str, context_text: str = "") -> str:
        """意图识别 Prompt - 判断用户意图类型
        
        Args:
            user_input: 用户输入
            context_text: 历史上下文
            
        Returns:
            完整的 prompt 字符串
        """
        context_hint = ""
        if context_text:
            context_hint = f"""
## 历史上下文（参考）
{context_text}

注意：如果用户问题很简短（如"这些的评分呢？"），请结合历史上下文推断参数！"""
        
        return f"""分析用户问题，判断意图类型。

## 意图定义
- greeting: 打招呼、问好
- capability: 询问能力（如"你能做什么"）
- query: 查询番剧列表（主要意图）
- detail: 获取特定番剧详情
- ranking: 查看排行榜
- recommend: 推荐番剧
- compare: 对比番剧
- thanks: 感谢
- chat: 闲聊

## 用户问题
{user_input}

## 历史上下文
{context_text}

只输出意图类型名称，不要其他内容："""
    
    # ==================== 参数提取 Prompt ====================
    
    @staticmethod
    def get_param_extraction_prompt(user_input: str, intent: str, context_text: str = "") -> str:
        """参数提取 Prompt - 增强版（带Few-Shot）
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            context_text: 历史上下文
            
        Returns:
            完整的 prompt 字符串
        """
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

## Few-Shot示例（正例）
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
        
        return prompt
    
    # ==================== 直接回复内容 ====================
    
    @staticmethod
    def get_direct_response(intent: str) -> str:
        """获取直接回复内容
        
        Args:
            intent: 意图类型
            
        Returns:
            回复文本
        """
        responses = {
            "greeting": "你好！我是番剧智能助手，专注于帮助你了解日本动画番剧的相关信息。有什么番剧想了解的吗？",
            "capability": """我可以帮助你：
1. 📋 查询番剧信息 - 根据时间、类型、平台搜索番剧
2. 📖 了解番剧详情 - 获取特定番剧的剧情介绍
3. 🔥 查看热门排行 - 了解当前最受欢迎的番剧
4. 🔍 关键词搜索 - 搜索特定番剧信息

请告诉我你想了解什么？""",
            "thanks": "不客气！很高兴能帮到你。还有什么想了解的吗？"
        }
        return responses.get(intent, "你好！有什么可以帮你的？")
    
    # ==================== 澄清问题模板 ====================
    
    @staticmethod
    def generate_clarification_question(missing_slots: list, params: dict) -> str:
        """生成澄清问题
        
        根据缺失的槽位生成反问用户的问题
        
        Args:
            missing_slots: 缺失的槽位列表
            params: 当前参数
            
        Returns:
            澄清问题文本
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
            return "，".join(questions)
        return ""
