from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.vacancy_profile import VacancyProfile


def create_vacancy_profile_version(
    session: Session,
    *,
    course_id: int,
    requirements: dict[str, Any],
    notes: str,
    created_by_id: int | None,
) -> VacancyProfile:
    previous_current = session.scalar(
        select(VacancyProfile).where(VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True))
    )
    next_version = (previous_current.version + 1) if previous_current else 1

    if previous_current is not None:
        previous_current.is_current = False
        session.flush()  # UPDATE до INSERT — иначе partial unique index (uq_vacancy_profile_course_current)
        # может увидеть на миг две строки is_current=True на одном course_id (порядок flush не гарантирован)

    new_profile = VacancyProfile(
        course_id=course_id,
        version=next_version,
        is_current=True,
        requirements=requirements,
        notes=notes,
        created_by_id=created_by_id,
    )
    session.add(new_profile)
    session.commit()
    session.refresh(new_profile)
    return new_profile
