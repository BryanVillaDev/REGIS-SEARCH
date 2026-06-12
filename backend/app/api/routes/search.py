import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_client_ip, get_current_user
from app.models.schemas import (
    BulkCedulasRequest,
    BulkNombresRequest,
    JobPublic,
    NameSearchResponse,
)
from app.services.audit import record_audit
from app.services.jobs import create_cedulas_job, create_nombres_job
from app.services.records import search_by_name
from app.services.users import UserRecord

router = APIRouter()


@router.get("/name", response_model=NameSearchResponse)
def name_search(
    request: Request,
    apellido1: str | None = None,
    apellido2: str | None = None,
    nombre1: str | None = None,
    nombre2: str | None = None,
    mode: str = "prefix",
    limit: int = 50,
    offset: int = 0,
    user: UserRecord = Depends(get_current_user),
) -> NameSearchResponse:
    started = time.perf_counter()
    status_label = "ok"
    result_count = 0
    try:
        response = search_by_name(
            apellido1=apellido1,
            apellido2=apellido2,
            nombre1=nombre1,
            nombre2=nombre2,
            mode=mode,
            limit=limit,
            offset=offset,
        )
        result_count = len(response.items)
        return response
    except ValueError as exc:
        status_label = "bad_request"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        record_audit(
            user=user,
            event="name_search",
            filters={
                "apellido1": apellido1,
                "apellido2": apellido2,
                "nombre1": nombre1,
                "nombre2": nombre2,
                "mode": mode,
                "limit": limit,
                "offset": offset,
            },
            result_count=result_count,
            status=status_label,
            duration_ms=int((time.perf_counter() - started) * 1000),
            ip=get_client_ip(request),
        )


@router.post("/cedulas", response_model=JobPublic, status_code=status.HTTP_202_ACCEPTED)
def bulk_cedulas(
    payload: BulkCedulasRequest,
    request: Request,
    user: UserRecord = Depends(get_current_user),
) -> JobPublic:
    started = time.perf_counter()
    status_label = "queued"
    result_count = 0
    try:
        job = create_cedulas_job(payload.cedulas, user)
        result_count = job.unique_count
        return job
    except ValueError as exc:
        status_label = "bad_request"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        record_audit(
            user=user,
            event="bulk_cedulas",
            filters={"input_type": type(payload.cedulas).__name__},
            result_count=result_count,
            status=status_label,
            duration_ms=int((time.perf_counter() - started) * 1000),
            ip=get_client_ip(request),
        )


@router.post("/nombres", response_model=JobPublic, status_code=status.HTTP_202_ACCEPTED)
def bulk_nombres(
    payload: BulkNombresRequest,
    request: Request,
    user: UserRecord = Depends(get_current_user),
) -> JobPublic:
    started = time.perf_counter()
    status_label = "queued"
    result_count = 0
    try:
        job = create_nombres_job(payload.nombres, user)
        result_count = job.unique_count
        return job
    except ValueError as exc:
        status_label = "bad_request"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        record_audit(
            user=user,
            event="bulk_nombres",
            filters={"input_type": type(payload.nombres).__name__},
            result_count=result_count,
            status=status_label,
            duration_ms=int((time.perf_counter() - started) * 1000),
            ip=get_client_ip(request),
        )
