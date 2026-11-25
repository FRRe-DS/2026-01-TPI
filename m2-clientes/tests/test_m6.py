import httpx
import pytest
import config
from errores import ErrorDominio
from integraciones.m6 import _solicitar_m6, obtener_viaje, listar_viajes


def responder_error(request):
    return httpx.Response(500)


def responder_no_encontrado(request):
    return httpx.Response(404)


def responder_error_cliente(request):
    responder_error_cliente.intentos += 1
    return httpx.Response(responder_error_cliente.codigo)


def responder_error_conexion(request):
    responder_error_conexion.intentos += 1
    raise httpx.ConnectError("No se pudo conectar con M6", request=request)


def responder_error_lectura(request):
    raise httpx.ReadError(
        "Se interrumpió la comunicación con M6",
        request=request,
    )


def responder_timeout(request):
    raise httpx.TimeoutException("M6 tardó demasiado", request=request)


def responder_primero_error(request):
    if responder_primero_error.intentos == 0:
        responder_primero_error.intentos += 1
        return httpx.Response(500)

    return httpx.Response(200, json={"items": [], "total": 0})


def responder_lista_viajes(request):
    responder_lista_viajes.solicitud = request

    return httpx.Response(
        200,
        json={
            "items": [],
            "page": 2,
            "pageSize": 10,
            "total": 0,
        },
    )


def test_m6_reintenta_y_obtiene_respuesta_correcta():
    responder_primero_error.intentos = 0
    transporte = httpx.MockTransport(responder_primero_error)
    respuesta = _solicitar_m6(
        "GET",
        "/trips",
        "Bearer token-prueba",
        transporte=transporte,
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"items": [], "total": 0}
    assert responder_primero_error.intentos == 1


def test_m6_dos_errores_500_generan_503():
    transporte = httpx.MockTransport(responder_error)
    with pytest.raises(ErrorDominio) as error:
        _solicitar_m6(
            "GET",
            "/trips",
            "Bearer token-prueba",
            transporte=transporte,
        )

    assert error.value.status == 503
    assert error.value.headers == {"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)}


def test_m6_dos_errores_conexion_generan_503():
    responder_error_conexion.intentos = 0
    transporte = httpx.MockTransport(responder_error_conexion)
    with pytest.raises(ErrorDominio) as error:
        _solicitar_m6(
            "GET",
            "/trips",
            "Bearer token-prueba",
            transporte=transporte,
        )

    assert error.value.status == 503
    assert error.value.headers == {"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)}
    assert responder_error_conexion.intentos == 2


def test_m6_dos_timeout_generan_503():
    transporte = httpx.MockTransport(responder_timeout)

    with pytest.raises(ErrorDominio) as error:
        _solicitar_m6(
            "GET",
            "/trips",
            "Bearer token-prueba",
            transporte=transporte,
        )

    assert error.value.status == 503
    assert error.value.headers == {"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)}


def test_obtener_viaje_devuelve_none_si_m6_responde_404():
    transporte = httpx.MockTransport(responder_no_encontrado)

    viaje = obtener_viaje(
        "viaje-inexistente",
        "Bearer token-prueba",
        transporte=transporte,
    )

    assert viaje is None


def test_listar_viajes_envia_parametros_correctos():
    transporte = httpx.MockTransport(responder_lista_viajes)

    respuesta = listar_viajes(
        cliente_id="cliente-123",
        page=1,
        size=10,
        autorizacion="Bearer token-prueba",
        transporte=transporte,
    )

    assert respuesta == {
        "items": [],
        "page": 2,
        "pageSize": 10,
        "total": 0,
    }

    solicitud = responder_lista_viajes.solicitud
    assert solicitud.url.path == "/trips"
    assert solicitud.url.params["clientId"] == "cliente-123"
    assert solicitud.url.params["page"] == "2"
    assert solicitud.url.params["pageSize"] == "10"
    assert solicitud.headers["Authorization"] == "Bearer token-prueba"


def test_m6_dos_errores_lectura_generan_503():
    transporte = httpx.MockTransport(responder_error_lectura)

    with pytest.raises(ErrorDominio) as error:
        _solicitar_m6(
            "GET",
            "/trips",
            "Bearer token-prueba",
            transporte=transporte,
        )

    assert error.value.status == 503
    assert error.value.headers == {"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)}


@pytest.mark.parametrize("codigo", [400, 401, 403])
def test_obtener_viaje_convierte_errores_4xx_en_503(codigo):
    responder_error_cliente.codigo = codigo
    responder_error_cliente.intentos = 0

    transporte = httpx.MockTransport(responder_error_cliente)

    with pytest.raises(ErrorDominio) as error:
        obtener_viaje(
            "viaje-123",
            "Bearer token-prueba",
            transporte=transporte,
        )

    assert error.value.status == 503
    assert error.value.tipo == "/errores/dependencia-no-disponible"
    assert error.value.headers == {"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)}
    assert responder_error_cliente.intentos == 1
