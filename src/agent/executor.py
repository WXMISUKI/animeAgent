"""执行器模块"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("Executor")


class Executor:
    """执行器
    
    负责执行工具并返回结果
    """
    
    def __init__(self, tool_map: Dict):
        self.tool_map = tool_map
    
    async def execute(self, plan: List[Dict]) -> List[Dict]:
        """执行计划
        
        Args:
            plan: 执行计划列表
            
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
                logger.info(f"✅ 工具 {tool_name} 执行成功")
                
            except Exception as e:
                error_msg = str(e)
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": error_msg,
                    "params": tool_params
                })
                
                logger.error(f"❌ 工具 {tool_name} 执行失败: {error_msg}")
        
        return results
