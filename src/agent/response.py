"""响应生成器模块"""

import json
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger("ResponseGenerator")


class ResponseStyle:
    """响应风格"""
    CONCISE = "concise"      # 简洁
    DETAILED = "detailed"   # 详细
    CASUAL = "casual"       # 口语化
    PROFESSIONAL = "professional"  # 专业


class ResponseGenerator:
    """响应生成器 - 增强版
    
    特性：
    - 多风格响应（简洁/详细/口语化/专业）
    - 结果聚合去重
    - 个性化响应（基于会话上下文）
    """
    
    # 风格对应的 prompt
    STYLE_PROMPTS = {
        ResponseStyle.CONCISE: """请用简洁的方式回答，包含：
- 番剧名称
- 评分（如有）
- 数据来源（如：Bilibili，Jikan，Bangumi）
- 一句话介绍

重要：每条结果必须标注数据来源！""",
        
        ResponseStyle.DETAILED: """请用详细的方式回答，每部番剧包含：
- 番剧名称（原名）
- 评分和评价人数
- 播出时间
- 剧情简介（50字内）
- 标签
- 数据来源（必须标注：如 Bilibili，Jikan，Bangumi）
使用清晰的分隔符分隔每部番剧。

重要：每条结果必须标注数据来源！""",
        
        ResponseStyle.CASUAL: """请用轻松、口语化的方式回答，像朋友推荐一样：
- 用 emoji 让内容更生动
- 适当加入个人感受
- 语气亲切自然
- 不要太正式

重要：每条结果必须标注数据来源（如：📺 数据来源：Bilibili）！""",
        
        ResponseStyle.PROFESSIONAL: """请用专业、客观的方式回答：
- 使用规范的术语
- 数据准确引用
- 结构化呈现
- 适当加入数据对比

重要：必须标注每条结果的数据来源（Bilibili/Jikan/Bangumi/AniList）"""
    }
    
    def __init__(self, llm: ChatOpenAI, default_style: str = ResponseStyle.CASUAL):
        self.llm = llm
        self.default_style = default_style
    
    async def generate(
        self, 
        user_input: str, 
        intent: str, 
        tool_results: List[Dict],
        style: str = None
    ) -> str:
        """生成响应文本（非流式）
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            tool_results: 工具执行结果
            style: 响应风格（concise/detailed/casual/professional）
        """
        
        # 如果没有工具结果
        if not tool_results:
            return "抱歉，我没有找到相关信息。你可以换个关键词试试？"
        
        # 检查是否有成功的结果
        success_results = [r for r in tool_results if r.get("success")]
        
        if not success_results:
            return "抱歉，查询过程中出现了问题。请稍后重试。"
        
        # 收集结果数据
        results_data = []
        for r in success_results:
            if r.get("result"):
                try:
                    data = json.loads(r["result"])
                    if isinstance(data, list):
                        results_data.extend(data)
                    else:
                        results_data.append(data)
                except:
                    results_data.append(r.get("result"))
        
        # 获取风格提示
        response_style = style or self.default_style
        style_prompt = self.STYLE_PROMPTS.get(response_style, self.STYLE_PROMPTS[ResponseStyle.CASUAL])
        
        # 使用LLM生成自然语言回复
        prompt = f"""用户问题: {user_input}

番剧查询结果:
{json.dumps(results_data[:10], ensure_ascii=False, indent=2)}

{style_prompt}

注意：只输出回复内容，不要输出其他解释。"""

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            response = await self.llm.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            return f"我找到了相关信息，但回复生成有点问题。请查看以下结果：\n\n{results_data[:5]}"

    async def astream_generate(
        self, 
        user_input: str, 
        intent: str, 
        tool_results: List[Dict],
        style: str = None
    ):
        """异步流式生成响应 - 每次 LLM 输出 chunk 时立即 yield
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            tool_results: 工具执行结果
            style: 响应风格（concise/detailed/casual/professional）
        """
        
        # 如果没有工具结果
        if not tool_results:
            yield "抱歉，我没有找到相关信息。你可以换个关键词试试？"
            return
        
        # 检查是否有成功的结果
        success_results = [r for r in tool_results if r.get("success")]
        
        if not success_results:
            yield "抱歉，查询过程中出现了问题。请稍后重试。"
            return
        
        # 收集结果数据
        results_data = []
        for r in success_results:
            if r.get("result"):
                try:
                    data = json.loads(r["result"])
                    if isinstance(data, list):
                        results_data.extend(data)
                    else:
                        results_data.append(data)
                except:
                    results_data.append(r.get("result"))
        
        # 获取风格提示
        response_style = style or self.default_style
        style_prompt = self.STYLE_PROMPTS.get(response_style, self.STYLE_PROMPTS[ResponseStyle.CASUAL])
        
        # 使用LLM生成自然语言回复
        prompt = f"""用户问题: {user_input}

番剧查询结果:
{json.dumps(results_data[:10], ensure_ascii=False, indent=2)}

{style_prompt}

注意：只输出回复内容，不要输出其他解释。"""

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            # 使用 astream 方法实现真正的流式输出
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            yield f"我找到了相关信息，但回复生成有点问题。请查看以下结果：\n\n{results_data[:5]}"