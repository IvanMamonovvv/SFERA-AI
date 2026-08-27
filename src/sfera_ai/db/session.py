from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from sfera_ai.config import Settings


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_write_engine(settings: Settings | None = None) -> Engine:
    settings = settings or Settings()
    return create_engine(settings.write_database_url)
