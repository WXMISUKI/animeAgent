"""数据源路由器 - 增强版（支持容错、熔断、重试）"""

import asyncio
import logging
import time
from typing import List, Dict, Optional
from .base import AnimeDataSource
from ..models.anime_info import AnimeInfo
from ..models.query_params import QueryParams

logger = logging.getLogger("DataSourceRouter")


class CircuitBreaker:
    """熔断器 - 防止故障数据源持续调用"""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold  # 连续失败次数阈值
        self.recovery_timeout = recovery_timeout  # 恢复超时（秒）
        self.failure_count = {}  # 每个数据源的失败计数
        self.last_failure_time = {}  # 上次失败时间
        self.state = {}  # 数据源状态: "closed", "open", "half_open"
    
    def is_available(self, source_name: str) -> bool:
        """检查数据源是否可用"""
        if source_name not in self.state:
            self.state[source_name] = "closed"
            return True
        
        state = self.state[source_name]
        
        if state == "closed":
            return True
        
        if state == "open":
            # 检查是否超时可以进入半开状态
            if source_name in self.last_failure_time:
                elapsed = time.time() - self.last_failure_time[source_name]
                if elapsed > self.recovery_timeout:
                    self.state[source_name] = "half_open"
                    logger.info(f"🔄 数据源 {source_name} 进入半开状态")
                    return True
            return False
        
        if state == "half_open":
            return True
        
        return True
    
    def record_success(self, source_name: str):
        """记录成功调用"""
        self.failure_count[source_name] = 0
        self.state[source_name] = "closed"
    
    def record_failure(self, source_name: str):
        """记录失败调用"""
        self.failure_count[source_name] = self.failure_count.get(source_name, 0) + 1
        self.last_failure_time[source_name] = time.time()
        
        if self.failure_count[source_name] >= self.failure_threshold:
            self.state[source_name] = "open"
            logger.warning(f"🛑 数据源 {source_name} 触发熔断，失败次数: {self.failure_count[source_name]}")


class DataSourceRouter:
    """数据源路由器 - 增强版
    
    特性：
    - 支持多数据源并行查询
    - 超时重试机制
    - 熔断降级
    - 结果校验
    - 日志记录
    
    支持的平台:
    - "jikan": Jikan API (MyAnimeList 数据源)
    - "anilist": AniList API (全球动漫数据源)
    - "bangumi": Bangumi API (中文番剧数据)
    - "all": 同时查询 Jikan + AniList (默认)
    """
    
    # 平台名称到数据源名称的映射（优先级排序）
    PLATFORM_MAP = {
        "jikan": ["Jikan"],
        "anilist": ["AniList"],
        "bangumi": ["Bangumi"],
        "all": ["Jikan", "AniList"],  # 默认查询 Jikan + AniList
    }
    
    # 平台别名（兼容旧版本）
    ALIAS_MAP = {
        "bilibili": "all",
        "iqiyi": "all",
        "tencent": "all",
    }
    
    def __init__(
        self, 
        sources: List[AnimeDataSource],
        timeout: int = 3,
        max_retries: int = 2,
        use_circuit_breaker: bool = True
    ):
        self.sources = sources
        self.source_map = {source.NAME: source for source in sources}
        
        # 容错配置
        self.timeout = timeout  # 超时时间（秒）
        self.max_retries = max_retries  # 最大重试次数
        
        # 熔断器
        self.circuit_breaker = CircuitBreaker() if use_circuit_breaker else None
    
    async def search(self, params: QueryParams) -> list[AnimeInfo]:
        """查询数据源
        
        流程：
        1. 选择数据源（根据平台参数 + 熔断状态）
        2. 并行查询（带超时和重试）
        3. 合并结果并去重
        4. 结果校验
        """
        
        # 获取平台参数（处理别名）
        platform = params.platform or "all"
        platform = self.ALIAS_MAP.get(platform, platform)
        
        # 获取要查询的数据源列表
        source_names = self.PLATFORM_MAP.get(platform, self.PLATFORM_MAP["all"])
        
        # 过滤出可用的数据源
        sources_to_query = []
        unavailable_sources = []
        
        for name in source_names:
            if name not in self.source_map:
                continue
            
            # 检查熔断器
            if self.circuit_breaker and not self.circuit_breaker.is_available(name):
                unavailable_sources.append(name)
                continue
            
            sources_to_query.append(self.source_map[name])
        
        # 如果所有数据源都不可用，记录警告
        if not sources_to_query and unavailable_sources:
            logger.warning(f"⚠️ 所有目标数据源均不可用: {unavailable_sources}，尝试使用备用数据源")
            # 降级：使用所有可用的数据源
            sources_to_query = [
                s for s in self.sources
                if not self.circuit_breaker or self.circuit_breaker.is_available(s.NAME)
            ]
        
        # 如果仍然没有可用数据源
        if not sources_to_query:
            logger.error("❌ 没有可用的数据源")
            return []
        
        # 并行查询所有选中的数据源
        results = await self._fetch_all(sources_to_query, params)
        
        # 合并结果并去重
        merged = self._merge_results(results)
        
        # 结果校验
        validated = self._validate_results(merged)
        
        return validated
    
    async def _fetch_all(
        self, 
        sources: List[AnimeDataSource], 
        params: QueryParams
    ) -> List[List[AnimeInfo]]:
        """并行查询所有数据源（带超时和重试）"""
        
        async def fetch_with_retry(source: AnimeDataSource):
            """带重试的查询"""
            last_error = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    # 检查熔断器
                    if self.circuit_breaker and not self.circuit_breaker.is_available(source.NAME):
                        return []
                    
                    # 执行查询（带超时）
                    result = await asyncio.wait_for(
                        source.search(params),
                        timeout=self.timeout
                    )
                    
                    # 记录成功
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success(source.NAME)
                    
                    logger.info(f"✅ {source.NAME} 查询成功，返回 {len(result)} 条结果")
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = "超时"
                    logger.warning(f"⏱️ {source.NAME} 查询超时 (尝试 {attempt + 1}/{self.max_retries + 1})")
                    
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"❌ {source.NAME} 查询失败: {e} (尝试 {attempt + 1}/{self.max_retries + 1})")
                
                # 重试间隔
                if attempt < self.max_retries:
                    await asyncio.sleep(1)  # 1秒后重试
            
            # 记录失败
            if self.circuit_breaker:
                self.circuit_breaker.record_failure(source.NAME)
            
            logger.error(f"❌ {source.NAME} 查询最终失败: {last_error}")
            return []
        
        # 并行执行
        results = await asyncio.gather(
            *[fetch_with_retry(s) for s in sources],
            return_exceptions=True
        )
        
        # 过滤异常结果
        return [r for r in results if isinstance(r, list)]
    
    def _merge_results(self, results: List[List[AnimeInfo]]) -> List[AnimeInfo]:
        """合并去重"""
        seen = set()
        merged = []
        
        for result_list in results:
            for anime in result_list:
                if anime.id not in seen:
                    seen.add(anime.id)
                    merged.append(anime)
        
        # 按评分排序
        return sorted(merged, key=lambda x: x.rating or 0, reverse=True)
    
    def _validate_results(self, results: List[AnimeInfo]) -> List[AnimeInfo]:
        """校验结果"""
        if not results:
            return results
        
        validated = []
        for anime in results:
            # 基本校验：必须有 ID 和名称
            if not anime.id or not anime.name:
                logger.warning(f"⚠️ 跳过无效番剧数据: {anime}")
                continue
            validated.append(anime)
        
        # 如果校验后结果大量减少，记录警告
        if len(validated) < len(results) * 0.5:
            logger.warning(f"⚠️ 结果校验过滤较多数据: {len(results)} -> {len(validated)}")
        
        return validated
    
    def get_status(self) -> Dict[str, str]:
        """获取数据源状态"""
        if not self.circuit_breaker:
            return {s.NAME: "normal" for s in self.sources}
        
        return {
            name: self.circuit_breaker.state.get(name, "closed")
            for name in self.source_map.keys()
        }