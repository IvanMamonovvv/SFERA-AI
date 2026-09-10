import httpx
import pytest

from sfera_ai.providers import LLMProviderError, OpenRouterClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    return OpenRouterClient(api_key="test-key", http_client=httpx.Client(transport=transport))


def test_complete_returns_parsed_result():
    def handler(request):
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    client = _client(handler)
    result = client.complete(model="test-model", prompt_version="v1", messages=[{"role": "user", "content": "hi"}])

    assert result.content == '{"ok": true}'
    assert result.provider == "openrouter"
    assert result.model == "test-model"
    assert result.tokens_input == 10
    assert result.tokens_output == 5
    assert result.latency_ms >= 0


def test_complete_non_200_raises_provider_error():
    def handler(request):
        return httpx.Response(500, text="internal error")

    client = _client(handler)
    with pytest.raises(LLMProviderError):
        client.complete(model="test-model", prompt_version="v1", messages=[])


def test_complete_network_error_raises_provider_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    client = _client(handler)
    with pytest.raises(LLMProviderError):
        client.complete(model="test-model", prompt_version="v1", messages=[])


def test_complete_retries_once_after_stale_connection_drop():
    """Наблюдалось в проде (04_STATE.md) — простаивающее keep-alive соединение
    сервер закрывает молча, httpx кидает RemoteProtocolError на первой попытке
    переиспользовать его; повторный запрос идёт по новому соединению и проходит."""
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}},
        )

    client = _client(handler)
    result = client.complete(model="test-model", prompt_version="v1", messages=[])

    assert result.content == '{"ok": true}'
    assert calls["count"] == 2


def test_complete_gives_up_after_retry_exhausted():
    def handler(request):
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)

    client = _client(handler)
    with pytest.raises(LLMProviderError):
        client.complete(model="test-model", prompt_version="v1", messages=[])
