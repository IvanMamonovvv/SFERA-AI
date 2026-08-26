from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class Dummy(TimestampMixin, Base):
    __tablename__ = "dummy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


def test_timestamp_mixin_has_created_and_updated(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    from sqlalchemy.orm import Session

    with Session(tmp_engine) as session:
        row = Dummy()
        session.add(row)
        session.commit()
        session.refresh(row)
        assert isinstance(row.created_at, datetime)
        assert isinstance(row.updated_at, datetime)
