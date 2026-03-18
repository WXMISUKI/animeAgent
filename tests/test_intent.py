"""意图识别测试"""

import pytest
from src.llm.client import MiniMaxClient


class TestIntentClassification:
    """意图分类测试"""
    
    def test_greeting_keywords(self):
        """测试打招呼关键词识别"""
        client = MiniMaxClient()
        
        test_cases = [
            "你好",
            "hi",
            "hello",
            "早上好",
            "在吗"
        ]
        
        for query in test_cases:
            result = client.classify_intent(query)
            assert result["response_mode"] == "direct", f"'{query}' 应识别为直接回复"
            assert result["needs_fetch"] is False
    
    def test_thanks_keywords(self):
        """测试感谢关键词识别"""
        client = MiniMaxClient()
        
        test_cases = [
            "谢谢",
            "感谢",
            "好的，明白了"
        ]
        
        for query in test_cases:
            result = client.classify_intent(query)
            assert result["response_mode"] == "direct", f"'{query}' 应识别为直接回复"
    
    def test_query_intent(self):
        """测试查询意图识别"""
        client = MiniMaxClient()
        
        test_cases = [
            "最近有什么好看的番剧？",
            "2024年7月有哪些新番？",
            "推荐几部热血番剧"
        ]
        
        for query in test_cases:
            result = client.classify_intent(query)
            assert result["intent_type"] in ["query", "detail", "ranking"]


class TestDirectResponse:
    """直接回复测试"""
    
    def test_greeting_response(self):
        """测试打招呼回复"""
        client = MiniMaxClient()
        response = client.get_direct_response("greeting")
        assert len(response) > 0
        assert isinstance(response, str)
    
    def test_thanks_response(self):
        """测试感谢回复"""
        client = MiniMaxClient()
        response = client.get_direct_response("thanks")
        assert len(response) > 0
    
    def test_unknown_intent(self):
        """测试未知意图的默认回复"""
        client = MiniMaxClient()
        response = client.get_direct_response("unknown")
        assert len(response) > 0
