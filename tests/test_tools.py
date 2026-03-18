"""工具测试"""

import pytest
from src.agent.tools import (
    QueryAnimeTool,
    GetAnimeDetailTool,
    GetAnimeRankingTool,
    create_tools
)


class TestQueryAnimeTool:
    """番剧查询工具测试"""
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = QueryAnimeTool()
        
        assert tool.name == "query_anime"
        assert tool.description is not None
        assert len(tool.description) > 0
    
    def test_tool_parameters(self):
        """测试工具参数"""
        tool = QueryAnimeTool()
        
        # 验证参数 schema
        schema = tool.args_schema.model_json_schema()
        
        assert "time_range" in schema["properties"]
        assert "platform" in schema["properties"]
        assert "anime_type" in schema["properties"]
        assert "sort_by" in schema["properties"]
        assert "keyword" in schema["properties"]


class TestGetAnimeDetailTool:
    """番剧详情工具测试"""
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = GetAnimeDetailTool()
        
        assert tool.name == "get_anime_detail"
    
    def test_tool_parameters(self):
        """测试工具参数"""
        tool = GetAnimeDetailTool()
        
        schema = tool.args_schema.model_json_schema()
        
        assert "anime_id" in schema["properties"]


class TestGetAnimeRankingTool:
    """番剧排行榜工具测试"""
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = GetAnimeRankingTool()
        
        assert tool.name == "get_anime_ranking"


class TestCreateTools:
    """工具创建测试"""
    
    def test_create_all_tools(self):
        """测试创建所有工具"""
        tools = create_tools()
        
        assert len(tools) >= 3  # 至少3个基础工具
        
        tool_names = [tool.name for tool in tools]
        
        assert "query_anime" in tool_names
        assert "get_anime_detail" in tool_names
        assert "get_anime_ranking" in tool_names
    
    def test_tool_map_creation(self):
        """测试工具映射创建"""
        tools = create_tools()
        tool_map = {tool.name: tool for tool in tools}
        
        assert len(tool_map) == len(tools)
        assert "query_anime" in tool_map
