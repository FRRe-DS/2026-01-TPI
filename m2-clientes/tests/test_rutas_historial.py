# Tests del historial de viajes del cliente (RF-2.4).

import uuid

import pytest

from conftest import auth, crear_perfil, es_problema
from contrato import validar, respuestas_declaradas
from errores import ErrorDominio
from integraciones import m6
from rutas import historial


def ruta(sub):
    return f"/api/v1/clientes/{sub}/viajes"


@pytest.fixture
def sub(cliente_http):
    """Crea un cliente con perfil."""
    s = str(uuid.uuid4())
    assert crear_perfil(cliente_http, s).status_code == 201
    return s


@pytest.fixture
def m6_simulado(monkeypatch):
    """Simula la respuesta de M6 al listar viajes."""
    simulado = {"respuesta": {}, "llamadas": []}

    def listar_viajes(cliente_id, page, size, autorizacion):
        simulado["llamadas"].append((cliente_id, page, size, autorizacion))
        return simulado["respuesta"]

    monkeypatch.setattr(m6, "listar_viajes", listar_viajes)

    return simulado


def test_cliente_consulta_su_historial(cliente_http, sub, m6_simulado):
    m6_simulado["respuesta"] = {
        "items": [],
        "page": 1,
        "pageSize": 20,
        "total": 0,
    }

    encabezados = auth(["CLIENTE"], sub)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    validar("PaginaViajes", cuerpo)

    assert cuerpo["items"] == []
    assert cuerpo["page"] == 0
    assert cuerpo["size"] == 20
    assert cuerpo["totalElementos"] == 0
    assert cuerpo["totalPaginas"] == 0


def test_cliente_no_puede_consultar_historial_ajeno(cliente_http, sub, m6_simulado):
    otro_cliente = str(uuid.uuid4())
    assert crear_perfil(cliente_http, otro_cliente).status_code == 201

    encabezados = auth(["CLIENTE"], otro_cliente)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 403
    assert m6_simulado["llamadas"] == []


def test_operador_puede_consultar_historial(cliente_http, sub, m6_simulado):
    m6_simulado["respuesta"] = {
        "items": [],
        "page": 1,
        "pageSize": 20,
        "total": 0,
    }

    encabezados = auth(["OPERADOR"])

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["items"] == []


def test_historial_sin_perfil_da_404(cliente_http, m6_simulado):
    cliente_inexistente = str(uuid.uuid4())

    encabezados = auth(["CLIENTE"], cliente_inexistente)

    respuesta = cliente_http.get(
        ruta(cliente_inexistente),
        headers=encabezados,
    )

    assert respuesta.status_code == 404
    assert m6_simulado["llamadas"] == []


def test_a_m6_se_le_pasa_el_token_del_cliente(cliente_http, sub, m6_simulado):
    m6_simulado["respuesta"] = {
        "items": [],
        "page": 1,
        "pageSize": 20,
        "total": 0,
    }

    encabezados = auth(["CLIENTE"], sub)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 200
    assert len(m6_simulado["llamadas"]) == 1

    cliente_id, page, size, autorizacion = m6_simulado["llamadas"][0]

    assert cliente_id == sub
    assert page == 0
    assert size == 20
    assert autorizacion == encabezados["Authorization"]


def test_transformar_viajes_de_m6_a_m2(cliente_http, sub, m6_simulado):
    viaje_id = str(uuid.uuid4())
    conductor_id = str(uuid.uuid4())

    m6_simulado["respuesta"] = {
        "items": [
            {
                "id": viaje_id,
                "state": "COMPLETED",
                "vehicleType": "CAR",
                "clientId": sub,
                "driverId": conductor_id,
                "originAddress": "Resistencia",
                "destinationAddress": "Corrientes",
                "createdAt": "2026-11-24T10:00:00Z",
                "completedAt": "2026-11-24T10:30:00Z",
            }
        ],
        "page": 1,
        "pageSize": 20,
        "total": 1,
    }

    encabezados = auth(["CLIENTE"], sub)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    validar("PaginaViajes", cuerpo)

    viaje = cuerpo["items"][0]

    assert viaje["viajeId"] == viaje_id
    assert viaje["estado"] == "COMPLETED"
    assert viaje["tipoVehiculo"] == "AUTO"
    assert viaje["origen"] == "Resistencia"
    assert viaje["destino"] == "Corrientes"
    assert viaje["conductorId"] == conductor_id
    assert viaje["iniciadoEn"] == "2026-11-24T10:00:00Z"
    assert viaje["finalizadoEn"] == "2026-11-24T10:30:00Z"
    assert viaje["calificado"] is False


def test_transformar_moto_de_m6_a_m2(cliente_http, sub, m6_simulado):
    viaje_id = str(uuid.uuid4())

    m6_simulado["respuesta"] = {
        "items": [
            {
                "id": viaje_id,
                "state": "IN_PROGRESS",
                "vehicleType": "MOTORCYCLE",
                "clientId": sub,
                "originAddress": "Resistencia",
                "destinationAddress": "Barranqueras",
                "createdAt": "2026-11-24T10:00:00Z",
            }
        ],
        "page": 1,
        "pageSize": 20,
        "total": 1,
    }

    respuesta = cliente_http.get(
        ruta(sub),
        headers=auth(["CLIENTE"], sub),
    )

    assert respuesta.status_code == 200

    viaje = respuesta.json()["items"][0]

    assert viaje["tipoVehiculo"] == "MOTO"
    assert viaje["estado"] == "IN_PROGRESS"
    assert "finalizadoEn" not in viaje
    assert "conductorId" not in viaje


@pytest.mark.parametrize("tipo_m6, tipo_m2", [("AUTO", "AUTO"), ("MOTO", "MOTO")])
def test_tipo_de_vehiculo_en_castellano_de_m6(cliente_http, sub, m6_simulado, tipo_m6, tipo_m2):
    # Los M6 reales (grupos 5 y 12) mandan AUTO/MOTO en vez de CAR/MOTORCYCLE
    m6_simulado["respuesta"] = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "state": "COMPLETED",
                "vehicleType": tipo_m6,
                "clientId": sub,
                "createdAt": "2026-11-24T10:00:00Z",
            }
        ],
        "page": 1,
        "pageSize": 20,
        "total": 1,
    }

    respuesta = cliente_http.get(
        ruta(sub),
        headers=auth(["CLIENTE"], sub),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["items"][0]["tipoVehiculo"] == tipo_m2


def test_paginacion_del_historial(cliente_http, sub, m6_simulado):
    m6_simulado["respuesta"] = {
        "items": [],
        "page": 2,
        "pageSize": 10,
        "total": 25,
    }

    respuesta = cliente_http.get(
        ruta(sub),
        params={"page": 1, "size": 10},
        headers=auth(["CLIENTE"], sub),
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["page"] == 1
    assert cuerpo["size"] == 10
    assert cuerpo["totalElementos"] == 25
    assert cuerpo["totalPaginas"] == 3


def test_m6_no_disponible_devuelve_503(cliente_http, sub, monkeypatch):
    def m6_caido(cliente_id, page, size, autorizacion):
        raise ErrorDominio(
            503,
            "/errores/dependencia-no-disponible",
            "M6 no está disponible",
            "M6 no respondió.",
            headers={"Retry-After": "5"},
        )

    monkeypatch.setattr(m6, "listar_viajes", m6_caido)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=auth(["CLIENTE"], sub),
    )

    assert respuesta.status_code == 503
    assert respuesta.headers["Retry-After"] == "5"

    cuerpo = es_problema(respuesta, 503, generico=False)
    assert cuerpo["type"] == "/errores/dependencia-no-disponible"


@pytest.mark.parametrize(
    "params",
    [
        {"page": -1},
        {"size": 0},
        {"size": 101},
    ],
)
def test_historial_con_paginacion_invalida_da_400(
    cliente_http, sub, m6_simulado, params
):
    respuesta = cliente_http.get(
        ruta(sub),
        params=params,
        headers=auth(["CLIENTE"], sub),
    )

    assert respuesta.status_code == 400
    assert m6_simulado["llamadas"] == []


def test_servicio_no_puede_consultar_historial(cliente_http, sub, m6_simulado):
    encabezados = auth(["SERVICIO"], "m9-reservas")

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 403
    assert m6_simulado["llamadas"] == []


def test_codigos_usados_estan_en_el_contrato():
    codigos = {200, 400, 401, 403, 404, 500, 503}

    assert codigos <= respuestas_declaradas("listarHistorialViajes")


def test_viaje_calificado_devuelve_true(
    cliente_http, sub, m6_simulado, base_en_memoria
):
    viaje_id = str(uuid.uuid4())
    conductor_id = str(uuid.uuid4())

    m6_simulado["respuesta"] = {
        "items": [
            {
                "id": viaje_id,
                "state": "COMPLETED",
                "vehicleType": "CAR",
                "clientId": sub,
                "driverId": conductor_id,
                "originAddress": "Resistencia",
                "destinationAddress": "Corrientes",
                "createdAt": "2026-11-24T10:00:00Z",
                "completedAt": "2026-11-24T10:30:00Z",
            }
        ],
        "page": 1,
        "pageSize": 20,
        "total": 1,
    }

    base_en_memoria["calificaciones"].insert_one(
        {
            "_id": str(uuid.uuid4()),
            "clienteId": sub,
            "viajeId": viaje_id,
            "conductorId": conductor_id,
            "puntaje": 5,
        }
    )

    encabezados = auth(["CLIENTE"], sub)

    respuesta = cliente_http.get(
        ruta(sub),
        headers=encabezados,
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()
    validar("PaginaViajes", cuerpo)

    viaje = cuerpo["items"][0]

    assert viaje["viajeId"] == viaje_id
    assert viaje["calificado"] is True
