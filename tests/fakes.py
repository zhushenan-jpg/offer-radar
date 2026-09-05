"""测试用假响应构造器。

用 openai SDK 的真实类型构造响应对象,保证 instructor 的任何内省
(model_dump / role / tool_calls 等)都与生产行为一致;仅替换
chat.completions.create 注入假响应,不触网。
"""

import json

from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice

TEST_BASE_URL = "http://localhost:9999/v1"


class FakeChatCompletions:
    """responder(kwargs) -> ChatCompletion;记录全部调用供断言."""

    def __init__(self, responder):
        self._responder = responder
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responder(kwargs)


def make_client(responder) -> OpenAI:
    """真实 OpenAI 客户端 + 假 completions;responder(kwargs) 返回 ChatCompletion."""
    client = OpenAI(api_key="test-key", base_url=TEST_BASE_URL)
    client.chat.completions = FakeChatCompletions(responder)
    return client


def _completion(message: ChatCompletionMessage, usage: dict | None) -> ChatCompletion:
    return ChatCompletion(
        id="cmpl-1",
        object="chat.completion",
        created=1700000000,
        model="glm-5.3-flash",
        choices=[Choice(index=0, finish_reason="stop", message=message)],
        usage=usage or {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )


def tool_call_completion(payload: dict, usage: dict | None = None) -> ChatCompletion:
    """instructor TOOLS 模式期望的响应形式."""
    message = ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[
            ChatCompletionMessageToolCall(
                id="call_1",
                type="function",
                function={"name": "respond", "arguments": json.dumps(payload, ensure_ascii=False)},
            )
        ],
    )
    return _completion(message, usage)


def text_completion(
    content: str, reasoning: str | None = None, usage: dict | None = None
) -> ChatCompletion:
    message = ChatCompletionMessage(role="assistant", content=content)
    if reasoning is not None:
        message.reasoning_content = reasoning  # GLM 兼容层的额外字段(extra=allow)
    return _completion(message, usage)


def no_tools_responder(responder):
    """模拟不支持 tools 的服务端:instructor 的调用直接抛错 → 触发网关手动回退."""

    def wrapped(kwargs):
        if "tools" in kwargs:
            raise TypeError("server does not support tools")
        return responder(kwargs)

    return wrapped
