from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.models.schemas import JobPublic
from app.services.jobs import get_download_file, get_job, list_jobs
from app.services.users import UserRecord

router = APIRouter()


@router.get("", response_model=list[JobPublic])
def jobs(
    limit: int = Query(default=50, ge=1, le=200),
    user: UserRecord = Depends(get_current_user),
) -> list[JobPublic]:
    return list_jobs(user, limit=limit)


@router.get("/{job_id}", response_model=JobPublic)
def job_detail(job_id: str, user: UserRecord = Depends(get_current_user)) -> JobPublic:
    job = get_job(job_id, user)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job no encontrado",
        )
    return job.public()


@router.get("/{job_id}/download")
def job_download(
    job_id: str,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    user: UserRecord = Depends(get_current_user),
) -> FileResponse:
    file_path = get_download_file(job_id, user, format)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no disponible",
        )
    media_type = (
        "text/csv"
        if format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
    )
