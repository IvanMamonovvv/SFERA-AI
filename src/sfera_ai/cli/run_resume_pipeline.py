import argparse
import sys

import boto3
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.integrations.hh_client import HHClient
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.resume_pipeline import process_resume


def main() -> None:
    """Ручной драй-ран на реальных HH-резюме (E3-05, DoD): берёт N уже
    зарезолвленных `CandidateProfile.hh_negotiation_id` (E2), прогоняет через
    `process_resume`, печатает статус каждого. ANKETA_FILE-источник — вне
    scope: детекция «какой Answer — резюме» относится к Answers Pipeline/E5,
    не к этому шагу (03_TDD.md, «Resume Pipeline» vs «Answers Pipeline»)."""
    parser = argparse.ArgumentParser(description="Ручной прогон resume-пайплайна на реальных HH-резюме")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    settings = Settings()
    write_engine = make_write_engine(settings)

    hh_client = HHClient(
        base_url=settings.hh_backend_base_url,
        login=settings.hh_backend_admin_login,
        password=settings.hh_backend_admin_password,
        company_slug=settings.hh_backend_company_slug,
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

    processed = 0
    failed = 0
    with Session(write_engine) as session:
        profiles = session.scalars(
            select(CandidateProfile)
            .where(CandidateProfile.hh_negotiation_id.is_not(None))
            .order_by(CandidateProfile.hh_negotiation_id.desc())
            .limit(args.limit)
        ).all()

        for profile in profiles:
            extract = process_resume(
                session=session,
                platform_base=None,  # HH_RESUME источник не читает testchecks_answer
                hh_client=hh_client,
                s3_client=s3_client,
                s3_bucket=settings.s3_bucket,
                llm_client=llm_client,
                candidate_profile_id=profile.id,
                hh_resume_id=str(profile.hh_negotiation_id),
            )
            processed += 1
            status = "OK" if extract.status == "DONE" else extract.status
            print(f"{status} candidate_profile_id={profile.id} extract_id={extract.id}", file=sys.stderr)
            if extract.status == "FAILED":
                failed += 1
                print(f"  error: {extract.error}", file=sys.stderr)

    print(f"OK: processed {processed}, failed {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
