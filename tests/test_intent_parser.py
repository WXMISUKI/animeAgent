# 意图解析模块测试文件

import sys
sys.path.insert(0, '.')

from src.agent.intent import IntentParser, IntentType, IntentTypeConfig, SlotDefinition

# 测试用例
TEST_CASES = [
    # 意图识别测试
    ("推荐国漫", "意图识别"),
    ("《夏目友人帐》的评分", "意图识别"),
    ("有没有好看的日漫排行榜", "意图识别"),
    ("帮我找一下剧情介绍", "意图识别"),
    ("你好", "意图识别"),
    ("有什么功能", "意图识别"),
    
    # 参数提取测试
    ("推荐几部国漫", "参数提取"),
    ("2024年7月有哪些日漫", "参数提取"),
    ("剧场版电影有哪些", "参数提取"),
    ("本月最新的热门番剧", "参数提取"),
    ("最近火的国产动画", "参数提取"),
]

def test_intent_keyword_match():
    """测试关键词匹配意图"""
    print("=" * 50)
    print("测试1: 关键词匹配意图")
    print("=" * 50)
    
    test_inputs = [
        "推荐几部国漫",
        "《夏目友人帐》的评分",
        "有没有好看的日漫排行榜",
        "帮我找一下剧情介绍",
        "你好",
        "有什么功能",
        "谢谢",
    ]
    
    for text in test_inputs:
        result = IntentTypeConfig.keyword_match(text)
        print(f"「{text}」→ 意图: {result}")
    print()

def test_param_template():
    """测试参数模板"""
    print("=" * 50)
    print("测试2: 参数模板")
    print("=" * 50)
    
    intents = ["query", "detail", "ranking", "recommend", "compare"]
    for intent in intents:
        template = IntentTypeConfig.get_param_template(intent)
        print(f"{intent}: {template}")
    print()

def test_slot_definition():
    """测试槽位定义"""
    print("=" * 50)
    print("测试3: 槽位定义")
    print("=" * 50)
    
    print(f"DEFINITIONS keys: {list(SlotDefinition.DEFINITIONS.keys())}")
    print(f"anime_type enum: {SlotDefinition.DEFINITIONS['anime_type'].get('enum')}")
    print(f"sort_by enum: {SlotDefinition.DEFINITIONS['sort_by'].get('enum')}")
    print()

def test_intent_parser():
    """测试IntentParser类"""
    print("=" * 50)
    print("测试4: IntentParser方法")
    print("=" * 50)
    
    parser = IntentParser(None)
    
    # 检查方法是否存在
    methods = [m for m in dir(parser) if not m.startswith('__')]
    print(f"IntentParser方法: {methods}")
    
    # 检查关键方法
    key_methods = [
        '_quick_match',
        '_extract_params', 
        '_astream_extract_params',
        '_rule_based_extract',
        '_validate_and_correct_params',
        '_parse_json',
        '_get_direct_response'
    ]
    
    for method in key_methods:
        exists = hasattr(parser, method)
        print(f"  {method}: {'✅' if exists else '❌'}")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("意图解析模块测试")
    print("=" * 50 + "\n")
    
    try:
        test_intent_keyword_match()
        test_param_template()
        test_slot_definition()
        test_intent_parser()
        
        print("=" * 50)
        print("✅ 所有测试完成!")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()