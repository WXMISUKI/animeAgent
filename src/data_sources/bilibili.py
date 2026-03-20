# data_sources/bilibili.py
"""Bilibili 数据源适配器

使用 B 站公开 API 接口：
- 番剧索引: https://api.bilibili.com/pgc/season/index/result
- 番剧排行榜: https://api.bilibili.com/pgc/web/rank/v2/list?season_type=1
- 番剧搜索: https://api.bilibili.com/x/web-interface/search/type?keyword=xxx&search_type=media_bangumi
- 番剧详情: https://api.bilibili.com/pgc/view/web/season?season_id=xxx
"""

import aiohttp
import json
import logging
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams

logger = logging.getLogger("BilibiliAPI")


class BilibiliAPI(AnimeDataSource):
    """Bilibili 数据源
    
    B站公开 API 接口
    """
    
    BASE_URL = "https://api.bilibili.com"
    NAME = "Bilibili"
    
    # 中文类型映射 (season_type: 1=番剧, 2=电影, 3=纪录片, 4=国创, 5=综艺)
    CHINESE_TYPE_MAP = {
        "日漫": 1,
        "TV": 1,
        "动画": 1,
        "国漫": 4,
        "国创": 4,
        "剧场版": 2,
        "电影": 2,
        "OVA": 1,
        "OAD": 1,
        "特别篇": 1,
        "SP": 1,
        "纪录片": 3,
        "综艺": 5,
    }
    
    def _parse_anime_type(self, anime_type: str) -> int:
        """解析动画类型为 B站 season_type"""
        if not anime_type or anime_type == "all":
            return 1  # 默认番剧
        return self.CHINESE_TYPE_MAP.get(anime_type, 1)
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """搜索番剧"""
        
        logger.info(f"🔍 [BilibiliAPI] search 开始")
        logger.info(f"   params: anime_type={params.anime_type}, keyword={params.keyword}, time_range={params.time_range}, platform={params.platform}")
        
        # 直接从 anime_type 和 keyword 检测是否国漫
        is_chinese_anime = False
        search_keyword = ""
        
        # 检测 anime_type
        if params.anime_type in ["国漫", "国产", "国创"]:
            is_chinese_anime = True
            logger.info(f"   🎯 从 anime_type 检测到国漫")
        
        # 检测 keyword 是否包含国漫关键词
        if params.keyword and any(kw in params.keyword for kw in ["国漫", "国产", "国创", "中国"]):
            is_chinese_anime = True
            search_keyword = params.keyword
            logger.info(f"   🎯 从 keyword 检测到国漫: {params.keyword}")
        
        # 解析动画类型
        anime_type = self._parse_anime_type(params.anime_type)
        logger.info(f"📌 [BilibiliAPI] 解析后的 season_type={anime_type}")
        
        # 根据排序方式选择不同的 API
        sort_by = params.sort_by or "latest"
        
        # 国漫/国产/国创：强制使用搜索接口
        if is_chinese_anime:
            logger.info(f"🎯 [BilibiliAPI] 检测到国漫查询，使用专门搜索接口")
            result = await self._search_by_chinese_anime(params, anime_type, search_keyword)
        elif sort_by == "hot" or sort_by == "rating":
            # 使用排行榜接口
            logger.info(f"📊 [BilibiliAPI] 使用排行榜接口")
            result = await self._get_ranking(params, anime_type)
        elif params.keyword:
            # 使用搜索接口
            logger.info(f"🔍 [BilibiliAPI] 使用搜索接口")
            result = await self._search(params, anime_type)
        else:
            # 使用番剧索引接口
            logger.info(f"📋 [BilibiliAPI] 使用番剧索引接口")
            result = await self._get_index(params, anime_type)
        
        logger.info(f"✅ [BilibiliAPI] search 完成, 返回 {len(result)} 条数据")
        
        # 打印返回的数据摘要
        if result:
            for item in result[:3]:
                logger.info(f"📝 [BilibiliAPI] 返回数据: {item.name} ({item.platform}) 评分:{item.rating}")
        else:
            logger.warning(f"⚠️ [BilibiliAPI] 返回数据为空!")
        
        return result
    
    async def _search_by_chinese_anime(self, params: QueryParams, anime_type: int = 4, search_keyword: str = "") -> list[AnimeInfo]:
        """专门搜索国漫/国产动画
        
        使用 B站搜索接口，搜索关键词包括：国漫、国产动画、国产动漫
        """
        
        # 如果有传入 keyword，优先使用
        if search_keyword:
            keywords = [search_keyword]
        else:
            # 国漫搜索关键词
            keywords = ["国漫", "国产动画", "国产动漫", "国创"]
        
        url = f"{self.BASE_URL}/x/web-interface/search/type"
        
        all_results = []
        
        for keyword in keywords:
            params_dict = {
                "search_type": "media_bangumi",  # 使用番剧搜索
                "keyword": keyword,
                "page": 1,
                "page_size": 20,
            }
            
            logger.info(f"🔍 [BilibiliAPI] _search_by_chinese_anime 搜索: {keyword}")
            logger.info(f"   URL: {url}")
            logger.info(f"   参数: {json.dumps(params_dict, ensure_ascii=False)}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params_dict,
                        timeout=aiohttp.ClientTimeout(total=10),
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": "https://www.bilibili.com",
                            "Accept": "application/json, text/plain, */*",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                        }
                    ) as resp:
                        status = resp.status
                        
                        # 检查返回类型
                        content_type = resp.headers.get("Content-Type", "")
                        logger.info(f"📥 [BilibiliAPI] 响应: 状态码={status}, Content-Type={content_type}")
                        
                        # 如果不是 JSON，返回错误
                        if "application/json" not in content_type:
                            text = await resp.text()
                            logger.warning(f"⚠️ [BilibiliAPI] 返回非JSON: {text[:200]}")
                            continue
                        
                        data = await resp.json()
                        
                        logger.info(f"📥 [BilibiliAPI] _search_by_chinese_anime 响应: 状态码={status}, code={data.get('code')}")
                        
                        # 打印完整响应用于调试
                        response_str = json.dumps(data, ensure_ascii=False)
                        logger.info(f"   响应({len(response_str)}字符): {response_str[:1000]}")
                        
                        if status != 200 or data.get("code") != 0:
                            logger.warning(f"⚠️ [BilibiliAPI] API返回错误: code={data.get('code')}, message={data.get('message')}")
                            continue
                        
                        # B站搜索结果结构
                        items = data.get("data", {}).get("result", [])
                        if not items:
                            items = data.get("data", {}).get("list", []) or []
                        
                        logger.info(f"📊 [BilibiliAPI] 关键词 '{keyword}' 找到 {len(items)} 条结果")
                        
                        for item in items:
                            anime = self._parse_search_result(item)
                            # 去重
                            if not any(a.id == anime.id for a in all_results):
                                all_results.append(anime)
                                
            except Exception as e:
                logger.error(f"💥 [BilibiliAPI] _search_by_chinese_anime 异常: {str(e)}")
        
        logger.info(f"✅ [BilibiliAPI] _search_by_chinese_anime 完成, 共 {len(all_results)} 条去重结果")
        return all_results
    
    async def _get_index(self, params: QueryParams, anime_type: int = 1) -> list[AnimeInfo]:
        """获取番剧索引/列表
        
        B站番剧索引 API: https://api.bilibili.com/pgc/season/index/result
        """
        
        # 排序映射
        sort_map = {
            "latest": "2",  # 更新时间
            "hot": "1",     # 播放量
            "rating": "3"   # 评分
        }
        
        season_type = anime_type
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
            import re
            match = re.match(r"(\d{4})-?(\d{2})?", params.time_range)
            if match:
                year, month = match.groups()
                if year:
                    params_dict["year"] = year
                if month:
                    params_dict["month"] = month
        
        logger.info(f"🔍 [BilibiliAPI] _get_index 请求:")
        logger.info(f"   URL: {url}")
        logger.info(f"   参数: {json.dumps(params_dict, ensure_ascii=False)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    status = resp.status
                    data = await resp.json()
                    
                    logger.info(f"📥 [BilibiliAPI] _get_index 响应:")
                    logger.info(f"   状态码: {status}")
                    logger.info(f"   响应内容: {json.dumps(data, ensure_ascii=False)[:1000]}")
                    
                    if status != 200:
                        logger.warning(f"❌ [BilibiliAPI] HTTP错误: {status}")
                        return []
                    
                    if data.get("code") != 0:
                        logger.warning(f"❌ [BilibiliAPI] API错误: {data.get('message')}")
                        return []
                    
                    items = data.get("data", {}).get("list", [])
                    logger.info(f"📊 [BilibiliAPI] 获取到 {len(items)} 条数据")
                    
                    return [self._parse_anime(item) for item in items]
                    
        except Exception as e:
            logger.error(f"💥 [BilibiliAPI] _get_index 异常: {str(e)}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return []
    
    async def _get_ranking(self, params: QueryParams, anime_type: int = 1) -> list[AnimeInfo]:
        """获取排行榜"""
        
        # 排序类型: 1=播放指数, 2=追番指数, 3=评分指数
        rank_type_map = {
            "hot": 1,     # 播放指数
            "rating": 3,  # 评分指数
        }
        
        season_type = anime_type
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
    
    async def _search(self, params: QueryParams, anime_type: int = 1) -> list[AnimeInfo]:
        """搜索番剧
        
        B站搜索 API: https://api.bilibili.com/x/web-interface/search/type
        """
        
        url = f"{self.BASE_URL}/x/web-interface/search/type"
        
        # 根据类型选择搜索类型
        search_type_map = {
            1: "media_bangumi",   # 番剧
            2: "media_bangumi",   # 电影
            3: "media_documentary", # 纪录片
            4: "media_bangumi",   # 国创（使用番剧搜索）
            5: "media_variety",   # 综艺
        }
        
        # 构建关键词
        keyword = params.keyword
        if not keyword:
            # 根据 anime_type 构建关键词
            if anime_type == 4:  # 国创
                keyword = "国漫 国产动画"
            elif anime_type == 2:  # 电影
                keyword = "剧场版 动画电影"
            else:
                keyword = "番剧 日本动画"
        
        params_dict = {
            "search_type": search_type_map.get(anime_type, "media_bangumi"),
            "keyword": keyword,
            "page": 1,
            "page_size": 20,
        }
        
        logger.info(f"🔍 [BilibiliAPI] _search 请求:")
        logger.info(f"   URL: {url}")
        logger.info(f"   参数: {json.dumps(params_dict, ensure_ascii=False)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params_dict,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    status = resp.status
                    data = await resp.json()
                    
                    logger.info(f"📥 [BilibiliAPI] _search 响应:")
                    logger.info(f"   状态码: {status}")
                    logger.info(f"   响应内容: {json.dumps(data, ensure_ascii=False)[:1000]}")
                    
                    if status != 200:
                        logger.warning(f"❌ [BilibiliAPI] HTTP错误: {status}")
                        return []
                    
                    if data.get("code") != 0:
                        logger.warning(f"❌ [BilibiliAPI] API错误: {data.get('message')}")
                        return []
                    
                    # B站搜索结果在 data.result 中
                    items = data.get("data", {}).get("result", [])
                    logger.info(f"📊 [BilibiliAPI] 搜索到 {len(items)} 条结果")
                    
                    if not items:
                        # 尝试其他字段
                        items = data.get("data", {}).get("list", []) or []
                        logger.info(f"📊 [BilibiliAPI] 尝试 list 字段，找到 {len(items)} 条结果")
                    
                    return [self._parse_search_result(item) for item in items]
                    
        except Exception as e:
            logger.error(f"💥 [BilibiliAPI] _search 异常: {str(e)}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
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
