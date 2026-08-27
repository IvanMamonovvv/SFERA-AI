from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version


def test_first_version_is_current(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = create_vacancy_profile_version(
            session, course_id=1, requirements={"must_have": ["B2B sales"]}, notes="", created_by_id=None,
        )
        assert profile.version == 1
        assert profile.is_current is True


def test_second_version_unsets_previous_current(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        create_vacancy_profile_version(session, course_id=1, requirements={"a": 1}, notes="", created_by_id=None)
        second = create_vacancy_profile_version(session, course_id=1, requirements={"a": 2}, notes="", created_by_id=None)

        rows = session.query(VacancyProfile).filter_by(course_id=1).order_by(VacancyProfile.version).all()
        assert [r.is_current for r in rows] == [False, True]
        assert second.version == 2
