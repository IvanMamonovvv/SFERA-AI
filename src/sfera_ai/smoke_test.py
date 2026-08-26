import sys

from sqlalchemy import create_engine

from sfera_ai.config import Settings
from sfera_ai.platform_db import reflect_platform_tables

PLATFORM_TABLES = ("courses_application", "testchecks_answer")


def main(application_id: int) -> None:
    settings = Settings()
    engine = create_engine(settings.platform_database_url)
    base = reflect_platform_tables(engine, tables=PLATFORM_TABLES)
    Application = base.classes.courses_application

    from sqlalchemy.orm import Session
    from sqlalchemy.exc import DBAPIError

    with Session(engine) as session:
        app = session.get(Application, application_id)
        if app is None:
            print(f"Application {application_id} not found", file=sys.stderr)
            raise SystemExit(1)
        print(f"OK: read Application id={app.id}")

        # Подтверждаем, что роль ai_readonly реально read-only — не только по DDL,
        # но и на практике: попытка записи должна упасть InsufficientPrivilege.
        try:
            session.execute(
                Application.__table__.update()
                .where(Application.id == application_id)
                .values(comment=app.comment)
            )
            session.rollback()
            print(
                "FAIL: write succeeded through ai_readonly — role is not actually read-only",
                file=sys.stderr,
            )
            raise SystemExit(1)
        except DBAPIError:
            session.rollback()
            print("OK: write correctly rejected (read-only role confirmed)")


if __name__ == "__main__":
    main(int(sys.argv[1]))
