# Tests de estado de cuenta y bloqueos (RF-2.6).
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import auth, crear_perfil, es_problema
from contrato import respuestas_declaradas, validar

OPERADOR_SUB = str(uuid.uuid4())


def op(**extra):
    return auth(["OPERADOR"], OPERADOR_SUB, **extra)


def ruta(sub, bloqueo_id=None):
    base = f"/api/v1/clientes/{sub}/bloqueos"
    return f"{base}/{bloqueo_id}" if bloqueo_id else base


def ruta_estado(sub):
    return f"/api/v1/clientes/{sub}/estado-cuenta"


def bloquear(cliente_http, sub, cuerpo=None):
    return cliente_http.post(ruta(sub), json=cuerpo if cuerpo is not None else {"motivo": "Deuda pendiente"},
                             headers=op(**{"Idempotency-Key": str(uuid.uuid4())}))


def levantar(cliente_http, sub, bloqueo_id, motivo="Pagó la deuda"):
    return cliente_http.patch(ruta(sub, bloqueo_id), json={"motivo": motivo}, headers=op())


def en(minutos: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutos)).isoformat()


@pytest.fixture
def sub(cliente_http):
    """Un cliente con perfil creado."""
    s = str(uuid.uuid4())
    assert crear_perfil(cliente_http, s).status_code == 201
    return s


@pytest.fixture
def vencido(base_en_memoria, sub):
    """Un bloqueo cuyo `hasta` ya pasó, nunca levantado (se carga directo en la base)."""
    hace_un_rato = datetime.now(timezone.utc) - timedelta(hours=2)
    doc = {"_id": str(uuid.uuid4()), "clienteId": sub, "motivo": "Suspensión de un día",
           "desde": hace_un_rato - timedelta(days=1), "hasta": hace_un_rato,
           "creadoEn": hace_un_rato - timedelta(days=1), "creadoPor": OPERADOR_SUB}
    base_en_memoria["bloqueos"].insert_one(doc)
    return doc["_id"]


# ------------------------------------------------------------ Crear

def test_crear_bloqueo_sin_fin(cliente_http, sub):
    r = bloquear(cliente_http, sub)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    validar("Bloqueo", cuerpo)
    assert cuerpo["vigente"] is True and cuerpo["motivo"] == "Deuda pendiente"
    assert cuerpo["creadoPor"] == OPERADOR_SUB
    assert cuerpo["desde"] == cuerpo["creadoEn"]
    assert "hasta" not in cuerpo and "levantadoEn" not in cuerpo
    assert r.headers["Location"] == ruta(sub, cuerpo["bloqueoId"])


def test_crear_bloqueo_con_fin_lo_devuelve_en_utc_igual_que_el_get(cliente_http, sub):
    hasta = (datetime.now(timezone(timedelta(hours=-3))) + timedelta(days=7)).isoformat()  # hora de Argentina
    creado = bloquear(cliente_http, sub, {"motivo": "Suspensión", "hasta": hasta}).json()
    assert datetime.fromisoformat(creado["hasta"]) == datetime.fromisoformat(hasta).replace(
        microsecond=datetime.fromisoformat(hasta).microsecond // 1000 * 1000)
    assert creado["hasta"].endswith("Z")
    leido = cliente_http.get(ruta(sub, creado["bloqueoId"]), headers=op()).json()
    assert creado == leido


def test_fin_en_el_pasado_da_422(cliente_http, sub):
    cuerpo = es_problema(bloquear(cliente_http, sub, {"motivo": "x", "hasta": en(-1)}), 422, generico=False)
    assert cuerpo["type"] == "/errores/fin-de-bloqueo-pasado"


@pytest.mark.parametrize("cuerpo", [
    {},                                                    # falta motivo
    {"motivo": ""},                                        # motivo vacío
    {"motivo": "x" * 501},                                 # motivo largo
    {"motivo": "x", "hasta": None},                        # null
    {"motivo": "x", "hasta": "mañana"},                    # no es fecha
    {"motivo": "x", "hasta": "2030-01-01T10:00:00"},       # sin zona horaria
    {"motivo": "x", "vigente": False},                     # campo que no está en el contrato
])
def test_crear_bloqueo_invalido_da_400(cliente_http, sub, cuerpo):
    es_problema(bloquear(cliente_http, sub, cuerpo), 400)


def test_crear_bloqueo_sin_idempotency_key_da_400(cliente_http, sub):
    es_problema(cliente_http.post(ruta(sub), json={"motivo": "x"}, headers=op()), 400)


def test_bloquear_cliente_sin_perfil_da_404(cliente_http):
    es_problema(bloquear(cliente_http, str(uuid.uuid4())), 404)


# ------------------------------------------------------------ Consultar

def test_obtener_bloqueo(cliente_http, sub):
    creado = bloquear(cliente_http, sub).json()
    r = cliente_http.get(ruta(sub, creado["bloqueoId"]), headers=op())
    assert r.status_code == 200
    validar("Bloqueo", r.json())
    assert r.json() == creado


def test_bloqueo_de_otro_cliente_da_404(cliente_http, sub):
    otro = str(uuid.uuid4())
    crear_perfil(cliente_http, otro)
    bloqueo_id = bloquear(cliente_http, otro).json()["bloqueoId"]
    es_problema(cliente_http.get(ruta(sub, bloqueo_id), headers=op()), 404)
    es_problema(levantar(cliente_http, sub, bloqueo_id), 404)


def test_bloqueo_inexistente_da_404(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, uuid.uuid4()), headers=op()), 404)


def test_bloqueo_id_que_no_es_uuid_da_400(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, "abc"), headers=op()), 400)


# ------------------------------------------------------------ Levantar

def test_levantar_bloqueo(cliente_http, sub):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    r = levantar(cliente_http, sub, bloqueo_id)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    validar("Bloqueo", cuerpo)
    assert cuerpo["vigente"] is False
    assert cuerpo["levantadoPor"] == OPERADOR_SUB and cuerpo["motivoLevantamiento"] == "Pagó la deuda"
    assert cuerpo["levantadoEn"] >= cuerpo["creadoEn"]
    # No se borra: sigue en el historial
    assert cliente_http.get(ruta(sub, bloqueo_id), headers=op()).json() == cuerpo


def test_levantar_dos_veces_da_409(cliente_http, sub):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    levantar(cliente_http, sub, bloqueo_id)
    cuerpo = es_problema(levantar(cliente_http, sub, bloqueo_id, "otra vez"), 409, generico=False)
    assert cuerpo["type"] == "/errores/bloqueo-no-vigente"
    assert "levantado" in cuerpo["detail"]
    # El segundo intento no pisa los datos del primero
    guardado = cliente_http.get(ruta(sub, bloqueo_id), headers=op()).json()
    assert guardado["motivoLevantamiento"] == "Pagó la deuda"


def test_levantar_un_vencido_da_409(cliente_http, sub, vencido):
    cuerpo = es_problema(levantar(cliente_http, sub, vencido), 409, generico=False)
    assert "venció" in cuerpo["detail"]


@pytest.mark.parametrize("cuerpo", [{}, {"motivo": ""}, {"motivo": "x", "levantadoPor": "otro"}])
def test_levantar_con_cuerpo_invalido_da_400(cliente_http, sub, cuerpo):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    es_problema(cliente_http.patch(ruta(sub, bloqueo_id), json=cuerpo, headers=op()), 400)


def test_levantar_inexistente_da_404(cliente_http, sub):
    es_problema(levantar(cliente_http, sub, uuid.uuid4()), 404)


def test_borrar_bloqueo_no_existe_405(cliente_http, sub):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    r = cliente_http.delete(ruta(sub, bloqueo_id), headers=op())
    es_problema(r, 405)
    assert set(r.headers["Allow"].replace(" ", "").split(",")) == {"GET", "PATCH"}


# ------------------------------------------------------------ Listar

@pytest.fixture
def historial(cliente_http, sub, vencido):
    """Tres bloqueos: uno vigente, uno levantado y uno vencido."""
    vigente = bloquear(cliente_http, sub, {"motivo": "Vigente"}).json()["bloqueoId"]
    levantado = bloquear(cliente_http, sub, {"motivo": "Levantado"}).json()["bloqueoId"]
    levantar(cliente_http, sub, levantado)
    return {"vigente": vigente, "levantado": levantado, "vencido": vencido}


def test_listar_todos_mas_nuevos_primero(cliente_http, sub, historial):
    r = cliente_http.get(ruta(sub), headers=op())
    assert r.status_code == 200
    cuerpo = r.json()
    validar("PaginaBloqueos", cuerpo)
    assert cuerpo["totalElementos"] == 3
    fechas = [b["creadoEn"] for b in cuerpo["items"]]
    assert fechas == sorted(fechas, reverse=True)
    assert cuerpo["items"][-1]["bloqueoId"] == historial["vencido"]


def test_listar_solo_vigentes(cliente_http, sub, historial):
    cuerpo = cliente_http.get(ruta(sub), params={"vigente": "true"}, headers=op()).json()
    assert [b["bloqueoId"] for b in cuerpo["items"]] == [historial["vigente"]]
    assert cuerpo["items"][0]["vigente"] is True


def test_listar_no_vigentes_incluye_levantados_y_vencidos(cliente_http, sub, historial):
    cuerpo = cliente_http.get(ruta(sub), params={"vigente": "false"}, headers=op()).json()
    assert {b["bloqueoId"] for b in cuerpo["items"]} == {historial["levantado"], historial["vencido"]}
    assert all(b["vigente"] is False for b in cuerpo["items"])


def test_listar_paginado(cliente_http, sub, historial):
    cuerpo = cliente_http.get(ruta(sub), params={"page": 1, "size": 2}, headers=op()).json()
    assert len(cuerpo["items"]) == 1
    assert cuerpo["page"] == 1 and cuerpo["size"] == 2 and cuerpo["totalPaginas"] == 2


@pytest.mark.parametrize("params", [{"vigente": "talvez"}, {"page": -1}, {"size": 101}])
def test_listar_con_parametros_invalidos_da_400(cliente_http, sub, params):
    es_problema(cliente_http.get(ruta(sub), params=params, headers=op()), 400)


def test_listar_sin_perfil_da_404(cliente_http):
    es_problema(cliente_http.get(ruta(uuid.uuid4()), headers=op()), 404)


# ------------------------------------------------------------ Solo el OPERADOR maneja bloqueos

@pytest.mark.parametrize("roles", [["CLIENTE"], ["SERVICIO"], ["Operador"], []])
def test_bloqueos_solo_para_operador(cliente_http, sub, roles):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    h = auth(roles, sub, **{"Idempotency-Key": str(uuid.uuid4())})
    es_problema(cliente_http.get(ruta(sub), headers=h), 403)
    es_problema(cliente_http.post(ruta(sub), json={"motivo": "x"}, headers=h), 403)
    es_problema(cliente_http.get(ruta(sub, bloqueo_id), headers=h), 403)
    es_problema(cliente_http.patch(ruta(sub, bloqueo_id), json={"motivo": "x"}, headers=h), 403)


def test_bloqueos_sin_token_da_401(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub)), 401)
    es_problema(cliente_http.get(ruta_estado(sub)), 401)


# ------------------------------------------------------------ Estado de cuenta

def test_estado_sin_bloqueos_es_activo(cliente_http, sub):
    r = cliente_http.get(ruta_estado(sub), headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    cuerpo = r.json()
    validar("EstadoCuenta", cuerpo)
    assert cuerpo == {"clienteId": sub, "estado": "ACTIVO", "bloqueosVigentes": []}


def test_estado_con_bloqueo_vigente_es_bloqueado(cliente_http, sub):
    bloqueo = bloquear(cliente_http, sub).json()
    cuerpo = cliente_http.get(ruta_estado(sub), headers=auth(["CLIENTE"], sub)).json()
    validar("EstadoCuenta", cuerpo)
    assert cuerpo["estado"] == "BLOQUEADO"
    assert cuerpo["bloqueosVigentes"] == [bloqueo]


def test_estado_vuelve_a_activo_al_levantar(cliente_http, sub):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    levantar(cliente_http, sub, bloqueo_id)
    cuerpo = cliente_http.get(ruta_estado(sub), headers=op()).json()
    assert cuerpo["estado"] == "ACTIVO" and cuerpo["bloqueosVigentes"] == []


def test_estado_ignora_bloqueos_vencidos(cliente_http, sub, vencido):
    assert cliente_http.get(ruta_estado(sub), headers=op()).json()["estado"] == "ACTIVO"


def test_con_dos_bloqueos_sigue_bloqueado_hasta_levantar_ambos(cliente_http, sub):
    primero = bloquear(cliente_http, sub, {"motivo": "Deuda"}).json()["bloqueoId"]
    segundo = bloquear(cliente_http, sub, {"motivo": "Denuncia", "hasta": en(60)}).json()["bloqueoId"]
    levantar(cliente_http, sub, primero)
    cuerpo = cliente_http.get(ruta_estado(sub), headers=op()).json()
    assert cuerpo["estado"] == "BLOQUEADO"
    assert [b["bloqueoId"] for b in cuerpo["bloqueosVigentes"]] == [segundo]
    levantar(cliente_http, sub, segundo)
    assert cliente_http.get(ruta_estado(sub), headers=op()).json()["estado"] == "ACTIVO"


def test_servicio_consulta_el_estado_de_cualquier_cliente(cliente_http, sub):
    # M5 o M9: el sub del token nombra al módulo, no es un clienteId
    bloquear(cliente_http, sub)
    r = cliente_http.get(ruta_estado(sub), headers=auth(["SERVICIO"], "m9-reservas"))
    assert r.status_code == 200 and r.json()["estado"] == "BLOQUEADO"


def test_cliente_no_ve_el_estado_de_otro(cliente_http, sub):
    es_problema(cliente_http.get(ruta_estado(sub), headers=auth(["CLIENTE"], str(uuid.uuid4()))), 403)


def test_estado_con_rol_desconocido_da_403(cliente_http, sub):
    es_problema(cliente_http.get(ruta_estado(sub), headers=auth(["CONDUCTOR"], sub)), 403)


def test_estado_sin_perfil_da_404(cliente_http):
    es_problema(cliente_http.get(ruta_estado(uuid.uuid4()), headers=auth(["SERVICIO"], "m5-solicitud")), 404)


# ------------------------------------------------------------ El perfil muestra el estado real

def test_perfil_muestra_bloqueado(cliente_http, sub):
    bloqueo_id = bloquear(cliente_http, sub).json()["bloqueoId"]
    assert cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub)).json()["estado"] == "BLOQUEADO"
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json={"nombre": "Ana María"}, headers=auth(["CLIENTE"], sub))
    assert r.json()["estado"] == "BLOQUEADO"
    levantar(cliente_http, sub, bloqueo_id)
    assert cliente_http.get(f"/api/v1/clientes/{sub}", headers=op()).json()["estado"] == "ACTIVO"


# ------------------------------------------------------------ Solo códigos declarados en el contrato

@pytest.mark.parametrize("operacion,codigos", [
    ("obtenerEstadoCuenta", {200, 400, 401, 403, 404, 500, 503}),
    ("listarBloqueos", {200, 400, 401, 403, 404, 500, 503}),
    ("crearBloqueo", {201, 400, 401, 403, 404, 413, 415, 422, 500, 503}),
    ("obtenerBloqueo", {200, 400, 401, 403, 404, 500, 503}),
    ("levantarBloqueo", {200, 400, 401, 403, 404, 409, 413, 415, 500, 503}),
])
def test_codigos_usados_estan_en_el_contrato(operacion, codigos):
    assert codigos <= respuestas_declaradas(operacion)
