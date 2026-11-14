# Tests de calificaciones al conductor (RF-2.5).
# M6 se simula: obtener_viaje se reemplaza por una función que busca en un diccionario de viajes de
# ejemplo. Así estas pruebas no necesitan que M6 exista ni que el conector de T02 esté terminado.
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import auth, crear_perfil, es_problema
from contrato import respuestas_declaradas, validar
from errores import ErrorDominio
from integraciones import m6
from rutas import calificaciones

CONDUCTOR = str(uuid.uuid4())
VIAJE = str(uuid.uuid4())  # para los cuerpos inválidos: el pedido no llega a buscarlo en M6


def ruta(sub, calificacion_id=None):
    base = f"/api/v1/clientes/{sub}/calificaciones"
    return f"{base}/{calificacion_id}" if calificacion_id else base


def calificar(cliente_http, sub, cuerpo, roles=("CLIENTE",), sub_token=None):
    """POST de una calificación. Por defecto, con el token del mismo cliente dueño del perfil."""
    encabezados = auth(list(roles), sub_token or sub, **{"Idempotency-Key": str(uuid.uuid4())})
    return cliente_http.post(ruta(sub), json=cuerpo, headers=encabezados)


@pytest.fixture
def sub(cliente_http):
    """Un cliente con perfil creado."""
    s = str(uuid.uuid4())
    assert crear_perfil(cliente_http, s).status_code == 201
    return s


@pytest.fixture
def m6_simulado(monkeypatch):
    """Reemplaza a M6: obtener_viaje busca en `viajes` y anota cada llamada en `llamadas`."""
    simulado = {"viajes": {}, "llamadas": []}

    def obtener_viaje(viaje_id, autorizacion):
        simulado["llamadas"].append((viaje_id, autorizacion))
        return simulado["viajes"].get(viaje_id)

    monkeypatch.setattr(m6, "obtener_viaje", obtener_viaje)
    return simulado


def nuevo_viaje(m6_simulado, cliente_id, estado="COMPLETED") -> str:
    """Agrega a M6 simulado un viaje como lo devuelve GET /trips/{id} (solo los campos que usa M2)."""
    viaje_id = str(uuid.uuid4())
    m6_simulado["viajes"][viaje_id] = {"id": viaje_id, "clientId": cliente_id, "driverId": CONDUCTOR,
                                       "state": estado}
    return viaje_id


def calificar_varios(cliente_http, m6_simulado, sub, cantidad) -> list[str]:
    """Califica `cantidad` viajes completados del cliente. Devuelve sus viajeId en el orden en que se calificaron."""
    viajes = []
    for i in range(cantidad):
        viaje_id = nuevo_viaje(m6_simulado, sub)
        assert calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 1 + i % 5}).status_code == 201
        viajes.append(viaje_id)
    return viajes


@pytest.fixture
def reloj(monkeypatch):
    """Cada calificación se guarda un minuto después de la anterior, así el orden del listado no depende del azar."""
    inicio = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    minutos = iter(range(1000))
    monkeypatch.setattr(calificaciones, "ahora", lambda: inicio + timedelta(minutes=next(minutos)))


# ------------------------------------------------------------ Calificar

def test_calificar_viaje_completado(cliente_http, sub, m6_simulado):
    viaje_id = nuevo_viaje(m6_simulado, sub)
    r = calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5, "comentario": "Muy amable"})
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    validar("Calificacion", cuerpo)
    assert (cuerpo["viajeId"], cuerpo["puntaje"], cuerpo["comentario"]) == (viaje_id, 5, "Muy amable")
    assert r.headers["Location"] == ruta(sub, cuerpo["calificacionId"])


def test_calificar_sin_comentario(cliente_http, sub, m6_simulado):
    cuerpo = calificar(cliente_http, sub, {"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 3}).json()
    validar("Calificacion", cuerpo)
    assert "comentario" not in cuerpo


def test_el_conductor_sale_de_m6(cliente_http, sub, m6_simulado):
    cuerpo = calificar(cliente_http, sub, {"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 4}).json()
    assert cuerpo["conductorId"] == CONDUCTOR


def test_a_m6_se_le_pasa_el_token_del_cliente(cliente_http, sub, m6_simulado):
    viaje_id = nuevo_viaje(m6_simulado, sub)
    encabezados = auth(["CLIENTE"], sub, **{"Idempotency-Key": str(uuid.uuid4())})
    cliente_http.post(ruta(sub), json={"viajeId": viaje_id, "puntaje": 5}, headers=encabezados)
    assert m6_simulado["llamadas"] == [(viaje_id, encabezados["Authorization"])]


def test_calificar_dos_veces_el_mismo_viaje_da_409(cliente_http, sub, m6_simulado):
    viaje_id = nuevo_viaje(m6_simulado, sub)
    calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5})
    cuerpo = es_problema(calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 1}), 409, generico=False)
    assert cuerpo["type"] == "/errores/calificacion-duplicada"
    # Quedó solo la primera, sin cambios
    items = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()["items"]
    assert [c["puntaje"] for c in items] == [5]


def test_el_mismo_viaje_escrito_en_mayusculas_tambien_da_409(cliente_http, sub, m6_simulado):
    # El viajeId se guarda en su forma normal: escribirlo distinto no esquiva el índice único
    viaje_id = nuevo_viaje(m6_simulado, sub)
    calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5})
    es_problema(calificar(cliente_http, sub, {"viajeId": viaje_id.upper(), "puntaje": 1}), 409, generico=False)


def test_si_otro_pedido_la_guarda_mientras_se_consulta_a_m6_igual_da_409(
        cliente_http, sub, m6_simulado, monkeypatch, base_en_memoria):
    # Dos pedidos al mismo tiempo: el otro guarda su calificación mientras este espera la respuesta de M6.
    # Un "if ya existe" hecho antes de consultar a M6 no lo vería y dejaría pasar los dos; el índice único
    # lo frena igual (RNF-08).
    viaje_id = nuevo_viaje(m6_simulado, sub)
    consultar_m6 = m6.obtener_viaje

    def m6_mientras_otro_pedido_guarda(viaje_pedido, autorizacion):
        base_en_memoria["calificaciones"].insert_one({
            "_id": str(uuid.uuid4()), "clienteId": sub, "viajeId": viaje_pedido, "conductorId": CONDUCTOR,
            "puntaje": 2, "creadoEn": datetime.now(timezone.utc),
        })
        return consultar_m6(viaje_pedido, autorizacion)

    monkeypatch.setattr(m6, "obtener_viaje", m6_mientras_otro_pedido_guarda)
    es_problema(calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5}), 409, generico=False)
    assert base_en_memoria["calificaciones"].count_documents({"clienteId": sub}) == 1


@pytest.mark.parametrize("estado", ["PENDING_ARRIVAL", "DRIVER_ARRIVED", "IN_PROGRESS", "CANCELLED"])
def test_viaje_no_completado_da_422(cliente_http, sub, m6_simulado, estado):
    viaje_id = nuevo_viaje(m6_simulado, sub, estado)
    cuerpo = es_problema(calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5}), 422, generico=False)
    assert cuerpo["type"] == "/errores/viaje-no-completado"


def test_viaje_inexistente_da_404(cliente_http, sub, m6_simulado):
    es_problema(calificar(cliente_http, sub, {"viajeId": str(uuid.uuid4()), "puntaje": 5}), 404)


def test_viaje_de_otro_cliente_da_404(cliente_http, sub, m6_simulado):
    viaje_ajeno = nuevo_viaje(m6_simulado, str(uuid.uuid4()))
    es_problema(calificar(cliente_http, sub, {"viajeId": viaje_ajeno, "puntaje": 5}), 404)


def test_m6_no_disponible_da_503_y_no_guarda_nada(cliente_http, sub, monkeypatch, base_en_memoria):
    def m6_caido(viaje_id, autorizacion):
        raise ErrorDominio(503, "/errores/dependencia-no-disponible", "M6 no está disponible", "M6 no respondió.")

    monkeypatch.setattr(m6, "obtener_viaje", m6_caido)
    cuerpo = es_problema(calificar(cliente_http, sub, {"viajeId": VIAJE, "puntaje": 5}), 503, generico=False)
    assert cuerpo["type"] == "/errores/dependencia-no-disponible"
    assert base_en_memoria["calificaciones"].count_documents({}) == 0


@pytest.mark.parametrize("cuerpo", [
    {"puntaje": 5},                                              # falta viajeId
    {"viajeId": VIAJE},                                          # falta puntaje
    {"viajeId": "abc", "puntaje": 5},                            # viajeId que no es UUID
    {"viajeId": VIAJE, "puntaje": 0},                            # fuera de rango
    {"viajeId": VIAJE, "puntaje": 6},
    {"viajeId": VIAJE, "puntaje": "5"},                          # el contrato pide un entero
    {"viajeId": VIAJE, "puntaje": 4.5},
    {"viajeId": VIAJE, "puntaje": True},                         # sin strict, valdría 1 estrella
    {"viajeId": VIAJE, "puntaje": 5, "comentario": None},        # null
    {"viajeId": VIAJE, "puntaje": 5, "comentario": "x" * 501},   # comentario largo
    {"viajeId": VIAJE, "puntaje": 5, "conductorId": CONDUCTOR},  # el conductor no lo elige el cliente
])
def test_cuerpo_invalido_da_400_sin_consultar_a_m6(cliente_http, sub, m6_simulado, cuerpo):
    es_problema(calificar(cliente_http, sub, cuerpo), 400)
    assert m6_simulado["llamadas"] == []


def test_sin_idempotency_key_da_400(cliente_http, sub, m6_simulado):
    r = cliente_http.post(ruta(sub), json={"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 5},
                          headers=auth(["CLIENTE"], sub))
    es_problema(r, 400)


def test_calificar_sin_perfil_da_404(cliente_http, m6_simulado):
    s = str(uuid.uuid4())
    es_problema(calificar(cliente_http, s, {"viajeId": nuevo_viaje(m6_simulado, s), "puntaje": 5}), 404)
    assert m6_simulado["llamadas"] == []


@pytest.mark.parametrize("roles,sub_token", [(["OPERADOR"], str(uuid.uuid4())), (["SERVICIO"], "m9-reservas")])
def test_solo_el_cliente_puede_calificar(cliente_http, sub, m6_simulado, roles, sub_token):
    viaje_id = nuevo_viaje(m6_simulado, sub)
    es_problema(calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 5}, roles, sub_token), 403)


def test_cliente_no_puede_calificar_en_otro_perfil(cliente_http, sub, m6_simulado):
    viaje_id = nuevo_viaje(m6_simulado, sub)
    r = calificar(cliente_http, sub, {"viajeId": viaje_id, "puntaje": 1}, sub_token=str(uuid.uuid4()))
    es_problema(r, 403)
    assert m6_simulado["llamadas"] == []


# ------------------------------------------------------------ Listar

def test_listar_mas_nuevas_primero(cliente_http, sub, m6_simulado, reloj):
    viajes = calificar_varios(cliente_http, m6_simulado, sub, 3)
    cuerpo = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()
    validar("PaginaCalificaciones", cuerpo)
    assert [c["viajeId"] for c in cuerpo["items"]] == list(reversed(viajes))


def test_listar_con_paginacion(cliente_http, sub, m6_simulado, reloj):
    viajes = calificar_varios(cliente_http, m6_simulado, sub, 5)
    r = cliente_http.get(ruta(sub), params={"page": 1, "size": 2}, headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    cuerpo = r.json()
    validar("PaginaCalificaciones", cuerpo)
    assert (cuerpo["page"], cuerpo["size"], cuerpo["totalElementos"], cuerpo["totalPaginas"]) == (1, 2, 5, 3)
    # Más nuevas primero: la página 0 tiene la 5.ª y la 4.ª; la página 1, la 3.ª y la 2.ª
    assert [c["viajeId"] for c in cuerpo["items"]] == [viajes[2], viajes[1]]


def test_listar_vacio(cliente_http, sub):
    cuerpo = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()
    validar("PaginaCalificaciones", cuerpo)
    assert cuerpo["items"] == [] and cuerpo["totalElementos"] == 0 and cuerpo["totalPaginas"] == 0


def test_listar_no_mezcla_clientes(cliente_http, sub, m6_simulado):
    otro = str(uuid.uuid4())
    crear_perfil(cliente_http, otro)
    calificar_varios(cliente_http, m6_simulado, otro, 1)
    assert cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()["items"] == []


@pytest.mark.parametrize("params", [{"page": -1}, {"size": 0}, {"size": 101}])
def test_listar_con_parametros_invalidos_da_400(cliente_http, sub, params):
    es_problema(cliente_http.get(ruta(sub), params=params, headers=auth(["CLIENTE"], sub)), 400)


def test_operador_lista_las_de_cualquier_cliente(cliente_http, sub, m6_simulado):
    calificar_varios(cliente_http, m6_simulado, sub, 2)
    r = cliente_http.get(ruta(sub), headers=auth(["OPERADOR"]))
    assert r.status_code == 200 and r.json()["totalElementos"] == 2


def test_servicio_no_puede_listar_calificaciones(cliente_http, sub):
    # SERVICIO solo se admite en obtenerEstadoCuenta
    es_problema(cliente_http.get(ruta(sub), headers=auth(["SERVICIO"], "m9-reservas")), 403)


def test_cliente_no_puede_listar_las_de_otro(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub), headers=auth(["CLIENTE"])), 403)


def test_listar_sin_perfil_da_404(cliente_http):
    s = str(uuid.uuid4())
    es_problema(cliente_http.get(ruta(s), headers=auth(["CLIENTE"], s)), 404)


# ------------------------------------------------------------ Consultar una

def test_obtener_calificacion(cliente_http, sub, m6_simulado):
    creada = calificar(cliente_http, sub, {"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 4}).json()
    r = cliente_http.get(ruta(sub, creada["calificacionId"]), headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    validar("Calificacion", r.json())
    assert r.json() == creada  # el GET devuelve exactamente lo que devolvió el POST


def test_operador_obtiene_una_calificacion(cliente_http, sub, m6_simulado):
    creada = calificar(cliente_http, sub, {"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 4}).json()
    assert cliente_http.get(ruta(sub, creada["calificacionId"]), headers=auth(["OPERADOR"])).status_code == 200


def test_calificacion_de_otro_cliente_da_404(cliente_http, sub, m6_simulado):
    otro = str(uuid.uuid4())
    crear_perfil(cliente_http, otro)
    ajena = calificar(cliente_http, otro, {"viajeId": nuevo_viaje(m6_simulado, otro), "puntaje": 2}).json()
    # Pedida por el perfil equivocado no existe, aunque quien pregunte sea un OPERADOR
    es_problema(cliente_http.get(ruta(sub, ajena["calificacionId"]), headers=auth(["OPERADOR"])), 404)


def test_cliente_no_puede_ver_una_de_otro(cliente_http, sub, m6_simulado):
    creada = calificar(cliente_http, sub, {"viajeId": nuevo_viaje(m6_simulado, sub), "puntaje": 4}).json()
    es_problema(cliente_http.get(ruta(sub, creada["calificacionId"]), headers=auth(["CLIENTE"])), 403)


def test_calificacion_inexistente_da_404(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, uuid.uuid4()), headers=auth(["CLIENTE"], sub)), 404)


def test_calificacion_id_que_no_es_uuid_da_400(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, "abc"), headers=auth(["CLIENTE"], sub)), 400)


# ------------------------------------------------------------ Solo códigos declarados en el contrato

@pytest.mark.parametrize("operacion,codigos", [
    ("listarCalificaciones", {200, 400, 401, 403, 404, 500, 503}),
    ("calificarConductor", {201, 400, 401, 403, 404, 409, 413, 415, 422, 500, 503}),
    ("obtenerCalificacion", {200, 400, 401, 403, 404, 500, 503}),
])
def test_codigos_usados_estan_en_el_contrato(operacion, codigos):
    assert codigos <= respuestas_declaradas(operacion)
