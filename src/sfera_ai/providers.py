import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """LLM-провайдер недоступен или вернул ошибку (сеть, non-200, таймаут)."""


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    tokens_input: int
    tokens_output: int
    latency_ms: int


class OpenRouterClient:
    """Тонкий клиент OpenRouter — единая точка входа для всех LLM-вызовов пайплайна
    (03_TDD.md, «AI Pipeline — какие вызовы и когда»). Логирует provider/model/
    prompt_version/токены/latency на каждый вызов — не универсальная AI-платформа,
    просто обёртка с наблюдаемостью затрат (03_TDD.md, «Cost Protection», п.6)."""

    def __init__(
        self, *, api_key: str, base_url: str = "https://openrouter.ai/api/v1",
        http_client: httpx.Client | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client(timeout=60.0)

    def _request_with_retry(self, payload: dict) -> httpx.Response:
        """Один повтор при RemoteProtocolError — httpx кидает его, когда пытается
        переиспользовать keep-alive соединение, которое сервер уже закрыл молча
        (наблюдалось в проде: 34/35 FAILED резюме — этот же обрыв, см. 04_STATE.md).
        Retry идёт по новому соединению из пула, не по тому же самому."""
        try:
            return self._http.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
        except httpx.RemoteProtocolError:
            return self._http.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )

    def complete(
        self, *, model: str, prompt_version: str, messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResult:
        payload: dict = {"model": model, "messages": messages}
        if response_format is not None:
            payload["response_format"] = response_format

        started = time.monotonic()
        try:
            response = self._request_with_retry(payload)
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenRouter request failed: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code != 200:
            raise LLMProviderError(f"OpenRouter {response.status_code}: {response.text[:200]}")

        data = response.json()
        usage = data.get("usage", {})
        result = LLMResult(
            content=data["choices"][0]["message"]["content"],
            provider="openrouter",
            model=model,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )
        logger.info(
            "llm_call provider=%s model=%s prompt_version=%s tokens_input=%d tokens_output=%d latency_ms=%d",
            result.provider, result.model, prompt_version, result.tokens_input,
            result.tokens_output, result.latency_ms,
        )
        return result
