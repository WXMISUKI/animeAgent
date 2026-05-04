# llm/client.py
"""LLM 客户端 - 豆包大模型"""

import os
import json
import re
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .prompts import (
    INTENT_PROMPT,
    FORMAT_PROMPT,
    INTENT_CLASSIFY_PROMPT,
    SYSTEM_PROMPT,
    DIRECT_RESPONSE_TEMPLATES,
    INTENT_KEYWORDS
)

logger = logging.getLogger("LLMClient")


def create_llm(
    temperature: float = 0.7,
    max_tokens: int = 2000,
    streaming: bool = False,
):
    """创建豆包 LLM 实例"""
    return ChatOpenAI(
        model=os.getenv("ORCH_MODEL", ""),
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        base_url=os.getenv("ORCH_API_BASE", "https://ark.cn-beijing.volces.com/api/v3"),
        api_key=os.getenv("ORCH_API_KEY", ""),
    )


class LLMClient:
    """豆包 LLM 客户端"""

    def __init__(self):
        self.client = create_llm(temperature=0.7, max_tokens=2000)
        self.intent_client = create_llm(temperature=0.1, max_tokens=500)

    def classify_intent(self, query: str) -> dict:
        """意图分类 - 先用关键词快速匹配，失败则调用 LLM"""

        query_lower = query.lower()

        # 快速关键词匹配
        for intent_type, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    # 匹配成功，返回分类结果
                    if intent_type in ["greeting", "identity", "capability", "thanks"]:
                        return {
                            "intent_type": intent_type,
                            "needs_fetch": False,
                            "response_mode": "direct",
                            "params": {}
                        }
                    elif intent_type in ["detail", "ranking"]:
                        return {
                            "intent_type": intent_type,
                            "needs_fetch": True,
                            "response_mode": "skill",
                            "params": {}
                        }

        # 关键词匹配失败，调用 LLM 进行智能判断
        messages = [
            SystemMessage(content=INTENT_CLASSIFY_PROMPT),
            HumanMessage(content=f"用户查询：{query}")
        ]

        response = self.intent_client.invoke(messages)
        result = self._parse_json_response(response.content)

        # 提取意图类型和响应模式
        intent_type = result.get("intent_type", "chat")
        needs_fetch = result.get("needs_fetch", False)
        response_mode = result.get("response_mode", "direct" if not needs_fetch else "skill")

        return {
            "intent_type": intent_type,
            "needs_fetch": needs_fetch,
            "response_mode": response_mode,
            "params": result.get("params", {})
        }

    def get_direct_response(self, intent_type: str) -> str:
        """获取直接回复内容"""
        return DIRECT_RESPONSE_TEMPLATES.get(intent_type, "你好！有什么可以帮你的吗？")

    def chat_with_system(self, query: str, context: list = None) -> str:
        """使用系统提示词进行对话"""
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # 添加历史上下文
        if context:
            recent = context[-6:] if len(context) > 6 else context
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=query))

        response = self.client.invoke(messages)
        return response.content
    
    def parse_intent(self, query: str, context: list = None) -> dict:
        """解析用户意图"""
        
        context_str = ""
        if context:
            # 取最近3轮对话
            recent = context[-6:] if len(context) > 6 else context
            context_str = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent
            ])
        
        messages = [
            SystemMessage(content=INTENT_PROMPT),
            HumanMessage(content=f"用户查询：{query}\n\n历史上下文：{context_str}")
        ]
        
        response = self.intent_client.invoke(messages)
        
        # 解析 JSON 响应
        return self._parse_json_response(response.content)
    
    def format_response(self, query: str, anime_data: list) -> str:
        """格式化番剧数据"""
        
        messages = [
            SystemMessage(content=FORMAT_PROMPT),
            HumanMessage(content=f"用户查询：{query}\n\n番剧数据：{json.dumps(anime_data, ensure_ascii=False)}")
        ]
        
        response = self.client.invoke(messages)
        
        return response.content
    
    def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """通用对话接口"""

        chat_client = create_llm(temperature=temperature, max_tokens=max_tokens)
        
        # 转换消息格式
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        response = chat_client.invoke(langchain_messages)
        return response.content
    
    def stream_chat(self, messages: list, temperature: float = 0.7):
        """流式对话"""

        chat_client = create_llm(temperature=temperature, max_tokens=2000, streaming=True)
        
        # 转换消息格式
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        for chunk in chat_client.stream(langchain_messages):
            if chunk.content:
                yield chunk.content
    
    def _parse_json_response(self, content: str) -> dict:
        """解析 JSON 响应，包含回退机制"""
        
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 回退：尝试提取 JSON 块
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # 最终回退：返回原始内容
        return {"raw": content, "error": "JSON解析失败"}
