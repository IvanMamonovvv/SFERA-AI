import argparse
import sys

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.integrations.hh_client import HHClient
from sfera_ai.platform_db import RESUME_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.resume_pipeline import requeue_failed_resumes


def main() -> None:
    """Ручной прогон requeue_failed_resumes (step-E18-03) — не ждать до 2 часов
    следующего cron-тика, сразу проверить результат на реальных FAILED-резюме."""
    parser = argparse.ArgumentParser(description="Ручной ретрай ResumeExtract.status=FAILED")
    args = parser.parse_args()

    settings = Settings()
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=RESUME_DETECTION_TABLES)

    hh_client = HHClient(
        base_url=settings.hh_backend_base_url,
        login=settings.hh_backend_admin_login,
        password=settings.hh_backend_admin_password,
        host_header=settings.hh_backend_host_header,
    )
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    llm_client = OpenRouterClient(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)

    with Session(write_engine) as session:
        retried = requeue_failed_resumes(
            session,
            platform_base,
            hh_client=hh_client,
            s3_client=s3_client,
            s3_bucket=settings.s3_bucket,
            llm_client=llm_client,
            max_attempts=settings.resume_extract_max_attempts,
        )

        done = 0
        still_failed = 0
        for extract in retried:
            status = "OK" if extract.status == "DONE" else extract.status
            print(
                f"{status} extract_id={extract.id} candidate_profile_id={extract.candidate_profile_id} "
                f"attempts={extract.attempts} retry_after={extract.retry_after}",
                file=sys.stderr,
            )
            if extract.status == "DONE":
                done += 1
            else:
                still_failed += 1
                print(f"  error: {extract.error}", file=sys.stderr)

    print(f"OK: retried {len(retried)}, done {done}, still_failed {still_failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
