import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.platform_db import IDENTITY_RESOLVER_TABLES, reflect_platform_tables
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile


def main() -> None:
    settings = Settings()
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=IDENTITY_RESOLVER_TABLES)
    Application = platform_base.classes.courses_application
    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord

    write_engine = make_write_engine(settings)

    created = 0
    with Session(platform_engine) as platform_session, Session(write_engine) as write_session:
        for record in platform_session.scalars(select(HHNegotiationRecord)):
            resolve_or_create_candidate_profile(
                write_session, platform_base=platform_base,
                hh_negotiation_id=record.id, application_id=record.application_id,
            )
            created += 1

        hh_linked_application_ids = {
            r.application_id for r in platform_session.scalars(select(HHNegotiationRecord))
            if r.application_id is not None
        }
        for application in platform_session.scalars(select(Application)):
            if application.id in hh_linked_application_ids:
                continue  # уже обработан через HHNegotiationRecord выше
            resolve_or_create_candidate_profile(
                write_session, platform_base=platform_base, application_id=application.id,
            )
            created += 1

    print(f"OK: processed {created} platform records, 0 platform writes", file=sys.stderr)


if __name__ == "__main__":
    main()
