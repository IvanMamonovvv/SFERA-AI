from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_service_state import AiServiceState


def test_ai_service_state_has_expected_columns():
    columns = {c.name for c in AiServiceState.__table__.columns}
    assert columns == {"key", "value", "created_at", "updated_at"}


def test_ai_service_state_roundtrip(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.add(AiServiceState(key="last_seen_merge_log_id", value="42"))
        session.commit()

    with Session(tmp_engine) as session:
        state = session.get(AiServiceState, "last_seen_merge_log_id")
        assert state.value == "42"
