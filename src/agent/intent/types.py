"""意图类型定义 - 增强版"""

from enum import Enum


class IntentType(Enum):
    """意图类型枚举"""
    GREETING = "greeting"           # 打招呼
    DESCRIPTION = "description"     # 询问身份/自我介绍
    CAPABILITY = "capability"       # 询问能力
    QUERY = "query"                 # 番剧查询
    DETAIL = "detail"               # 番剧详情
    RANKING = "ranking"             # 排行榜
    RECOMMEND = "recommend"         # 推荐
    COMPARE = "compare"             # 对比
    THANKS = "thanks"               # 感谢
    CHAT = "chat"                   # 闲聊
    UNKNOWN = "unknown"             # 无法理解/无意义输入
    
    @property
    def value(self):
        return self._value_
    
    @property
    def label(self):
        """意图中文标签"""
        labels = {
            "greeting": "打招呼",
            "description": "询问身份",
            "capability": "询问能力",
            "query": "番剧查询",
            "detail": "番剧详情",
            "ranking": "排行榜",
            "recommend": "推荐",
            "compare": "对比",
            "thanks": "感谢",
            "chat": "闲聊",
            "unknown": "无法理解"
        }
        return labels.get(self.value, self.value)


class IntentTypeConfig:
    """意图类型配置管理器"""
    
    # 所有意图类型列表
    ALL = [
        IntentType.GREETING,
        IntentType.DESCRIPTION,
        IntentType.CAPABILITY,
        IntentType.QUERY,
        IntentType.DETAIL,
        IntentType.RANKING,
        IntentType.RECOMMEND,
        IntentType.COMPARE,
        IntentType.THANKS,
        IntentType.CHAT,
        IntentType.UNKNOWN
    ]
    
    # 需要数据的意图
    NEEDS_DATA = [IntentType.QUERY, IntentType.DETAIL, IntentType.RANKING]
    
    # 直接回复意图（无需数据查询）
    DIRECT_REPLY = [IntentType.GREETING, IntentType.DESCRIPTION, IntentType.CAPABILITY, IntentType.THANKS, IntentType.UNKNOWN]
    
    # 意图关键词兜底映射（优先级：精准关键词 > 模糊关键词）
    INTENT_KEYWORDS = {
        IntentType.DETAIL: ["详情", "评分", "介绍", "角色", "声优", "制作", "《", "讲什么", "怎么样", "多少分"],
        IntentType.RANKING: ["排行", "榜单", "top", "热门榜", "评分榜", "排行榜", "最火", "最热", "最高分"],
        IntentType.RECOMMEND: ["推荐", "好看的", "值得看", "安利", "必看"],
        IntentType.COMPARE: ["对比", "哪个好", "和...比", "比较", "差异"],
        IntentType.QUERY: ["查询", "搜索", "找找", "有哪些", "有什么", "看看"],
        IntentType.CAPABILITY: ["功能", "能做什么", "会什么", "你可以", "你是谁", "你是谁啊", "是什么", "干嘛的", "叫什么", "什么机器人", "什么助手", "智能体", "身份"],
        IntentType.GREETING: ["你好", "哈喽", "hi", "hello", "早上好", "晚安", "在吗", "嗨"],
        IntentType.THANKS: ["谢谢", "感谢", "多谢", "好的"],
        IntentType.CHAT: ["闲聊", "聊聊", "随便说", "聊天", "今天天气"],
        IntentType.UNKNOWN: ["你是水", "嗯啊", "123", "？？", "aaa", "测试"]  # 无意义输入模式
    }
    
    # 意图参数模板配置
    INTENT_PARAM_TEMPLATES = {
        IntentType.QUERY: {
            "required": [],
            "optional": ["anime_type", "time_range", "sort_by", "platform", "keyword"]
        },
        IntentType.DETAIL: {
            "required": ["keyword"],
            "optional": ["platform"]
        },
        IntentType.RANKING: {
            "required": [],
            "optional": ["anime_type", "time_range", "sort_by", "platform"]
        },
        IntentType.RECOMMEND: {
            "required": [],
            "optional": ["anime_type", "time_range", "sort_by", "platform", "preference"]
        },
        IntentType.COMPARE: {
            "required": ["keyword"],
            "optional": ["compare_dimension"]
        }
    }
    
    @classmethod
    def get_all_values(cls) -> list:
        """获取所有意图类型值"""
        return [i.value for i in cls.ALL]
    
    @classmethod
    def is_valid(cls, intent: str) -> bool:
        """检查意图是否有效"""
        return intent in cls.get_all_values()
    
    @classmethod
    def needs_data(cls, intent: str) -> bool:
        """检查意图是否需要数据"""
        return intent in [i.value for i in cls.NEEDS_DATA]
    
    @classmethod
    def is_direct_reply(cls, intent: str) -> bool:
        """检查意图是否直接回复"""
        return intent in [i.value for i in cls.DIRECT_REPLY]
    
    @classmethod
    def get_param_template(cls, intent: str) -> dict:
        """获取意图的参数模板"""
        intent_type = IntentType(intent) if isinstance(intent, str) else intent
        return cls.INTENT_PARAM_TEMPLATES.get(intent_type, cls.INTENT_PARAM_TEMPLATES[IntentType.QUERY])
    
    @classmethod
    def keyword_match(cls, user_input: str) -> str:
        """通过关键词匹配意图"""
        for intent_type, keywords in cls.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_input:
                    return intent_type.value
        return IntentType.QUERY.value  # 默认查询
