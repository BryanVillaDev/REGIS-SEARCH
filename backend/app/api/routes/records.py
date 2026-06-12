import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_client_ip, get_current_user
from app.models.schemas import RecordDetail
from app.services.audit import record_audit
from app.services.records import get_record_detail
from app.services.users import UserRecord

router = APIRouter()


@router.get("/{aninuip}", response_model=RecordDetail)
def get_record(
    aninuip: int,
    request: Request,
    user: UserRecord = Depends(get_current_user),
) -> RecordDetail:
    started = time.perf_counter()
    status_label = "ok"
    result_count = 0
    try:
        detail = get_record_detail(aninuip)
        if not detail:
            status_label = "not_found"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado",
            )
        result_count = 1
        return detail
    finally:
        record_audit(
            user=user,
            event="record_lookup",
            filters={"aninuip": aninuip},
            result_count=result_count,
            status=status_label,
            duration_ms=int((time.perf_counter() - started) * 1000),
            ip=get_client_ip(request),
        )
