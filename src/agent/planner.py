"""计划生成器模块"""

import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI

logger = logging.getLogger("Planner")


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
        
        Args:
            intent: 意图类型
            params: 查询参数
            
        Returns:
            [
                {"tool": "query_anime", "params": {...}},
                {"tool": "get_anime_detail", "params": {...}}
            ]
        """
        # 根据意图类型生成计划
        if intent == "query":
            return [self._plan_query(params)]
        elif intent == "detail":
            return [self._plan_detail(params)]
        elif intent == "ranking":
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
