import argparse
import csv
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import RESUME_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services import fit_scoring
from sfera_ai.services.candidate_facts import build_or_update_candidate_facts
from sfera_ai.services.fit_scoring import run_fit_scoring
from sfera_ai.services.resume_pipeline import reprocess_stale_resume_extracts

_FIELDNAMES = ("candidate_profile_id", "fit_score", "criteria_scores", "error")


def _stale_candidate_profile_ids_for_course(session: Session, course_id: int) -> list[int]:
    """Кандидаты курса, у которых текущий `CandidateVacancyAnalysis` посчитан ещё
    старым промптом (`fit_scoring.PROMPT_VERSION`) — те самые «100 вместо 10/10»
    и критерии-переменные из E19-E22, обнаруженные владельцем на реальном
    кандидате уже после деплоя фикса (04_STATE.md, шаг E21-01: «старые записи
    отдельный фикс не входит»)."""
    rows = session.scalars(
        select(CandidateVacancyAnalysis.candidate_profile_id).where(
            CandidateVacancyAnalysis.course_id == course_id,
            CandidateVacancyAnalysis.is_current.is_(True),
            CandidateVacancyAnalysis.prompt_version != fit_scoring.PROMPT_VERSION,
        )
    ).all()
    return list(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ре-обсчёт кандидатов, посчитанных старым промптом (до деплоя фикса) — "
            "переизвлекает устаревшие ResumeExtract, пересобирает facts, пересчитывает fit_scoring."
        )
    )
    parser.add_argument("--course-id", type=int, required=True)
    parser.add_argument(
        "--candidate-ids", type=str, default=None,
        help="через запятую id CandidateProfile — точечный ре-обсчёт вместо автопоиска устаревших по курсу",
    )
    parser.add_argument("--csv", type=str, default=None, help="путь для CSV-сводки вместо stdout")
    args = parser.parse_args()

    settings = Settings()
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=RESUME_DETECTION_TABLES)
    llm_client = OpenRouterClient(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)

    rows = []
    with Session(write_engine) as session:
        vacancy_profile = session.scalar(
            select(VacancyProfile).where(
                VacancyProfile.course_id == args.course_id, VacancyProfile.is_current.is_(True)
            )
        )
        if vacancy_profile is None:
            print(f"No current VacancyProfile for course_id={args.course_id}", file=sys.stderr)
            raise SystemExit(1)

        candidate_profile_ids = (
            [int(v) for v in args.candidate_ids.split(",") if v.strip()]
            if args.candidate_ids
            else _stale_candidate_profile_ids_for_course(session, args.course_id)
        )
        if not candidate_profile_ids:
            print("Устаревших кандидатов не найдено, нечего пересчитывать", file=sys.stderr)
            return

        for candidate_profile_id in candidate_profile_ids:
            profile = session.get(CandidateProfile, candidate_profile_id)
            if profile is None:
                rows.append(
                    {
                        "candidate_profile_id": candidate_profile_id, "fit_score": None,
                        "criteria_scores": None, "error": "CandidateProfile не найден",
                    }
                )
                continue
            try:
                reprocess_stale_resume_extracts(
                    session, llm_client=llm_client, candidate_profile_ids=[profile.id]
                )
                profile = build_or_update_candidate_facts(session, platform_base, llm_client, profile)
                analysis = run_fit_scoring(
                    session, candidate_profile=profile, vacancy_profile=vacancy_profile, llm_client=llm_client
                )
                rows.append(
                    {
                        "candidate_profile_id": profile.id, "fit_score": analysis.fit_score,
                        "criteria_scores": analysis.criteria_scores, "error": "",
                    }
                )
                print(f"OK candidate_profile_id={profile.id} fit_score={analysis.fit_score}", file=sys.stderr)
            except Exception as exc:
                rows.append(
                    {
                        "candidate_profile_id": candidate_profile_id, "fit_score": None,
                        "criteria_scores": None, "error": str(exc)[:500],
                    }
                )
                print(f"ERROR candidate_profile_id={candidate_profile_id}: {exc}", file=sys.stderr)

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
