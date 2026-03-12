# data_sources/bilibili_sdk.py
"""Bilibili 数据源适配器 - 使用 bilibili-api-python SDK

SDK 文档: https://bilibili-api-python.readthedocs.io/
安装: pip install bilibili-api-python
"""

import asyncio
from typing import List, Optional
from bilibili_api import bangumi, search
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class BilibiliSDKAPI(AnimeDataSource):
    """Bilibili 数据源 - 使用官方 SDK"""
    
    NAME = "Bilibili"
    
    # season_type: 1=番剧, 4=国创
    TYPE_MAP = {
        "日漫": 1,
        "国漫": 4,
        "all": 1,
        "剧场版": 3,
    }
    
    # 排序方式映射
    SORT_MAP = {
        "hot": "0",     # 播放
        "rating": "1",  # 评分
        "latest": "2",  # 更新时间
    }
    
    def __init__(self):
        # SDK 会自动处理 cookie 和签名
        pass
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        # 根据参数选择不同的查询方式
        if params.sort_by == "hot" or params.sort_by == "rating":
            return await self._get_ranking(params)
        elif params.keyword:
            return await self._search(params)
        else:
            return await self._get_index(params)
    
    async def _get_index(self, params: QueryParams) -> list[AnimeInfo]:
        """获取番剧索引/列表"""
        
        try:
            # 使用 get_index_info 方法，这是正确的 API
            # 构建过滤条件
            filters = {}
            
            # 类型过滤
            if params.anime_type == "日漫":
                filters["type"] = 1  # 番剧
            elif params.anime_type == "国漫":
                filters["type"] = 4  # 国创
            else:
                filters["type"] = 1  # 默认番剧
                
            # 时间范围过滤
            if params.time_range:
                import re
                match = re.match(r"(\d{4})-?(\d{2})?", params.time_range)
                if match:
                    year, month = match.groups()
                    if year:
                        filters["year"] = int(year)
                    if month:
                        filters["month"] = int(month)
            
            # 排序
            if params.sort_by == "latest":
                filters["order"] = 2  # 更新时间
            elif params.sort_by == "hot":
                filters["order"] = 1  # 播放量
            elif params.sort_by == "rating":
                filters["order"] = 3  # 评分
                
            result = await bangumi.get_index_info(
                filters=filters,
                page=1,
                pagesize=20
            )
            
            items = result.get("items", []) if isinstance(result, dict) else []
            return [self._parse_anime(item) for item in items]
            
        except Exception as e:
            print(f"[BilibiliSDKAPI] 获取番剧列表失败: {e}")
            return []
    
    async def _get_ranking(self, params: QueryParams) -> list[AnimeInfo]:
        """获取排行榜"""
        
        season_type = self.TYPE_MAP.get(params.anime_type, 1)
        
        # day: 1=昨日, 3=三日, 7=一周
        day = 7
        if params.time_range:
            if "昨日" in params.time_range:
                day = 1
            elif "3日" in params.time_range:
                day = 3
        
        try:
            # 获取排行榜
            rank = await bangumi.get_rank(
                season_type=season_type,
                day=day
            )
            
            items = rank.get("list", []) if isinstance(rank, dict) else []
            return [self._parse_anime(item) for item in items[:20]]
            
        except Exception as e:
            print(f"[BilibiliSDKAPI] 获取排行榜失败: {e}")
            return []
    
    async def _search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        keyword = params.keyword or params.time_range or "番剧"
        
        try:
            # 使用 SDK 搜索
            result = await search.search_by_type(
                keyword=keyword,
                search_type=search.SearchObjectType.BANGUMI,
                page=1,
                pagesize=20
            )
            
            items = result.get("result", []) if isinstance(result, dict) else []
            return [self._parse_search_result(item) for item in items]
            
        except Exception as e:
            print(f"[BilibiliSDKAPI] 搜索失败: {e}")
            return []
    
    async def get_detail(self, anime_id: str) -> Optional[AnimeInfo]:
        """获取番剧详情"""
        
        season_id = anime_id.replace("bilibili_", "")
        
        try:
            season_id = int(season_id)
        except ValueError:
            print(f"[BilibiliSDKAPI] 无效的 season_id: {anime_id}")
            return None
        
        try:
            info = await bangumi.get_season_info(season_id=season_id)
            return self._parse_detail(info)
            
        except Exception as e:
            print(f"[BilibiliSDKAPI] 获取详情失败: {e}")
            return None
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析番剧数据"""
        
        # 处理评分
        rating = None
        rating_info = raw.get("rating")
        if rating_info:
            try:
                rating = float(rating_info.get("score", 0))
            except (ValueError, TypeError, AttributeError):
                pass
        
        # 处理封面
        cover = raw.get("cover")
        
        # 处理标题
        title = raw.get("title", "")
        
        # 处理简介
        summary = raw.get("desc", "")
        
        # 处理日期
        air_date = raw.get("pub_time", raw.get("finish_time", ""))
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('season_id', raw.get('id', ''))}",
            name=title,
            name_cn=title,
            air_date=str(air_date) if air_date else "",
            rating=rating,
            summary=summary,
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('season_id', raw.get('id', ''))}/",
            cover_url=cover
        )
    
    def _parse_search_result(self, raw: dict) -> AnimeInfo:
        """解析搜索结果"""
        
        # 处理评分
        rating = None
        score = raw.get("score")
        if score:
            try:
                rating = float(score)
            except (ValueError, TypeError):
                pass
        
        # 处理标题
        title = raw.get("title", "")
        # 清理 HTML 标签
        if isinstance(title, str):
            title = title.replace("<em class=\"keyword\">", "").replace("</em>", "")
        
        # 处理封面
        cover = raw.get("cover")
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('media_id', '')}",
            name=title,
            name_cn=title,
            air_date=str(raw.get("pubdate", "")),
            rating=rating,
            summary=raw.get("description", ""),
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('media_id', '')}/",
            cover_url=cover
        )
    
    def _parse_detail(self, raw: dict) -> AnimeInfo:
        """解析详情数据"""
        
        # 处理评分
        rating = None
        rating_info = raw.get("rating")
        if rating_info:
            try:
                rating = float(rating_info.get("score", 0))
            except (ValueError, TypeError, AttributeError):
                pass
        
        # 处理标题
        title = raw.get("title", "")
        
        # 处理简介
        summary = raw.get("evaluate", "")
        
        # 处理封面
        cover = raw.get("cover")
        
        # 处理日期
        pub_time = raw.get("pub_time")
        if isinstance(pub_time, dict):
            air_date = pub_time.get("date", "")
        else:
            air_date = str(pub_time) if pub_time else ""
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('season_id', '')}",
            name=title,
            name_cn=title,
            air_date=air_date,
            rating=rating,
            summary=summary,
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('season_id', '')}/",
            cover_url=cover
        )


# 快捷函数 - 直接获取排行榜
async def get_bilibili_rank(season_type: int = 1, day: int = 7) -> List[AnimeInfo]:
    """获取 B 站番剧排行榜
    
    Args:
        season_type: 1=番剧, 4=国创
        day: 1=昨日, 3=三日, 7=一周
    
    Returns:
        番剧信息列表
    """
    api = BilibiliSDKAPI()
    params = QueryParams(anime_type="日漫" if season_type == 1 else "国漫", sort_by="hot")
    return await api._get_ranking(params)


# 快捷函数 - 获取番剧详情
async def get_bilibili_detail(season_id: int) -> Optional[AnimeInfo]:
    """获取 B 站番剧详情
    
    Args:
        season_id: 番剧 ID
    
    Returns:
        番剧详情
    """
    api = BilibiliSDKAPI()
    return await api.get_detail(f"bilibili_{season_id}")


if __name__ == "__main__":
    async def test():
        # 测试获取排行榜
        print("获取番剧周榜...")
        rank = await get_bilibili_rank(season_type=1, day=7)
        print(f"找到 {len(rank)} 部番剧")
        for anime in rank[:5]:
            print(f"  - {anime.name}: {anime.rating}分")
        
        # 测试获取详情
        if rank:
            print(f"\n获取《{rank[0].name}》详情...")
            detail = await get_bilibili_detail(int(rank[0].id.replace("bilibili_", "")))
            if detail:
                print(f"  标题: {detail.name}")
                print(f"  评分: {detail.rating}")
                print(f"  简介: {detail.summary[:50]}...")
    
    asyncio.run(test())