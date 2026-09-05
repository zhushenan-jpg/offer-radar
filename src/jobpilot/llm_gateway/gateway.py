"""LLM 网关:全项目唯一 LLM 入口。

通道:instructor(tools 模式)为主,失败回退"纯 JSON prompt + 校验错误回喂"。
职责:GLM 接入、<think>/reasoning_content 剥离、缓存、token 计量、月度预算硬保险。
"""

import hashlib
import re
from typing import TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .exceptions import BudgetExceeded, GatewaySchemaError

T = TypeVar("T", bound=BaseModel)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def sanitize_content(content: str | None) -> str:
    """GLM thinking 恒开:<think> 块与 reasoning_content 字段一律剥离."""
    return _THINK_RE.sub("", content or "").strip()


def extract_json(text: str) -> str:
    text = sanitize_content(text)
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return text


class LLMGateway:
    def __init__(self, cfg, storage=None, client: OpenAI | None = None):
        self.cfg = cfg
        self.storage = storage
        self._client = client or OpenAI(
            base_url=cfg.base_url,
            api_key=cfg.api_key.get_secret_value(),
            timeout=cfg.timeout_s,
        )
        self._instructor = instructor.from_openai(self._client)

    # ---- 预算与计量 ----
    def _budget_check(self) -> None:
        if self.storage and self.storage.usage.month_cost() >= self.cfg.monthly_budget_cny:
            raise BudgetExceeded(
                f"当月费用已达 ¥{self.storage.usage.month_cost():.2f},"
                f"超过预算 ¥{self.cfg.monthly_budget_cny:.2f},批处理终止"
            )

    def _meter(self, module: str, completion=None, cache_hit: bool = False) -> None:
        if self.storage is None:
            return
        pt = ct = 0
        cost = 0.0
        if completion is not None and getattr(completion, "usage", None) is not None:
            pt = completion.usage.prompt_tokens or 0
            ct = completion.usage.completion_tokens or 0
            cost = (
                pt * self.cfg.price_input_cny_per_mtok + ct * self.cfg.price_output_cny_per_mtok
            ) / 1e6
        self.storage.usage.record(
            module, self.cfg.model, pt, ct, round(cost, 6), 1 if cache_hit else 0
        )

    def _store_cache(self, cache_key: str | None, obj: BaseModel) -> None:
        if cache_key and self.storage is not None:
            self.storage.cache.put(cache_key, obj.model_dump_json())

    def _messages(self, prompt: str, system: str) -> list[dict]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    # ---- 公共入口 ----
    def json_in(
        self,
        schema: type[T],
        prompt: str,
        *,
        system: str = "",
        cache_key: str | None = None,
        module: str = "",
    ) -> T:
        self._budget_check()
        if cache_key and self.storage is not None:
            raw = self.storage.cache.get(cache_key)
            if raw is not None:
                self._meter(module, None, cache_hit=True)
                return schema.model_validate_json(raw)
        try:
            obj, completion = self._instructor.chat.completions.create_with_completion(
                model=self.cfg.model,
                response_model=schema,
                messages=self._messages(prompt, system),
                temperature=self.cfg.temperature,
                top_p=self.cfg.top_p,
                # instructor 内部重试关闭:重试与错误回喂统一由 _manual_json 管理
                max_retries=1,
            )
            self._meter(module, completion)
            self._store_cache(cache_key, obj)
            return obj
        except Exception:  # noqa: BLE001 - instructor 失败形态多样,统一交给回退通道处理
            return self._manual_json(schema, prompt, system, cache_key, module)

    def _manual_json(
        self,
        schema: type[T],
        prompt: str,
        system: str,
        cache_key: str | None,
        module: str,
    ) -> T:
        """回退通道:纯 JSON 输出 + pydantic 校验,校验错误回喂重试."""
        msgs = self._messages(prompt, system)
        last_err: Exception | None = None
        for _ in range(max(1, self.cfg.max_retries)):
            completion = self._client.chat.completions.create(
                model=self.cfg.model,
                messages=msgs,
                temperature=self.cfg.temperature,
                top_p=self.cfg.top_p,
            )
            self._meter(module, completion)
            content = completion.choices[0].message.content or ""
            try:
                obj = schema.model_validate_json(extract_json(content))
                self._store_cache(cache_key, obj)
                return obj
            except ValidationError as e:
                last_err = e
                msgs.append({"role": "assistant", "content": content})
                msgs.append(
                    {
                        "role": "user",
                        "content": (
                            f"上述输出不符合 schema,错误:{e}\n"
                            "请严格输出符合 schema 的纯 JSON,不要任何其他文字。"
                        ),
                    }
                )
        raise GatewaySchemaError(
            f"{self.cfg.max_retries} 次重试后仍无法产出合法 {schema.__name__}", last_err
        )

    def text(self, prompt: str, *, system: str = "", module: str = "") -> str:
        self._budget_check()
        completion = self._client.chat.completions.create(
            model=self.cfg.model,
            messages=self._messages(prompt, system),
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
        )
        self._meter(module, completion)
        return sanitize_content(completion.choices[0].message.content or "")


def make_cache_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
