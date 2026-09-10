import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.cli.vacancy_profile import cmd_create, cmd_create_from_portrait, cmd_list, cmd_show_current
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version


def test_cmd_show_current_returns_latest(tmp_engine, capsys):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        create_vacancy_profile_version(session, course_id=5, requirements={"a": 1}, notes="", created_by_id=None)

    cmd_show_current(tmp_engine, course_id=5)
    out = capsys.readouterr().out
    assert json.loads(out)["version"] == 1


def test_cmd_create_from_portrait_saves_portrait_text_and_source_url(tmp_engine, monkeypatch, capsys):
    Base.metadata.create_all(tmp_engine)
    fake_settings = type("FakeSettings", (), {"openrouter_api_key": "x", "openrouter_base_url": "https://x"})()
    monkeypatch.setattr("sfera_ai.cli.vacancy_profile.Settings", lambda: fake_settings)
    monkeypatch.setattr("sfera_ai.cli.vacancy_profile.OpenRouterClient", lambda **kwargs: object())
    monkeypatch.setattr(
        "sfera_ai.cli.vacancy_profile.build_vacancy_requirements",
        lambda portrait_text, source_url, *, llm_client: {"skills": ["Python"]},
    )

    cmd_create_from_portrait(
        tmp_engine, course_id=7, portrait_text="Ищем Python-разработчика",
        source_url="https://example.com/vacancy", notes="",
    )

    with Session(tmp_engine) as session:
        profile = session.scalar(select(VacancyProfile).where(VacancyProfile.course_id == 7))
        assert profile.portrait_text == "Ищем Python-разработчика"
        assert profile.source_url == "https://example.com/vacancy"
