from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import Engine, create_engine, text

from sfera_ai.api.auth import make_bff_secret_dependency
from sfera_ai.api.routes import router as api_v1_router
from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.providers import OpenRouterClient


def _make_platform_engine() -> Engine:
    return create_engine(Settings().platform_database_url)


def _make_llm_client() -> OpenRouterClient:
    settings = Settings()
    return OpenRouterClient(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)


def create_app(
    *,
    engine_factory: Callable[[], Engine] = make_write_engine,
    platform_engine_factory: Callable[[], Engine] = _make_platform_engine,
    llm_client_factory: Callable[[], OpenRouterClient] = _make_llm_client,
    bff_shared_secret: str | None = None,
) -> FastAPI:
    secret = bff_shared_secret if bff_shared_secret is not None else Settings().bff_shared_secret

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine_factory()
        app.state.platform_engine = platform_engine_factory()
        app.state.llm_client = llm_client_factory()
        yield
        app.state.engine.dispose()
        app.state.platform_engine.dispose()

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        with app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(api_v1_router, dependencies=[Depends(make_bff_secret_dependency(secret))])

    return app
