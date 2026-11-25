# Conector a M6 (Viajes): M2 le pide los viajes por su API, nunca a su base (RNF-05).
#
# El conector permite consultar viajes individuales y listar viajes mediante la API de M6.
# Implementa timeout de 2 segundos por intento, un reintento ante errores de red o respuestas 5xx
# y devuelve un error 503 si M6 continúa sin estar disponible.
# Ver docs/tareas/T02-historial-de-viajes.md.
import httpx
import config
from errores import ErrorDominio


def _solicitar_m6(
    metodo: str,
    ruta: str,
    autorizacion: str,
    parametros: dict | None = None,
    transporte: httpx.BaseTransport | None = None,
) -> httpx.Response:
    encabezados = {"Authorization": autorizacion}

    with httpx.Client(transport=transporte) as cliente:
        for intento in range(2):
            try:
                respuesta = cliente.request(
                    metodo,
                    f"{config.M6_URL}{ruta}",
                    headers=encabezados,
                    params=parametros,
                    timeout=config.M6_TIMEOUT_SEGUNDOS,
                )

                if respuesta.status_code >= 500:
                    if intento == 0:
                        continue

                    raise ErrorDominio(
                        503,
                        "/errores/dependencia-no-disponible",
                        "M6 no está disponible",
                        "M6 respondió con un error del servidor.",
                        headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)},
                    )
                return respuesta

            except (httpx.TimeoutException, httpx.NetworkError):
                if intento == 0:
                    continue

                raise ErrorDominio(
                    503,
                    "/errores/dependencia-no-disponible",
                    "M6 no está disponible",
                    "No se pudo establecer conexión con M6.",
                    headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)},
                )


def obtener_viaje(
    viaje_id: str, autorizacion: str, transporte: httpx.BaseTransport | None = None
) -> dict | None:
    """GET /trips/{id} de M6. Devuelve None si M6 responde 404."""
    respuesta = _solicitar_m6(
        "GET", f"/trips/{viaje_id}", autorizacion, transporte=transporte
    )

    if respuesta.status_code == 404:
        return None

    respuesta.raise_for_status()
    return respuesta.json()


def listar_viajes(
    cliente_id: str,
    page: int,
    size: int,
    autorizacion: str,
    transporte: httpx.BaseTransport | None = None,
) -> dict:
    parametros = {
        "clientId": cliente_id,
        "page": page + 1,
        "pageSize": size,
    }

    respuesta = _solicitar_m6(
        "GET",
        "/trips",
        autorizacion,
        parametros,
        transporte=transporte,
    )

    respuesta.raise_for_status()
    return respuesta.json()
