import json

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.cli.vacancy_profile import cmd_create, cmd_list, cmd_show_current
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version


def test_cmd_show_current_returns_latest(tmp_engine, capsys):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        create_vacancy_profile_version(session, course_id=5, requirements={"a": 1}, notes="", created_by_id=None)

    cmd_show_current(tmp_engine, course_id=5)
    out = capsys.readouterr().out
    assert json.loads(out)["version"] == 1
