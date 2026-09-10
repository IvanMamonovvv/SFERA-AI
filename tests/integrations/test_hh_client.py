import httpx
import pytest

from sfera_ai.integrations.hh_client import HHClient, HHClientError


def _client(handler) -> HHClient:
    transport = httpx.MockTransport(handler)
    return HHClient(
        base_url="http://backend:8000",
        login="admin@example.com",
        password="secret",
        http_client=httpx.Client(transport=transport),
    )


def test_get_resume_pdf_authenticates_then_fetches():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/auth/token/":
            return httpx.Response(200, json={"access": "tok-1", "refresh": "r-1"})
        assert request.headers["Authorization"] == "Bearer tok-1"
        assert request.url.path == "/api/v1/companies/acme/integrations/hh/negotiations/42/resume.pdf/"
        return httpx.Response(200, content=b"%PDF-1")

    client = _client(handler)
    result = client.get_resume_pdf(42, "acme")

    assert result == b"%PDF-1"
    assert calls == ["/api/v1/auth/token/", "/api/v1/companies/acme/integrations/hh/negotiations/42/resume.pdf/"]


def test_get_resume_pdf_reauthenticates_on_401():
    call_count = {"auth": 0, "pdf": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            call_count["auth"] += 1
            return httpx.Response(200, json={"access": f"tok-{call_count['auth']}", "refresh": "r"})
        call_count["pdf"] += 1
        if request.headers["Authorization"] == "Bearer tok-1":
            return httpx.Response(401, json={"detail": "expired"})
        return httpx.Response(200, content=b"%PDF-2")

    client = _client(handler)
    result = client.get_resume_pdf(42, "acme")

    assert result == b"%PDF-2"
    assert call_count == {"auth": 2, "pdf": 2}


def test_get_resume_pdf_404_raises_hh_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            return httpx.Response(200, json={"access": "tok-1"})
        return httpx.Response(404, json={"detail": "not found"})

    client = _client(handler)
    with pytest.raises(HHClientError, match="404"):
        client.get_resume_pdf(42, "acme")


def test_authentication_failure_raises_hh_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid credentials"})

    client = _client(handler)
    with pytest.raises(HHClientError, match="auth failed"):
        client.get_resume_pdf(42, "acme")


def test_network_error_raises_hh_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            return httpx.Response(200, json={"access": "tok-1"})
        raise httpx.ConnectError("connection refused")

    client = _client(handler)
    with pytest.raises(HHClientError, match="backend request failed"):
        client.get_resume_pdf(42, "acme")


def test_remote_protocol_error_retries_once_then_succeeds():
    """Сервер молча закрывает keep-alive соединение — httpx кидает RemoteProtocolError
    на первой попытке; повторный запрос идёт по новому соединению и проходит."""
    call_count = {"auth": 0, "pdf": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            call_count["auth"] += 1
            return httpx.Response(200, json={"access": "tok-1"})
        call_count["pdf"] += 1
        if call_count["pdf"] == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)
        return httpx.Response(200, content=b"%PDF-1")

    client = _client(handler)
    result = client.get_resume_pdf(42, "acme")

    assert result == b"%PDF-1"
    assert call_count["pdf"] == 2


def test_remote_protocol_error_on_both_attempts_raises_hh_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            return httpx.Response(200, json={"access": "tok-1"})
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)

    client = _client(handler)
    with pytest.raises(HHClientError, match="backend request failed"):
        client.get_resume_pdf(42, "acme")


def test_non_transport_error_is_not_retried():
    call_count = {"pdf": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/token/":
            return httpx.Response(200, json={"access": "tok-1"})
        call_count["pdf"] += 1
        raise httpx.ConnectTimeout("timed out", request=request)

    client = _client(handler)
    with pytest.raises(HHClientError, match="backend request failed"):
        client.get_resume_pdf(42, "acme")

    assert call_count["pdf"] == 1
