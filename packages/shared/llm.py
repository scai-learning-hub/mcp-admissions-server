"""LLM adapter — configurable model provider (Ollama by default, OpenAI-compatible optional).

Per the plan §6: "Do not hard-code an LLM provider. The application should run
with MODEL_PROVIDER=ollama and permit an OpenAI-compatible endpoint through
configuration."

Ollama exposes an OpenAI-compatible API at /v1, so we use the openai SDK for
both providers — just different base_url and api_key.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from packages.observability.logging import get_logger
from packages.shared.config import settings

log = get_logger("scai.llm")


class LLMAdapter:
    """Thin wrapper over the OpenAI-compatible API (works with Ollama + cloud)."""

    def __init__(self) -> None:
        self.provider = settings.model_provider
        self.model = settings.model_name
        self.client = AsyncOpenAI(
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
        )
        log.info("llm_adapter_init", provider=self.provider, model=self.model,
                 base_url=settings.model_base_url)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a chat completion. Returns {content, tool_calls}."""
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            resp = await self.client.chat.completions.create(**kwargs)
            choice = resp.choices[0]
            msg = choice.message

            result: dict[str, Any] = {
                "content": msg.content or "",
                "tool_calls": [],
            }
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn = tc.function
                    try:
                        args = json.loads(fn.arguments) if fn.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": fn.name,
                        "arguments": args,
                    })
            return result

        except Exception as e:
            log.error("llm_error", error=str(e), model=self.model)
            return {"content": f"(LLM error: {e})", "tool_calls": []}

    async def chat_simple(self, system: str, user: str) -> str:
        """Simple one-shot chat without tool calling. Returns text only."""
        result = await self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
        return result["content"]


# Singleton
_adapter: LLMAdapter | None = None


def get_llm() -> LLMAdapter:
    global _adapter
    if _adapter is None:
        _adapter = LLMAdapter()
    return _adapter


__all__ = ["LLMAdapter", "get_llm"]