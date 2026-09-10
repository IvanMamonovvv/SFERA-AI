import httpx


class HHClientError(Exception):
    """PDF резюме недоступен (сеть, HH API, 404, не подключено)."""


class HHClient:
    """Собственный клиент для контракта `get_resume_pdf` (03_TDD.md, «Что НЕ ломаем») —
    ходит не в HH API напрямую, а в свой уже существующий backend-эндпоинт
    `HHResumePdfView`, от имени сервисного admin-аккаунта (JWT), через внутреннюю
    docker-сеть `ai_shared`."""

    def __init__(
        self, *, base_url: str, login: str, password: str,
        host_header: str | None = None, http_client: httpx.Client | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._login = login
        self._password = password
        self._host_header = host_header
        self._http = http_client or httpx.Client(timeout=30.0)
        self._access_token: str | None = None

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Host": self._host_header} if self._host_header else {}
        if extra:
            headers.update(extra)
        return headers

    def _authenticate(self) -> None:
        response = self._http.post(
            f"{self._base_url}/api/v1/auth/token/",
            json={"email": self._login, "password": self._password},
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise HHClientError(f"backend auth failed: {response.status_code} {response.text[:200]}")
        self._access_token = response.json()["access"]

    def _get_with_retry(self, url: str, headers: dict[str, str]) -> httpx.Response:
        """Один повтор при RemoteProtocolError — зеркало
        `OpenRouterClient._request_with_retry` (providers.py). Retry идёт по новому
        соединению из пула, не по тому же самому."""
        try:
            return self._http.get(url, headers=headers)
        except httpx.RemoteProtocolError:
            return self._http.get(url, headers=headers)

    def _get(self, url: str) -> httpx.Response:
        if self._access_token is None:
            self._authenticate()
        response = self._get_with_retry(url, self._headers({"Authorization": f"Bearer {self._access_token}"}))
        if response.status_code == 401:
            self._authenticate()
            response = self._get_with_retry(url, self._headers({"Authorization": f"Bearer {self._access_token}"}))
        return response

    def get_resume_pdf(self, hh_negotiation_id: int, company_slug: str) -> bytes:
        url = (
            f"{self._base_url}/api/v1/companies/{company_slug}"
            f"/integrations/hh/negotiations/{hh_negotiation_id}/resume.pdf/"
        )
        try:
            response = self._get(url)
        except httpx.HTTPError as exc:
            raise HHClientError(f"backend request failed: {exc}") from exc
        if response.status_code != 200:
            raise HHClientError(f"resume.pdf failed: {response.status_code} {response.text[:200]}")
        return response.content
