import argparse
import csv
import sys
from collections import defaultdict

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import IDENTITY_RESOLVER_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.fit_scoring import run_fit_scoring

_FIELDNAMES = ("candidate_profile_id", "data_completeness", "fit_score", "confidence", "recommendation", "summary")


def _application_ids_for_course(platform_base, course_id: int) -> set[int]:
    Application = platform_base.classes.courses_application
    with Session(platform_base.engine) as platform_session:
        rows = platform_session.execute(select(Application.id).where(Application.course_id == course_id)).all()
    return {row[0] for row in rows}


def _sample_diverse(profiles: list[CandidateProfile], limit: int) -> list[CandidateProfile]:
    """Round-robin по `data_completeness` — в выборку попадают кандидаты разной полноты
    данных (step-E6-05, п.1), а не первые N подряд одного уровня."""
    buckets: dict[str, list[CandidateProfile]] = defaultdict(list)
    for profile in profiles:
        buckets[profile.data_completeness].append(profile)
    order = sorted(buckets)
    sample: list[CandidateProfile] = []
    while len(sample) < limit and any(buckets[key] for key in order):
        for key in order:
            if buckets[key] and len(sample) < limit:
                sample.append(buckets[key].pop(0))
    return sample


def _run_sample(
    session: Session, *, sample: list[CandidateProfile], vacancy_profile: VacancyProfile, llm_client: OpenRouterClient
) -> list[dict]:
    rows = []
    for profile in sample:
        try:
            analysis = run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy_profile, llm_client=llm_client,
            )
            rows.append({
                "candidate_profile_id": profile.id,
                "data_completeness": profile.data_completeness,
                "fit_score": analysis.fit_score,
                "confidence": analysis.confidence,
                "recommendation": analysis.recommendation,
                "summary": analysis.summary,
            })
        except Exception as exc:
            rows.append({
                "candidate_profile_id": profile.id,
                "data_completeness": profile.data_completeness,
                "fit_score": None,
                "confidence": "ERROR",
                "recommendation": "",
                "summary": str(exc)[:500],
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Ручной прогон Fit scoring на реальных кандидатах для сверки с HR")
    parser.add_argument("--course-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--csv", type=str, default=None, help="путь для CSV-вывода вместо stdout")
    args = parser.parse_args()

    settings = Settings()
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=IDENTITY_RESOLVER_TABLES)

    application_ids = _application_ids_for_course(platform_base, args.course_id)

    with Session(write_engine) as session:
        vacancy_profile = session.scalar(
            select(VacancyProfile).where(
                VacancyProfile.course_id == args.course_id, VacancyProfile.is_current.is_(True)
            )
        )
        if vacancy_profile is None:
            print(f"No current VacancyProfile for course_id={args.course_id}", file=sys.stderr)
            raise SystemExit(1)

        candidates = session.scalars(
            select(CandidateProfile).where(
                CandidateProfile.application_id.in_(application_ids),
                CandidateProfile.is_superseded.is_(False),
            )
        ).all()
        sample = _sample_diverse(list(candidates), args.limit)
        if not sample:
            print(f"No candidates found for course_id={args.course_id}", file=sys.stderr)
            raise SystemExit(1)

        llm_client = OpenRouterClient(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
        rows = _run_sample(session, sample=sample, vacancy_profile=vacancy_profile, llm_client=llm_client)

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
