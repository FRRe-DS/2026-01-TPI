# GET /health: disponibilidad del servicio. No exige token.
from fastapi import APIRouter, Request

import config
import database
from errores import problema
from models import Salud

router = APIRouter(tags=["Salud"])


@router.get("/health", operation_id="verificarSalud", response_model=Salud)
def verificar_salud(request: Request):
    """200 si el servicio y su base responden; si no, 503."""
    if not database.base_disponible():
        return problema(request, 503, "La base de datos de M2 no responde.",
                        headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)})
    return Salud()
