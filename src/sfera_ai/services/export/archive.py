import re
import zipfile
from io import BytesIO

from sqlalchemy.orm import Session

from sfera_ai.services.candidate_transfer import mark_candidate_transferred
from sfera_ai.services.export.ai_card import candidate_display_name, render_ai_card_pdf
from sfera_ai.services.export.files import collect_export_files

_PDF_MAGIC = b"%PDF"
_DOCX_MAGIC = b"PK\x03\x04"
_SANITIZE_RE = re.compile(r"[^A-Za-zА-Яа-яЁё0-9_-]+")


def _sniff_resume_extension(file_bytes: bytes) -> str:
    if file_bytes.startswith(_PDF_MAGIC):
        return "pdf"
    if file_bytes.startswith(_DOCX_MAGIC):
        return "docx"
    return "bin"


def _folder_name(candidate_profile_id: int, full_name: str) -> str:
    # step-E9-03 DoD — санитайзинг ФИО, fallback candidate_<id> при отсутствии имени.
    # Сейчас источника ФИО нет (candidate_display_name всегда возвращает фолбэк) —
    # ветка "есть имя" готова на будущее, когда источник появится.
    if full_name == candidate_display_name(candidate_profile_id):
        return f"candidate_{candidate_profile_id}"
    sanitized = _SANITIZE_RE.sub("_", full_name).strip("_")
    return sanitized or f"candidate_{candidate_profile_id}"


def build_candidates_export_archive(
    session: Session,
    platform_base,
    candidate_profile_ids: list[int],
    course_id: int,
    *,
    hh_client,
    s3_client,
    s3_bucket: str,
) -> bytes:
    """step-E9-03 — zip на несколько кандидатов, выбранных в UI: одна подпапка на
    кандидата (`card.pdf`/`resume.<ext>`/`video.mp4`), формат согласован с владельцем
    2026-08-31. Недоступные файлы не блокируют экспорт остальных — фиксируются в
    `manifest.txt` подпапки. step-E15-05 — «передан» (`CandidateVacancyTransfer`)
    помечается только кандидат, у которого реально собрался `card.pdf`."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for candidate_profile_id in candidate_profile_ids:
            full_name = candidate_display_name(candidate_profile_id)
            folder = _folder_name(candidate_profile_id, full_name)
            unavailable: list[str] = []

            pdf = render_ai_card_pdf(session, candidate_profile_id, course_id)
            if pdf is not None:
                archive.writestr(f"{folder}/card.pdf", pdf)
                mark_candidate_transferred(session, candidate_profile_id=candidate_profile_id, course_id=course_id)
            else:
                unavailable.append("card.pdf: недоступно (нет текущего анализа)")

            files = collect_export_files(
                session, platform_base, candidate_profile_id,
                hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket,
            )

            resume = files["resume"]
            if resume["available"]:
                ext = _sniff_resume_extension(resume["bytes"])
                archive.writestr(f"{folder}/resume.{ext}", resume["bytes"])
            else:
                unavailable.append("resume: недоступно (резюме не найдено)")

            video = files["video"]
            if video["available"]:
                archive.writestr(f"{folder}/video.mp4", video["bytes"])
            else:
                unavailable.append("video.mp4: недоступно (истёк срок хранения)")

            if unavailable:
                archive.writestr(f"{folder}/manifest.txt", "\n".join(unavailable) + "\n")

    return buffer.getvalue()
