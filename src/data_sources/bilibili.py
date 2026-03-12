# data_sources/bilibili.py
"""Bilibili 数据源适配器

使用 B 站公开 API 接口：
- 番剧索引: https://api.bilibili.com/pgc/season/index/result
- 番剧排行榜: https://api.bilibili.com/pgc/web/rank/v2/list?season_type=1
- 番剧搜索: https://api.bilibili.com/x/web-interface/search/type?keyword=xxx&search_type=media_bangumi
- 番剧详情: https://api.bilibili.com/pgc/view/web/season?season_id=xxx
"""

import aiohttp
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams


class BilibiliAPI(AnimeDataSource):
    """Bilibili 数据源"""
    
    BASE_URL = "https://api.bilibili.com"
    NAME = "Bilibili"
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        # 根据排序方式选择不同的 API
        sort_by = params.sort_by or "latest"
        
        if sort_by == "hot" or sort_by == "rating":
            # 使用排行榜接口
            return await self._get_ranking(params)
        elif params.keyword:
            # 使用搜索接口
            return await self._search(params)
        else:
            # 使用番剧索引接口
            return await self._get_index(params)
    
    async def _get_index(self, params: QueryParams) -> list[AnimeInfo]:
        """获取番剧索引/列表"""
        
        # 类型映射 (season_type: 1=番剧, 2=电影(?), 3=纪录片(?), 4=国创(?), 5=综艺(?))
        type_map = {
            "日漫": 1,
            "国漫": 4,  # 国创
            "all": 1,
            "剧场版": 2,
        }
        
        # 排序映射
        sort_map = {
            "latest": "2",  # 更新时间
            "hot": "1",     # 播放量
            "rating": "3"   # 评分
        }
        
        season_type = type_map.get(params.anime_type, 1)
        sort = sort_map.get(params.sort_by, "2")
        
        url = f"{self.BASE_URL}/pgc/season/index/result"
        
        params_dict = {
            "season_type": season_type,
            "sort": sort,
            "page": 1,
            "page_size": 20,
        }
        
        # 时间范围处理
        if params.time_range:
            # 解析时间范围，如 "2026-02" -> year=2026, month=2
            import re
            match = re.match(r"(\d{4})-?(\d{2})?", params.time_range)
            if match:
                year, month = match.groups()
                if year:
                    params_dict["year"] = year
                if month:
                    params_dict["month"] = month
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status != 200:
                        print(f"[BilibiliAPI] 请求失败: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    
                    # 检查 API 返回
                    if data.get("code") != 0:
                        print(f"[BilibiliAPI] API错误: {data.get('message')}")
                        return []
                    
                    items = data.get("data", {}).get("list", [])
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            print(f"[BilibiliAPI] 查询失败: {e}")
            return []
    
    async def _get_ranking(self, params: QueryParams) -> list[AnimeInfo]:
        """获取排行榜"""
        
        # 类型映射
        type_map = {
            "日漫": 1,
            "国漫": 4,
            "all": 1,
        }
        
        # 排序类型: 1=播放指数, 2=追番指数, 3=评分指数
        rank_type_map = {
            "hot": 1,     # 播放指数
            "rating": 3,  # 评分指数
        }
        
        season_type = type_map.get(params.anime_type, 1)
        rank_type = rank_type_map.get(params.sort_by, 1)
        
        # 时间范围: 1=昨日, 3=三日, 7=一周
        day_map = {
            "昨日": 1,
            "3日": 3,
            "7日": 7,
            "本周": 7,
        }
        
        day = 7  # 默认一周
        if params.time_range:
            day = day_map.get(params.time_range, 7)
        
        url = f"{self.BASE_URL}/pgc/web/rank/v2/list"
        params_dict = {
            "season_type": season_type,
            "day": day,
            "type": rank_type
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    
                    if data.get("code") != 0:
                        print(f"[BilibiliAPI] 排行榜API错误: {data.get('message')}")
                        return []
                    
                    items = data.get("data", {}).get("list", [])
                    return [self._parse_anime(item) for item in items[:20]]
                    
        except Exception as e:
            print(f"[BilibiliAPI] 排行榜查询失败: {e}")
            return []
    
    async def _search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        url = f"{self.BASE_URL}/x/web-interface/search/type"
        
        params_dict = {
            "search_type": "media_bangumi",
            "keyword": params.keyword or params.time_range or "番剧",
            "page": 1,
            "page_size": 20,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    
                    if data.get("code") != 0:
                        return []
                    
                    items = data.get("data", {}).get("result", [])
                    return [self._parse_search_result(item) for item in items]
                    
        except Exception as e:
            print(f"[BilibiliAPI] 搜索失败: {e}")
            return []
    
    def _parse_anime(self, raw: dict) -> AnimeInfo:
        """解析番剧索引/排行榜数据"""
        
        # 处理评分
        rating = raw.get("rating")
        if rating:
            rating = float(rating.get("score", 0)) if isinstance(rating, dict) else float(rating)
        
        # 处理封面
        cover = raw.get("cover")
        
        # 处理标题
        title = raw.get("title", "")
        title_cn = raw.get("title", "")
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('season_id', raw.get('id', ''))}",
            name=title,
            name_cn=title_cn,
            air_date=raw.get("publish_date", raw.get("finish_time", "")),
            rating=rating,
            summary=raw.get("desc", ""),
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('season_id', raw.get('id', ''))}/",
            cover_url=cover
        )
    
    def _parse_search_result(self, raw: dict) -> AnimeInfo:
        """解析搜索结果"""
        
        # 处理评分
        rating = raw.get("score")
        if rating:
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None
        
        # 处理封面
        cover = raw.get("cover")
        
        # 处理标题
        title = raw.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", "")
        
        return AnimeInfo(
            id=f"bilibili_{raw.get('media_id', '')}",
            name=title,
            name_cn=title,
            air_date=raw.get("pubdate", ""),
            rating=rating,
            summary=raw.get("description", ""),
            platform="Bilibili",
            source_url=f"https://www.bilibili.com/bangumi/media/md{raw.get('media_id', '')}/",
            cover_url=cover
        )
    
    async def get_detail(self, anime_id: str) -> AnimeInfo | None:
        """获取番剧详情"""
        
        season_id = anime_id.replace("bilibili_", "")
        
        url = f"{self.BASE_URL}/pgc/view/web/season"
        params_dict = {"season_id": season_id}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if data.get("code") != 0:
                        return None
                    
                    raw = data.get("data", {})
                    return self._parse_detail(raw)
                    
        except Exception as e:
            print(f"[BilibiliAPI] 详情查询失败: {e}")
            return None
    
    def _parse_detail(self, raw: dict) -> AnimeInfo:
        """解析详情数据"""
        
        # 处理评分
        rating = None
        rating_info = raw.get("rating", {})
        if rating_info:
            try:
                rating = float(rating_info.get("score", 0))
            except (ValueError, TypeError):
                pass
        
        # 处理封面
        cover = raw.get("cover")
        
        # 处理标题
        title = raw.get("title", "")
        
        # 处理简介
        summary = raw.get("evaluate", "")
        
        # 处理播出信息
        air_date = ""
        pub_info = raw.get("pub_time", {})
        if pub_info:
            air_date = str(pub_info.get("date", ""))
        
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
