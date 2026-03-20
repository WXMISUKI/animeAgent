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
- greeting: 打招呼、问好（如"你好"、"嗨"）
- description: 询问智能体身份/自我介绍（如"你是谁"、"你叫什么"）
- capability: 询问智能体能力/功能（如"你能做什么"、"你有什么用"）
- query: 查询番剧列表（主要意图，如"推荐番剧"、"搜索日漫"）
- detail: 获取特定番剧详情（如"《进击的巨人》怎么样"）
- ranking: 查看排行榜（如"热门排行"、"评分最高"）
- recommend: 推荐番剧（如"有什么推荐"）
- compare: 对比番剧（如"《A》和《B》哪个好"）
- thanks: 感谢（如"谢谢"）
- chat: 闲聊（如"今天天气"）
- unknown: 无法理解/无意义输入（如"你是水"、"123"、"啊啊啊"）

## 判断规则（重要！）
1. 如果用户问"你是谁"、"你叫什么"、"介绍一下自己" → description
2. 如果用户问"你能做什么"、"你有什么用" → capability
3. 如果用户说无意义的内容（如"你是水"、单个字符、纯符号） → unknown
4. 如果用户提到具体番剧名（如《xxx》） → detail
5. 如果用户提到番剧类型（如"日漫"、"国漫"） → query

## 用户问题
{user_input}

## 历史上下文
{context_text}

只输出意图类型名称（小写），不要其他任何内容："""
    
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
            "description": """你好！我是番剧智能助手，一个专注于日本动画番剧的AI助手。

你可以叫我"番剧小助手"，我的主要职责是帮助你：
🎬 查询番剧信息
📺 了解番剧详情
🔥 发现热门番剧
⭐ 获取个性化推荐

有什么番剧想了解的吗？""",
            "capability": """我可以帮助你：
1. 📋 查询番剧信息 - 根据时间、类型、平台搜索番剧
2. 📖 了解番剧详情 - 获取特定番剧的剧情介绍
3. 🔥 查看热门排行 - 了解当前最受欢迎的番剧
4. 🔍 关键词搜索 - 搜索特定番剧信息

请告诉我你想了解什么？""",
            "thanks": "不客气！很高兴能帮到你。还有什么想了解的吗？",
            "unknown": "抱歉，我不太理解你的意思。我是番剧智能助手，专注于帮助你查询日本动画番剧的信息。你可以这样问我：\n\n- '推荐几部好看的日漫'\n- '《进击的巨人》剧情介绍'\n- '2024年评分最高的番剧有哪些'\n\n请问有什么番剧想了解的吗？"
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
    
    # ==================== 智能体化意图识别 Prompt ====================
    
    @staticmethod
    def get_agent_intent_prompt(user_input: str, context_text: str = "") -> str:
        """智能体化意图识别 Prompt - 企业级版本
        
        特点：
        1. 角色定义 - 明确智能体身份
        2. Chain of Thought - 引导LLM进行思考
        3. Few-Shot示例 - 提供正反例
        4. 输出格式约束 - JSON格式确保解析稳定
        
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
        
        return f"""## 角色定义
你是一个专业的意图识别专家，专门负责分析用户对番剧查询的意图。你的判断必须准确、严谨。

## 任务
分析用户问题，判断其真实意图类型，并给出你的思考过程。

## 意图类型定义
| 意图类型 | 说明 | 典型示例 |
|---------|------|---------|
| greeting | 打招呼、问好 | "你好"、"嗨"、"早上好" |
| description | 询问智能体身份/自我介绍 | "你是谁"、"你叫什么" |
| capability | 询问智能体能力/功能 | "你能做什么"、"你有什么用" |
| query | 查询番剧列表（主要意图） | "推荐番剧"、"搜索日漫" |
| detail | 获取特定番剧详情 | "《进击的巨人》怎么样" |
| ranking | 查看排行榜 | "热门排行"、"评分最高" |
| recommend | 推荐番剧 | "有什么推荐" |
| compare | 对比番剧 | "《A》和《B》哪个好" |
| thanks | 感谢 | "谢谢" |
| chat | 闲聊 | "今天天气" |
| unknown | 无法理解/无意义输入 | "你是水"、"123" |

## 思维链要求（Chain of Thought）
请按以下步骤思考：
1. 首先，用户说的是什么？（字面意思）
2. 其次，用户真正想要什么？（深层意图）
3. 最后，应该归类为什么意图？（分类决策）

## 判断规则（重要！）
1. 如果用户问"你是谁"、"你叫什么"、"介绍一下自己" → description
2. 如果用户问"你能做什么"、"你有什么用" → capability
3. 如果用户说无意义的内容（如"你是水"、单个字符、纯符号） → unknown
4. 如果用户提到具体番剧名（如《xxx》） → detail
5. 如果用户提到番剧类型（如"日漫"、"国漫"） → query

## Few-Shot 示例（帮助你理解判断标准）
【示例1】
输入: "最近有什么好看的番剧推荐吗？"
思维链: 用户想要找番剧，提到"推荐"，意图是"推荐"
输出: {{"intent": "recommend", "reasoning": "用户想要获取番剧推荐，属于推荐意图"}}

【示例2】
输入: "《进击的巨人》讲的是什么故事？"
思维链: 用户提到具体番剧名"《进击的巨人》"，想要了解详情
输出: {{"intent": "detail", "reasoning": "用户明确提到番剧名称，想要获取该番剧的详细信息"}}

【示例3】
输入: "2024年10月新番有哪些？"
思维链: 用户询问特定时间的番剧列表，属于查询
输出: {{"intent": "query", "reasoning": "用户询问特定时间的番剧列表，属于查询意图"}}

【示例4】
输入: "b站最热的番剧排行"
思维链: 用户想看排行榜，提到"排行"和"最热"
输出: {{"intent": "ranking", "reasoning": "用户明确想看排行版，属于排行榜意图"}}

【示例5】
输入: "你是谁？"
思维链: 用户询问智能体身份
输出: {{"intent": "description", "reasoning": "用户询问智能体身份，属于描述意图"}}

【示例6】
输入: "aaa"
思维链: 用户输入无意义字符，无法理解
输出: {{"intent": "unknown", "reasoning": "用户输入无意义内容，无法识别具体意图"}}

## 用户问题
{user_input}
{context_hint}

## 输出要求
请严格按照以下JSON格式输出，不要输出其他任何内容：
{{"intent": "意图类型", "reasoning": "你的思考过程（20字以内）"}}"""
    
    # ==================== 智能体化参数提取 Prompt ====================
    
    @staticmethod
    def get_agent_params_prompt(user_input: str, intent: str, context_text: str = "") -> str:
        """智能体化参数提取 Prompt - 企业级版本
        
        特点：
        1. 明确参数定义和约束
        2. 丰富的Few-Shot示例
        3. 常见错误提醒
        4. 输出格式规范
        
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
        
        return f"""## 角色定义
你是一个专业的参数提取专家，专门从用户的查询中提取结构化的查询参数。你的提取必须准确、完整。

## 任务
从用户问题中提取查询参数。

## 参数定义
| 参数 | 类型 | 说明 | 可选值 |
|-----|------|------|-------|
| anime_type | string | 番剧类型 | 日漫、国漫、剧场版、OVA、all |
| time_range | string | 时间范围 | 2026-03、本月、最新、2026春等 |
| sort_by | string | 排序方式 | rating（评分）、hot（热门）、latest（最新） |
| platform | string | 数据平台 | jikan、anilist、bangumi、bilibili、all |
| keyword | string | 关键词 | 用户提到的具体番剧名或搜索词 |

## 参数提取规则
### anime_type（番剧类型）
- "国漫"、"国产动画"、"国产动漫" → "国漫"
- "日漫"、"日本动画"、"日本动漫" → "日漫"
- "剧场版"、"电影版"、"动画电影" → "剧场版"
- "OVA"、"OAD" → "OVA"
- 没有提到任何类型 → "all"

### time_range（时间范围）
- "2026-03"、"2026年3月" → "2026-03"
- "本月"、"这个月" → "本月"
- "最新"、"最近" → "最新"
- "2026春"、"春季" → "2026春"

### sort_by（排序方式）
- "最热"、"热门"、"火" → "hot"
- "最新"、"新番" → "latest"
- "评分"、"高分"、"推荐" → "rating"

## 正例示例（正确示范）
【示例1】
输入: "推荐几部国漫"
思考: 用户明确提到"国漫"
输出: {{"anime_type": "国漫", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例2】
输入: "2024年7月有哪些日漫"
思考: 用户提到"2024年7月"表示时间，"日漫"表示类型
输出: {{"anime_type": "日漫", "time_range": "2024-07", "sort_by": "rating", "platform": "all", "keyword": ""}}

【示例3】
输入: "剧场版电影有哪些"
思考: "电影"对应"剧场版"
输出: {{"anime_type": "剧场版", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例4】
输入: "有什么番剧推荐"
思考: 用户没有提到任何类型，使用默认值
输出: {{"anime_type": "all", "sort_by": "rating", "platform": "all", "time_range": "", "keyword": ""}}

【示例5】
输入: "本月最新的热门番剧"
思考: "本月"=time_range，"热门"=sort_by为hot
输出: {{"anime_type": "all", "time_range": "本月", "sort_by": "hot", "platform": "all", "keyword": ""}}

【示例6】
输入: "最近火的国产动画"
思考: "国产动画"=国漫，"最近"=最新，"火"=hot
输出: {{"anime_type": "国漫", "time_range": "最新", "sort_by": "hot", "platform": "all", "keyword": ""}}

## 反例示例（常见错误，请避免）
【错误1】
输入: "我想看动漫电影"
错误: "电影"应纠正为"剧场版"
正确: {{"anime_type": "剧场版", ...}}

【错误2】
输入: "2024年的新番"
错误: "新番"需要判断时间范围
正确: {{"anime_type": "all", "sort_by": "latest", "platform": "all", "time_range": "2024", "keyword": ""}}

【错误3】
输入: "日本动漫"
错误: "日本动漫"应该识别为"日漫"
正确: {{"anime_type": "日漫", ...}}

## 用户问题
{user_input}
意图类型: {intent}
{context_hint}

## 输出要求
只输出JSON格式，不要输出其他任何内容："""
    
    # ==================== 自反思 Prompt ====================
    
    @staticmethod
    def get_self_reflect_prompt(
        user_input: str, 
        current_intent: str, 
        reasoning: str,
        context_text: str = ""
    ) -> str:
        """自反思 Prompt - 用于置信度低时的二次校验
        
        当LLM首次识别置信度较低时，触发自反思机制：
        1. 重新审视用户输入
        2. 检查当前意图是否正确
        3. 考虑是否有更合适的意图
        
        Args:
            user_input: 用户输入
            current_intent: 当前识别的意图
            reasoning: 当前推理过程
            context_text: 历史上下文
            
        Returns:
            完整的 prompt 字符串
        """
        context_hint = ""
        if context_text:
            context_hint = f"""
## 历史上下文
{context_text}"""
        
        return f"""## 角色定义
你是一个严谨的意图审查专家。你的任务是重新审视之前的意图识别结果，确保判断准确无误。

## 任务背景
你之前对用户问题进行了意图识别，但置信度较低，需要重新审视。

## 之前识别结果
- 用户问题: {user_input}
- 识别出的意图: {current_intent}
- 识别理由: {reasoning}
{context_hint}

## 重新审视要求
请重新分析这个用户问题，回答以下问题：
1. 当前的意图判断是否正确？
2. 是否有其他更合适的意图类型？
3. 用户的真实意图可能是什么？

## 意图类型参考
| 意图类型 | 说明 |
|---------|------|
| greeting | 打招呼 |
| description | 询问身份 |
| capability | 询问能力 |
| query | 番剧查询 |
| detail | 番剧详情 |
| ranking | 排行榜 |
| recommend | 推荐 |
| compare | 对比 |
| thanks | 感谢 |
| chat | 闲聊 |
| unknown | 无法理解 |

## 输出要求
请严格按照以下JSON格式输出：
{{"intent": "修正后的意图（如果不需要修正则与之前相同）", "reasoning": "重新思考后的理由"}}"""
