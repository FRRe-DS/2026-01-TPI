# Tests de la etapa 1: salud, perfil del cliente y reglas comunes del contrato.
import uuid

import pytest

from conftest import auth, token
from contrato import respuestas_declaradas, validar

NUEVO = {"nombre": "Ana", "apellido": "Gómez", "telefono": "+5493624000000"}


def crear(cliente_http, sub, cuerpo=None, **extra):
    return cliente_http.post(
        "/api/v1/clientes",
        json=cuerpo if cuerpo is not None else NUEVO,
        headers=auth(["CLIENTE"], sub, **{"Idempotency-Key": str(uuid.uuid4())}, **extra),
    )


def es_problema(r, status, generico=True):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    cuerpo = r.json()
    validar("Problema", cuerpo)
    if generico:
        validar("ProblemaGenerico", cuerpo)
    assert r.headers.get("X-Request-Id")
    return cuerpo


# ------------------------------------------------------------ Salud

def test_health_sin_token(cliente_http):
    r = cliente_http.get("/health")
    assert r.status_code == 200
    validar("Salud", r.json())
    assert r.headers["X-Request-Id"]


def test_health_503_si_la_base_no_responde(cliente_http, monkeypatch):
    import database
    monkeypatch.setattr(database, "base_disponible", lambda: False)
    r = cliente_http.get("/health")
    cuerpo = es_problema(r, 503)
    assert cuerpo["title"] == "Servicio no disponible"
    assert r.headers["Retry-After"]


# ------------------------------------------------------------ Crear

def test_crear_perfil(cliente_http):
    sub = str(uuid.uuid4())
    r = crear(cliente_http, sub)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    validar("Cliente", cuerpo)
    assert cuerpo["clienteId"] == sub
    assert cuerpo["estado"] == "ACTIVO"
    assert r.headers["Location"] == f"/api/v1/clientes/{sub}"
    assert "fechaNacimiento" not in cuerpo


def test_crear_con_fecha_de_nacimiento(cliente_http):
    r = crear(cliente_http, str(uuid.uuid4()), {**NUEVO, "fechaNacimiento": "2000-05-17"})
    assert r.status_code == 201
    assert r.json()["fechaNacimiento"] == "2000-05-17"


def test_crear_dos_veces_da_409(cliente_http):
    sub = str(uuid.uuid4())
    assert crear(cliente_http, sub).status_code == 201
    cuerpo = es_problema(crear(cliente_http, sub), 409, generico=False)
    assert cuerpo["type"] == "/errores/cliente-existente"


def test_crear_sin_idempotency_key_da_400(cliente_http):
    r = cliente_http.post("/api/v1/clientes", json=NUEVO, headers=auth(["CLIENTE"]))
    es_problema(r, 400)


@pytest.mark.parametrize("cuerpo", [
    {**NUEVO, "telefono": "3624000000"},           # sin +, no es E.164
    {**NUEVO, "nombre": ""},                       # vacío
    {**NUEVO, "email": "ana@gmail.com"},           # campo que el contrato no tiene
    {"nombre": "Ana", "apellido": "Gómez"},        # falta el teléfono
    {**NUEVO, "fechaNacimiento": None},            # null
])
def test_crear_con_datos_invalidos_da_400(cliente_http, cuerpo):
    es_problema(crear(cliente_http, str(uuid.uuid4()), cuerpo), 400)


def test_crear_con_rol_operador_da_403(cliente_http):
    r = cliente_http.post("/api/v1/clientes", json=NUEVO,
                          headers=auth(["OPERADOR"], **{"Idempotency-Key": "k1"}))
    assert es_problema(r, 403)["title"] == "Sin permiso"


# ------------------------------------------------------------ Consultar

def test_cliente_consulta_su_perfil(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    validar("Cliente", r.json())


def test_cliente_no_puede_ver_otro_perfil(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"]))
    es_problema(r, 403)


def test_operador_ve_cualquier_perfil(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["OPERADOR"]))
    assert r.status_code == 200


def test_servicio_no_puede_ver_perfil(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["SERVICIO"], "m9-reservas"))
    es_problema(r, 403)


def test_perfil_inexistente_da_404(cliente_http):
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub))
    assert es_problema(r, 404)["title"] == "No encontrado"


def test_id_que_no_es_uuid_da_400(cliente_http):
    r = cliente_http.get("/api/v1/clientes/123", headers=auth(["OPERADOR"]))
    es_problema(r, 400)


# ------------------------------------------------------------ Actualizar

def test_patch_cambia_solo_lo_enviado(cliente_http):
    sub = str(uuid.uuid4())
    creado = crear(cliente_http, sub).json()
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json={"telefono": "+5493624111111"},
                           headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    validar("Cliente", cuerpo)
    assert cuerpo["telefono"] == "+5493624111111"
    assert cuerpo["nombre"] == creado["nombre"]
    assert cuerpo["actualizadoEn"] >= creado["actualizadoEn"]


@pytest.mark.parametrize("cuerpo", [{}, {"nombre": None}, {"email": "x@y.com"}])
def test_patch_invalido_da_400(cliente_http, cuerpo):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json=cuerpo, headers=auth(["CLIENTE"], sub))
    es_problema(r, 400)


def test_patch_de_otro_cliente_da_403(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json={"nombre": "X"}, headers=auth(["CLIENTE"]))
    es_problema(r, 403)


def test_operador_no_puede_hacer_patch(cliente_http):
    sub = str(uuid.uuid4())
    crear(cliente_http, sub)
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json={"nombre": "X"},
                           headers=auth(["OPERADOR", "CLIENTE"]))
    es_problema(r, 403)


def test_patch_sin_perfil_da_404(cliente_http):
    sub = str(uuid.uuid4())
    r = cliente_http.patch(f"/api/v1/clientes/{sub}", json={"nombre": "X"}, headers=auth(["CLIENTE"], sub))
    es_problema(r, 404)


# ------------------------------------------------------------ Autenticación

def test_sin_token_da_401(cliente_http):
    r = cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}")
    assert es_problema(r, 401)["title"] == "No autenticado"


def test_token_vencido_da_401(cliente_http):
    t = token(["CLIENTE"], vence_en=-10)
    r = cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}", headers={"Authorization": f"Bearer {t}"})
    es_problema(r, 401)


def test_token_falso_da_401(cliente_http):
    r = cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}", headers={"Authorization": "Bearer abc.def.ghi"})
    es_problema(r, 401)


def test_roles_con_otras_mayusculas_no_valen(cliente_http):
    r = cliente_http.post("/api/v1/clientes", json=NUEVO,
                          headers=auth(["Cliente"], **{"Idempotency-Key": "k"}))
    es_problema(r, 403)


# ------------------------------------------------------------ Reglas comunes

def test_x_request_id_se_devuelve(cliente_http):
    r = cliente_http.get("/health", headers={"X-Request-Id": "abc-123"})
    assert r.headers["X-Request-Id"] == "abc-123"


def test_x_request_id_invalido_se_reemplaza_sin_400(cliente_http):
    r = cliente_http.get("/health", headers={"X-Request-Id": "no valido!"})
    assert r.status_code == 200
    assert r.headers["X-Request-Id"] != "no valido!"


def test_metodo_no_permitido_da_405_con_allow(cliente_http):
    r = cliente_http.delete(f"/api/v1/clientes/{uuid.uuid4()}", headers=auth(["CLIENTE"]))
    es_problema(r, 405)
    assert "PATCH" in r.headers["Allow"] and "GET" in r.headers["Allow"]


def test_ruta_inexistente_da_404(cliente_http):
    es_problema(cliente_http.get("/no-existe"), 404)


def test_cuerpo_que_no_es_json_da_415(cliente_http):
    r = cliente_http.post("/api/v1/clientes", content="nombre=Ana",
                          headers=auth(["CLIENTE"], **{"Content-Type": "text/plain", "Idempotency-Key": "k"}))
    es_problema(r, 415)


def test_cuerpo_de_mas_de_1_mib_da_413(cliente_http):
    grande = '{"nombre": "' + "a" * (1024 * 1024) + '"}'
    r = cliente_http.post("/api/v1/clientes", content=grande,
                          headers=auth(["CLIENTE"], **{"Content-Type": "application/json", "Idempotency-Key": "k"}))
    es_problema(r, 413)


def test_base_caida_da_503(cliente_http, monkeypatch):
    import database
    from pymongo.errors import ServerSelectionTimeoutError

    class Caida:
        def find_one(self, *a, **k):
            raise ServerSelectionTimeoutError("sin base")

    monkeypatch.setattr(database, "coleccion_clientes", lambda: Caida())
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub))
    es_problema(r, 503)
    assert r.headers["Retry-After"]


def test_error_inesperado_da_500_sin_detalles(cliente_http, monkeypatch):
    import database

    class Rota:
        def find_one(self, *a, **k):
            raise RuntimeError("detalle interno que no se tiene que ver")

    monkeypatch.setattr(database, "coleccion_clientes", lambda: Rota())
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub, **{"X-Request-Id": "req-500"}))
    cuerpo = es_problema(r, 500)
    assert "interno que no" not in r.text
    assert r.headers["X-Request-Id"] == "req-500"
    assert cuerpo["title"] == "Error interno"


# ------------------------------------------------------------ Solo códigos declarados en el contrato

@pytest.mark.parametrize("operacion,codigos", [
    ("crearCliente", {201, 400, 401, 403, 409, 413, 415, 500, 503}),
    ("obtenerCliente", {200, 400, 401, 403, 404, 500, 503}),
    ("actualizarCliente", {200, 400, 401, 403, 404, 413, 415, 500, 503}),
    ("verificarSalud", {200, 500, 503}),
])
def test_codigos_usados_estan_en_el_contrato(operacion, codigos):
    assert codigos <= respuestas_declaradas(operacion)
