# Controles que valen para todas las rutas:
# - X-Request-Id: se devuelve en toda respuesta; si no llega o es inválido, M2 genera uno (nunca 400).
# - 413 si el cuerpo supera 1 MiB.
# - 415 si el cuerpo no es application/json.
import re
import uuid

from fastapi import Request
from starlette.routing import Match

import config
from errores import problema

_FORMATO_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_METODOS_CON_CUERPO = {"POST", "PUT", "PATCH"}


def _ruta_y_metodo_existen(request: Request) -> bool:
    for ruta in request.app.router.routes:
        coincidencia, _ = ruta.matches(request.scope)
        if coincidencia == Match.FULL:
            return True
    return False


def _trae_cuerpo(request: Request) -> bool:
    largo = request.headers.get("content-length")
    if largo is not None:
        return largo.strip() not in ("", "0")
    return "transfer-encoding" in request.headers


async def controles_generales(request: Request, call_next):
    recibido = request.headers.get("x-request-id", "")
    request.state.request_id = recibido if _FORMATO_REQUEST_ID.match(recibido) else str(uuid.uuid4())

    if request.method in _METODOS_CON_CUERPO and _ruta_y_metodo_existen(request) and _trae_cuerpo(request):
        largo = request.headers.get("content-length")
        if largo and largo.isdigit() and int(largo) > config.MAX_BODY_BYTES:
            return problema(request, 413, "El cuerpo supera 1 MiB.")
        tipo = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if tipo != "application/json":
            return problema(request, 415, "El cuerpo tiene que ser application/json.")

    respuesta = await call_next(request)
    respuesta.headers["X-Request-Id"] = request.state.request_id
    return respuesta
