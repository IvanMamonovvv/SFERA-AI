from sfera_ai.models.vacancy_profile import VacancyProfile


def test_vacancy_profile_has_expected_columns():
    columns = {c.name for c in VacancyProfile.__table__.columns}
    assert columns == {
        "id", "course_id", "version", "is_current", "requirements",
        "notes", "created_by_id", "created_at", "updated_at",
    }


def test_vacancy_profile_unique_constraint_on_course_and_version():
    constraint_columns = {
        tuple(c.name for c in uc.columns)
        for uc in VacancyProfile.__table__.constraints
        if uc.__class__.__name__ == "UniqueConstraint"
    }
    assert ("course_id", "version") in constraint_columns
