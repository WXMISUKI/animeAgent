# data_sources/baidu_search.py
"""百度搜索 API 数据源

百度智能云千帆搜索 API
文档: https://cloud.baidu.com/doc/ISAT/SDK-Notes.html
"""

import os
import aiohttp
from typing import List, Optional, Dict, Any
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class BaiduSearchAPI(AnimeDataSource):
    """百度搜索 API 数据源"""
    
    BASE_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"
    NAME = "BaiduSearch"
    
    def __init__(self):
        self.api_key = os.getenv("BAIDU_SEARCH_API_KEY", "")
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """通过百度搜索获取番剧信息
        
        当其他数据源无法找到结果时，使用此方法搜索互联网
        """
        
        # 构建搜索关键词
        keyword = params.keyword
        if not keyword:
            # 从时间范围构建关键词
            if params.time_range:
                keyword = f"{params.time_range} 番剧"
            else:
                keyword = "热门番剧 推荐"
        
        try:
            results = await self._search_web(keyword)
            return self._parse_search_results(results, keyword)
        except Exception as e:
            print(f"[BaiduSearchAPI] 搜索失败: {e}")
            return []
    
    async def _search_web(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """调用百度搜索 API
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        
        if not self.api_key:
            print("[BaiduSearchAPI] 未配置 API Key")
            return []
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        body = {
            "messages": [
                {
                    "content": query,
                    "role": "user"
                }
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [
                {"type": "web", "top_k": max_results}
            ],
            "search_recency_filter": "year"  # 最近一年
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"[BaiduSearchAPI] API 返回错误: {resp.status} - {text}")
                        return []
                    
                    data = await resp.json()
                    return self._extract_results(data)
                    
        except Exception as e:
            print(f"[BaiduSearchAPI] 请求失败: {e}")
            return []
    
    def _extract_results(self, data: Dict) -> List[Dict[str, Any]]:
        """从 API 响应中提取结果"""
        
        results = []
        
        try:
            # 百度搜索返回的结构
            # data.answer[0].knowledge_graph 或 data.web_page_results
            answer = data.get("answer", [])
            if answer:
                # 知识图谱结果
                kg = answer[0].get("knowledge_graph", {})
                if kg:
                    entities = kg.get("entities", [])
                    for entity in entities:
                        results.append({
                            "title": entity.get("name", ""),
                            "content": entity.get("description", ""),
                            "url": entity.get("url", "")
                        })
            
            # 网页结果
            web_results = data.get("web_page_results", [])
            for item in web_results:
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("snippet", ""),
                    "url": item.get("url", "")
                })
                
        except Exception as e:
            print(f"[BaiduSearchAPI] 解析结果失败: {e}")
        
        return results
    
    def _parse_search_results(self, results: List[Dict], query: str) -> list[AnimeInfo]:
        """解析搜索结果为 AnimeInfo"""
        
        anime_list = []
        
        for item in results:
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            
            # 跳过无效结果
            if not title or len(title) < 2:
                continue
            
            # 创建 AnimeInfo 对象
            anime = AnimeInfo(
                id=f"baidu_{hash(title) % 100000}",
                name=title,
                name_cn=title,
                air_date="",
                rating=None,
                summary=content[:200] if content else "",
                platform="BaiduSearch",
                source_url=url,
                cover_url=None
            )
            anime_list.append(anime)
        
        return anime_list
    
    async def get_detail(self, anime_id: str) -> Optional[AnimeInfo]:
        """获取搜索结果中的番剧详情"""
        
        # 从搜索结果中获取，此功能暂不实现
        return None


# 快捷函数
async def search_anime(keyword: str, max_results: int = 10) -> list[AnimeInfo]:
    """搜索番剧
    
    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        
    Returns:
        番剧信息列表
    """
    api = BaiduSearchAPI()
    params = QueryParams(keyword=keyword)
    return await api.search(params)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("测试百度搜索 API...")
        
        # 设置 API Key（实际使用时从环境变量读取）
        # os.environ["BAIDU_SEARCH_API_KEY"] = "your-api-key"
        
        api = BaiduSearchAPI()
        
        print("\n1. 搜索 '違国日記 番剧':")
        results = await api._search_web("違国日記 番剧")
        print(f"   找到 {len(results)} 条结果")
        for item in results[:3]:
            print(f"   - {item.get('title')}: {item.get('content')[:50]}...")
    
    asyncio.run(test())