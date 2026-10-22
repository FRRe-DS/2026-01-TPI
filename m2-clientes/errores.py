# Respuestas de error en formato RFC 9457 (application/problem+json), como pide el contrato.
#
# - Los errores genéricos (400, 401, 403, 404, 405, 413, 415, 500 y 503 de la base)
#   usan type "about:blank" y un title fijo en español.
# - Los errores de dominio (409, 422, 503 de otro módulo) tienen su propio type.
from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

import config

TITULOS = {
    400: "Solicitud inválida",
    401: "No autenticado",
    403: "Sin permiso",
    404: "No encontrado",
    405: "Método no permitido",
    413: "Cuerpo demasiado grande",
    415: "Tipo de contenido no soportado",
    500: "Error interno",
    503: "Servicio no disponible",
}


class ErrorDominio(Exception):
    """Error de negocio con type propio (por ejemplo, un perfil que ya existe)."""

    def __init__(self, status: int, tipo: str, titulo: str, detalle: str | None = None):
        self.status = status
        self.tipo = tipo
        self.titulo = titulo
        self.detalle = detalle


def problema(request: Request, status: int, detalle: str | None = None, tipo: str = "about:blank",
             titulo: str | None = None, headers: dict | None = None) -> JSONResponse:
    cuerpo = {
        "type": tipo,
        "title": titulo or TITULOS.get(status, "Error"),
        "status": status,
        "instance": request.url.path,
    }
    if detalle:
        cuerpo["detail"] = detalle
    encabezados = dict(headers or {})
    # Los errores también devuelven X-Request-Id (incluso un 500)
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        encabezados["X-Request-Id"] = request_id
    return JSONResponse(cuerpo, status_code=status, headers=encabezados,
                        media_type="application/problem+json")


def _texto_validacion(exc: RequestValidationError) -> str:
    """Arma un detalle legible que nombra el campo con error (el contrato no usa errores[])."""
    partes = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "path", "query", "header")]
        campo = ".".join(loc) or "cuerpo"
        partes.append(f"{campo}: {err.get('msg')}")
    return "; ".join(partes)


async def manejar_http(request: Request, exc: StarletteHTTPException):
    detalle = exc.detail if isinstance(exc.detail, str) else None
    # Los errores que arma Starlette solos (404 de ruta, 405) traen la frase en inglés: no la mostramos
    try:
        if detalle == HTTPStatus(exc.status_code).phrase:
            detalle = None
    except ValueError:
        pass
    encabezados = dict(getattr(exc, "headers", None) or {})
    if exc.status_code == 405:
        encabezados["Allow"] = _metodos_de_la_ruta(request)
    return problema(request, exc.status_code, detalle, headers=encabezados)


_METODOS_HTTP = ("GET", "POST", "PUT", "PATCH", "DELETE")


def _metodos_de_la_ruta(request: Request) -> str:
    """Todos los métodos que admite la ruta pedida (Starlette solo lista los de la primera que coincide).

    Se prueba cada método contra las rutas de la app, así funciona también con los routers incluidos.
    """
    admitidos = []
    for metodo in _METODOS_HTTP:
        scope = {**request.scope, "method": metodo}
        if any(ruta.matches(scope)[0] == Match.FULL for ruta in request.app.router.routes):
            admitidos.append(metodo)
    return ", ".join(admitidos)


async def manejar_validacion(request: Request, exc: RequestValidationError):
    # Cuerpo, parámetros o encabezados con formato inválido: 400 (el 422 queda para reglas de negocio)
    return problema(request, 400, _texto_validacion(exc))


async def manejar_dominio(request: Request, exc: ErrorDominio):
    return problema(request, exc.status, exc.detalle, tipo=exc.tipo, titulo=exc.titulo)


async def manejar_base(request: Request, exc: PyMongoError):
    return problema(request, 503, "La base de datos de M2 no responde.",
                    headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)})


async def manejar_inesperado(request: Request, exc: Exception):
    # No exponemos detalles internos
    return problema(request, 500)


def registrar(app):
    app.add_exception_handler(StarletteHTTPException, manejar_http)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(ErrorDominio, manejar_dominio)
    app.add_exception_handler(PyMongoError, manejar_base)
    app.add_exception_handler(Exception, manejar_inesperado)
