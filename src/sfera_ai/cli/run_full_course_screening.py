import argparse
import csv
import sys

import boto3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.integrations.hh_client import HHClient
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import RESUME_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.candidate_facts import build_or_update_candidate_facts, resume_status
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile
from sfera_ai.services.export.archive import build_candidates_export_archive
from sfera_ai.services.fit_scoring import run_fit_scoring
from sfera_ai.services.resume_pipeline import ensure_resume_processed

_FIELDNAMES = (
    "candidate_profile_id", "application_id", "data_completeness", "fit_score",
    "confidence", "recommendation", "summary", "resume_status",
)


def _application_ids_for_course(platform_base, course_id: int) -> list[int]:
    Application = platform_base.classes.courses_application
    with Session(platform_base.engine) as platform_session:
        rows = platform_session.execute(select(Application.id).where(Application.course_id == course_id)).all()
    return [row[0] for row in rows]


def _screen_profile(
    session, profile: CandidateProfile, application_id: int | None, *, platform_base,
    vacancy_profile: VacancyProfile, hh_client, s3_client, s3_bucket: str, llm_client,
) -> dict:
    try:
        ensure_resume_processed(
            profile, platform_base=platform_base, hh_client=hh_client,
            s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client, session=session,
        )
        profile = build_or_update_candidate_facts(session, platform_base, llm_client, profile)
        analysis = run_fit_scoring(session, candidate_profile=profile, vacancy_profile=vacancy_profile, llm_client=llm_client)
        resume_extracts = session.scalars(
            select(ResumeExtract).where(ResumeExtract.candidate_profile_id == profile.id)
        ).all()
        return {
            "candidate_profile_id": profile.id,
            "application_id": application_id,
            "data_completeness": profile.data_completeness,
            "fit_score": analysis.fit_score,
            "confidence": analysis.confidence,
            "recommendation": analysis.recommendation,
            "summary": analysis.summary,
            "resume_status": resume_status(resume_extracts),
        }
    except Exception as exc:
        return {
            "candidate_profile_id": profile.id,
            "application_id": application_id,
            "data_completeness": None,
            "fit_score": None,
            "confidence": "ERROR",
            "recommendation": "",
            "summary": str(exc)[:500],
            "resume_status": "UNKNOWN",
        }


def _screen_application(
    session, application_id: int, *, platform_base, vacancy_profile: VacancyProfile,
    hh_client, s3_client, s3_bucket: str, llm_client,
) -> dict:
    try:
        profile = resolve_or_create_candidate_profile(session, platform_base=platform_base, application_id=application_id)
    except Exception as exc:
        return {
            "candidate_profile_id": None,
            "application_id": application_id,
            "data_completeness": None,
            "fit_score": None,
            "confidence": "ERROR",
            "recommendation": "",
            "summary": str(exc)[:500],
            "resume_status": "UNKNOWN",
        }
    return _screen_profile(
        session, profile, application_id, platform_base=platform_base, vacancy_profile=vacancy_profile,
        hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client,
    )


def _screen_candidate_profile_id(
    session, candidate_profile_id: int, *, platform_base, vacancy_profile: VacancyProfile,
    hh_client, s3_client, s3_bucket: str, llm_client,
) -> dict:
    profile = session.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        return {
            "candidate_profile_id": candidate_profile_id,
            "application_id": None,
            "data_completeness": None,
            "fit_score": None,
            "confidence": "ERROR",
            "recommendation": "",
            "summary": f"CandidateProfile id={candidate_profile_id} не найден",
            "resume_status": "UNKNOWN",
        }
    return _screen_profile(
        session, profile, profile.application_id, platform_base=platform_base, vacancy_profile=vacancy_profile,
        hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Полный прогон вакансии по всем кандидатам курса (E10-01)")
    parser.add_argument("--course-id", type=int, required=True, help="используется и как источник вакансии при --candidate-ids")
    parser.add_argument(
        "--candidate-ids", type=str, default=None,
        help="через запятую id CandidateProfile — точечный пересчёт вместо всех заявок курса (E11-02)",
    )
    parser.add_argument("--fit-threshold", type=int, default=75)
    parser.add_argument("--zip-path", type=str, required=True, help="куда сохранить zip с карточками прошедших порог")
    parser.add_argument("--csv", type=str, default=None, help="путь для CSV-сводки вместо stdout")
    args = parser.parse_args()
    candidate_profile_ids = (
        [int(v) for v in args.candidate_ids.split(",") if v.strip()] if args.candidate_ids else None
    )

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

    application_ids = None if candidate_profile_ids else _application_ids_for_course(platform_base, args.course_id)

    with Session(write_engine) as session:
        vacancy_profile = session.scalar(
            select(VacancyProfile).where(
                VacancyProfile.course_id == args.course_id, VacancyProfile.is_current.is_(True)
            )
        )
        if vacancy_profile is None:
            print(f"No current VacancyProfile for course_id={args.course_id}", file=sys.stderr)
            raise SystemExit(1)

        rows = []
        passed_ids: list[int] = []
        if candidate_profile_ids:
            for candidate_profile_id in candidate_profile_ids:
                row = _screen_candidate_profile_id(
                    session, candidate_profile_id, platform_base=platform_base, vacancy_profile=vacancy_profile,
                    hh_client=hh_client, s3_client=s3_client, s3_bucket=settings.s3_bucket, llm_client=llm_client,
                )
                rows.append(row)
                if row["fit_score"] is not None and row["fit_score"] >= args.fit_threshold:
                    passed_ids.append(row["candidate_profile_id"])
        else:
            for application_id in application_ids:
                row = _screen_application(
                    session, application_id, platform_base=platform_base, vacancy_profile=vacancy_profile,
                    hh_client=hh_client, s3_client=s3_client, s3_bucket=settings.s3_bucket, llm_client=llm_client,
                )
                rows.append(row)
                if row["fit_score"] is not None and row["fit_score"] >= args.fit_threshold:
                    passed_ids.append(row["candidate_profile_id"])

        if passed_ids:
            archive_bytes = build_candidates_export_archive(
                session, platform_base, passed_ids, args.course_id,
                hh_client=hh_client, s3_client=s3_client, s3_bucket=settings.s3_bucket,
            )
            with open(args.zip_path, "wb") as fh:
                fh.write(archive_bytes)
            print(f"OK: zip with {len(passed_ids)} candidates written to {args.zip_path}", file=sys.stderr)
        else:
            print("No candidates passed the fit-score threshold, zip not written", file=sys.stderr)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"OK: {len(rows)} candidates written to {args.csv}", file=sys.stderr)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
