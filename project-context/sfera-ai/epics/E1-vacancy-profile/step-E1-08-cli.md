# Шаг E1-08 — CRUD-консоль для ручного заполнения

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1-07
**Перед началом:** прочитай `05_EPICS.md` эпик E1: «простой CRUD-скрипт/консоль для
ручного заполнения (без публичного API)». Три команды: `create` (новая версия),
`show-current` (текущая версия по `course_id`), `list` (все версии по `course_id`).

## Цель

CLI `vacancy-profile create/show-current/list` работает поверх versioning-сервиса
(E1-07).

## Что сделать

**Step 1: Написать падающий тест на `show-current`/`list` (через прямой вызов функций,
не subprocess — быстрее и детерминированнее)**

```python
# tests/cli/test_vacancy_profile_cli.py
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
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/cli/test_vacancy_profile_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать**

```python
# src/sfera_ai/cli/vacancy_profile.py
import argparse
import json
import sys

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sfera_ai.db.session import make_write_engine
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version


def _serialize(profile: VacancyProfile) -> dict:
    return {
        "id": profile.id, "course_id": profile.course_id, "version": profile.version,
        "is_current": profile.is_current, "requirements": profile.requirements, "notes": profile.notes,
    }


def cmd_create(engine: Engine, *, course_id: int, requirements: dict, notes: str) -> None:
    with Session(engine) as session:
        profile = create_vacancy_profile_version(
            session, course_id=course_id, requirements=requirements, notes=notes, created_by_id=None,
        )
        print(json.dumps(_serialize(profile), ensure_ascii=False))


def cmd_show_current(engine: Engine, *, course_id: int) -> None:
    with Session(engine) as session:
        profile = session.scalar(
            select(VacancyProfile).where(VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True))
        )
        if profile is None:
            print(f"No current VacancyProfile for course_id={course_id}", file=sys.stderr)
            raise SystemExit(1)
        print(json.dumps(_serialize(profile), ensure_ascii=False))


def cmd_list(engine: Engine, *, course_id: int) -> None:
    with Session(engine) as session:
        rows = session.scalars(
            select(VacancyProfile).where(VacancyProfile.course_id == course_id).order_by(VacancyProfile.version)
        )
        for row in rows:
            print(json.dumps(_serialize(row), ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="vacancy-profile")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--course-id", type=int, required=True)
    p_create.add_argument("--requirements-json", type=str, required=True, help="JSON string or @file.json")
    p_create.add_argument("--notes", type=str, default="")

    p_show = sub.add_parser("show-current")
    p_show.add_argument("--course-id", type=int, required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--course-id", type=int, required=True)

    args = parser.parse_args()
    engine = make_write_engine()

    if args.command == "create":
        raw = args.requirements_json
        if raw.startswith("@"):
            raw = open(raw[1:], encoding="utf-8").read()
        cmd_create(engine, course_id=args.course_id, requirements=json.loads(raw), notes=args.notes)
    elif args.command == "show-current":
        cmd_show_current(engine, course_id=args.course_id)
    elif args.command == "list":
        cmd_list(engine, course_id=args.course_id)


if __name__ == "__main__":
    main()
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/cli/test_vacancy_profile_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/cli tests/cli/test_vacancy_profile_cli.py
git commit -m "feat: add vacancy-profile CLI for manual data entry"
```

## Файлы

- `src/sfera_ai/cli/__init__.py` — создать
- `src/sfera_ai/cli/vacancy_profile.py` — создать
- `tests/cli/test_vacancy_profile_cli.py` — тест

## Критерии готовности (DoD)

- [x] `uv run pytest tests/cli/test_vacancy_profile_cli.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/cli/test_vacancy_profile_cli.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — CLI `vacancy-profile create/show-current/list` реализован поверх versioning-сервиса (E1-07). Тест `tests/cli/test_vacancy_profile_cli.py` зелёный, коммит `7da8fb1`.
