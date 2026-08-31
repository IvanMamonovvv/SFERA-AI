from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from sfera_ai.api.deps import get_hh_client, get_platform_engine, get_s3_bucket, get_s3_client, get_session, resolve_course_or_404
from sfera_ai.services.export.archive import build_candidates_export_archive

router = APIRouter()


class CandidatesExportRequest(BaseModel):
    candidate_profile_ids: list[int]


@router.post("/export/")
def export_candidates(
    course_uuid: str,
    body: CandidatesExportRequest,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
    hh_client=Depends(get_hh_client),
    s3_client=Depends(get_s3_client),
    s3_bucket: str = Depends(get_s3_bucket),
) -> Response:
    course_id, platform_base = resolve_course_or_404(platform_engine, course_uuid)
    archive_bytes = build_candidates_export_archive(
        session, platform_base, body.candidate_profile_ids, course_id,
        hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket,
    )
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="export-course-{course_id}.zip"'},
    )
