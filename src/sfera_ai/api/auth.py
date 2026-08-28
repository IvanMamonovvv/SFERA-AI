from collections.abc import Callable

from fastapi import Header, HTTPException, status


def make_bff_secret_dependency(secret: str) -> Callable[[str | None], None]:
    """Проверка shared-secret заголовка между BFF-прокси и AI-сервисом.

    03_TDD.md, «3. API / контракты» — фронтенд ходит к AI-сервису только через
    BFF-прокси SPHERA, сервис не должен быть открыт в интернет без проверки.
    """

    def require_bff_secret(x_bff_shared_secret: str | None = Header(default=None)) -> None:
        if x_bff_shared_secret != secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid shared secret")

    return require_bff_secret
