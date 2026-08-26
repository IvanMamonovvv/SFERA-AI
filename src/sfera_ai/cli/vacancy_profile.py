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
