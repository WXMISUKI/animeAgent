"""pytest 配置文件"""

import pytest
import sys
import os

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def mock_env():
    """模拟环境变量"""
    original_env = os.environ.copy()
    
    os.environ["ORCH_API_KEY"] = "test-api-key"
    os.environ["ORCH_API_BASE"] = "https://test.example.com/v1"
    os.environ["ORCH_MODEL"] = "MiniMax/MiniMax-M2.5"
    
    yield os.environ
    
    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_anime_data():
    """示例番剧数据"""
    return [
        {
            "id": "jikan_1",
            "name": "Spy x Family",
            "name_cn": "间谍过家家",
            "air_date": "2022-04-09",
            "rating": 8.6,
            "summary": "为了潜入名校...",
            "platform": "Jikan"
        },
        {
            "id": "jikan_2",
            "name": "Frieren",
            "name_cn": "葬送的芙莉莲",
            "air_date": "2023-09-30",
            "rating": 9.0,
            "summary": "这是关于魔法使...",
            "platform": "Jikan"
        }
    ]
