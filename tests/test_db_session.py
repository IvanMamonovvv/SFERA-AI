from sqlalchemy.orm import Session

from sfera_ai.db.session import make_session_factory


def test_make_session_factory_returns_working_session(tmp_engine):
    factory = make_session_factory(tmp_engine)
    with factory() as session:
        assert isinstance(session, Session)
