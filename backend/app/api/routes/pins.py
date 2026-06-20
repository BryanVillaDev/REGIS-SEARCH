from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_key
from app.models.schemas import PinCombinationsResponse
from app.services.records import get_pin_combinations

router = APIRouter()


@router.get(
    "/{cedula}",
    response_model=PinCombinationsResponse,
    dependencies=[Depends(require_api_key)],
)
def pin_combinations(cedula: int) -> PinCombinationsResponse:
    """Combinaciones de 4 digitos derivadas de la fecha de nacimiento de la cedula.

    Autenticacion: header ``X-API-Key`` (sin JWT).
    """
    detail = get_pin_combinations(cedula)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cedula no encontrada",
        )
    return detail
