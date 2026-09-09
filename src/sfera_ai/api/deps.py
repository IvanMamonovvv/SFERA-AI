from collections.abc import Iterator, Sequence

from fastapi import HTTPException, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sfera_ai.platform_db import API_READ_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.api_read import resolve_course_id


def get_session(request: Request) -> Iterator[Session]:
    factory = sessionmaker(bind=request.app.state.engine)
    with factory() as session:
        yield session


def get_platform_engine(request: Request) -> Engine:
    return request.app.state.platform_engine


def get_llm_client(request: Request) -> OpenRouterClient:
    return request.app.state.llm_client


def get_hh_client(request: Request):
    return request.app.state.hh_client


def get_s3_client(request: Request):
    return request.app.state.s3_client


def get_s3_bucket(request: Request) -> str:
    return request.app.state.s3_bucket


def resolve_course_or_404(
    platform_engine: Engine, course_uuid: str, *, tables: Sequence[str] = API_READ_TABLES
) -> tuple[int, object]:
    platform_base = reflect_platform_tables(platform_engine, tables=tables)
    course_id = resolve_course_id(platform_base, course_uuid)
    if course_id is None:
        raise HTTPException(status_code=404, detail="course not found")
    return course_id, platform_base
