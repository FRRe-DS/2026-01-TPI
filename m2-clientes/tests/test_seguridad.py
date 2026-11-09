# Tests de scopes, audiencia y disponibilidad de M1 (contrato acordado con el Grupo 17, FRRe-DS/2026-TPI#18).
# Las pruebas de cada recurso ya cubren roles y dueño; acá se prueba lo que es común a todas las operaciones.
import uuid

import pytest
from fastapi.routing import APIRoute
from jwt.exceptions import PyJWKClientConnectionError

import config
import security
from conftest import PERFIL, crear_perfil, es_problema, token
from contrato import _contrato
from main import app


def operaciones_del_contrato():
    """(operationId, método, ruta, roles, scope) de cada operación con token, leídos del contrato."""
    ops = []
    for ruta, metodos in _contrato()["paths"].items():
        for metodo, op in metodos.items():
            if not isinstance(op, dict) or "security" not in op or op["security"] == []:
                continue
            renglones = op["security"]
            assert len(renglones) == 1, f"{op['operationId']}: se espera un solo renglón de security"
            renglon = renglones[0]
            assert len(renglon["OAuth2Bearer"]) == 1, f"{op['operationId']}: se espera un solo scope"
            ops.append((op["operationId"], metodo.upper(), ruta, renglon["bearerAuth"], renglon["OAuth2Bearer"][0]))
    return ops


OPERACIONES = operaciones_del_contrato()
SCOPES = ("clientes:read", "clientes:write", "clientes.estado:read")


def encabezados(roles, sub, scope=None, aud=None):
    return {"Authorization": f"Bearer {token(roles, sub, scope=scope, aud=aud)}",
            "Idempotency-Key": str(uuid.uuid4())}


def pedir(cliente_http, metodo, ruta, sub, headers):
    url = ruta.replace("{clienteId}", sub)
    for parametro in ("{direccionId}", "{bloqueoId}", "{calificacionId}"):
        url = url.replace(parametro, str(uuid.uuid4()))
    cuerpo = {} if metodo in ("POST", "PUT", "PATCH") else None
    return cliente_http.request(metodo, url, json=cuerpo, headers=headers)


def rutas_de_la_api():
    """Las APIRoute de la app. Desde FastAPI 0.143, include_router las envuelve (ver AGENTS.md)."""
    rutas = []
    for ruta in app.routes:
        if isinstance(ruta, APIRoute):
            rutas.append(ruta)
        elif hasattr(ruta, "original_router"):
            rutas.extend(r for r in ruta.original_router.routes if isinstance(r, APIRoute))
    return rutas


def operaciones_implementadas():
    """operationId → scope que declara la ruta en requiere_roles(..., scope=...)."""
    declarados = {}
    for ruta in rutas_de_la_api():
        for dep in ruta.dependant.dependencies:
            if hasattr(dep.call, "scope"):
                declarados[ruta.operation_id] = dep.call.scope
    return declarados


@pytest.fixture
def con_scopes(monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_SCOPES", True)


# ------------------------------------------------------------ Cada operación declara el scope del contrato

def test_el_contrato_tiene_scopes_en_todas_las_operaciones_con_token():
    assert len(OPERACIONES) == 19
    assert {scope for *_, scope in OPERACIONES} == set(SCOPES)


@pytest.mark.parametrize("operacion,scope", [(o[0], o[4]) for o in OPERACIONES])
def test_cada_ruta_implementada_declara_el_scope_del_contrato(operacion, scope):
    declarados = operaciones_implementadas()
    if operacion not in declarados:
        pytest.skip(f"{operacion} todavía no está implementada (etapa 4)")
    assert declarados[operacion] == scope


def test_todas_las_rutas_con_token_declaran_scope():
    # Ninguna operación implementada puede quedar sin scope
    contrato = {o[0] for o in OPERACIONES}
    implementadas = operaciones_implementadas()
    con_token = [r.operation_id for r in rutas_de_la_api() if r.operation_id in contrato]
    assert con_token
    for operacion in con_token:
        assert operacion in implementadas, operacion


# ------------------------------------------------------------ Con EXIGIR_SCOPES activo

def _implementadas():
    implementadas = operaciones_implementadas()
    return [o for o in OPERACIONES if o[0] in implementadas]


@pytest.mark.parametrize("operacion,metodo,ruta,roles,scope", _implementadas(),
                         ids=[o[0] for o in _implementadas()])
def test_sin_el_scope_da_403(cliente_http, con_scopes, operacion, metodo, ruta, roles, scope):
    sub = str(uuid.uuid4())
    otros = " ".join(s for s in SCOPES if s != scope)  # todos menos el que hace falta
    r = pedir(cliente_http, metodo, ruta, sub, encabezados([roles[0]], sub, scope=otros))
    cuerpo = es_problema(r, 403)
    assert scope in cuerpo["detail"]


@pytest.mark.parametrize("operacion,metodo,ruta,roles,scope", _implementadas(),
                         ids=[o[0] for o in _implementadas()])
def test_con_el_scope_pasa_el_control(cliente_http, con_scopes, operacion, metodo, ruta, roles, scope):
    # Con el rol y el scope correctos no hay 403: lo que responda después (404, 400...) es otra cosa
    sub = str(uuid.uuid4())
    r = pedir(cliente_http, metodo, ruta, sub, encabezados([roles[0]], sub, scope=f"openid {scope}"))
    assert r.status_code not in (401, 403), r.text


def test_el_scope_no_reemplaza_al_rol(cliente_http, con_scopes):
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}/bloqueos",
                         headers=encabezados(["CLIENTE"], sub, scope=" ".join(SCOPES)))
    es_problema(r, 403)


def test_estado_de_cuenta_pide_su_propio_scope(cliente_http, con_scopes):
    # clientes:read no alcanza: obtenerEstadoCuenta pide clientes.estado:read, también a las personas
    sub = str(uuid.uuid4())
    cliente_http.post("/api/v1/clientes", json=PERFIL, headers=encabezados(["CLIENTE"], sub, scope="clientes:write"))
    ruta = f"/api/v1/clientes/{sub}/estado-cuenta"
    es_problema(cliente_http.get(ruta, headers=encabezados(["CLIENTE"], sub, scope="clientes:read clientes:write")), 403)
    r = cliente_http.get(ruta, headers=encabezados(["CLIENTE"], sub, scope="clientes.estado:read"))
    assert r.status_code == 200, r.text


def test_clientes_estado_read_no_da_acceso_a_nada_mas(cliente_http, con_scopes):
    # Es el scope de M5 y M9: con él no se ve el perfil ni las direcciones (RNF-19)
    sub = str(uuid.uuid4())
    h = encabezados(["OPERADOR"], str(uuid.uuid4()), scope="clientes.estado:read")
    es_problema(cliente_http.get(f"/api/v1/clientes/{sub}", headers=h), 403)
    es_problema(cliente_http.get(f"/api/v1/clientes/{sub}/direcciones", headers=h), 403)


def test_con_scopes_apagados_alcanza_el_rol(cliente_http):
    # Valor por defecto: los Keycloak locales todavía no emiten los scopes
    assert config.EXIGIR_SCOPES is False
    sub = str(uuid.uuid4())
    crear_perfil(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub))
    assert r.status_code == 200


# ------------------------------------------------------------ Audiencia

@pytest.fixture
def con_audiencia(monkeypatch):
    monkeypatch.setattr(config, "JWT_AUDIENCE", "m2-clientes")


@pytest.mark.parametrize("aud", ["m2-clientes", ["account", "m2-clientes"]])
def test_audiencia_correcta_pasa(cliente_http, con_audiencia, aud):
    sub = str(uuid.uuid4())
    cliente_http.post("/api/v1/clientes", json=PERFIL, headers=encabezados(["CLIENTE"], sub, aud="m2-clientes"))
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub, aud=aud))
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("aud", [None, "m6-viajes", ["account"]])
def test_audiencia_ausente_o_ajena_da_401(cliente_http, con_audiencia, aud):
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub, aud=aud))
    es_problema(r, 401)


def test_sin_audiencia_configurada_no_se_verifica(cliente_http):
    assert config.JWT_AUDIENCE == ""
    sub = str(uuid.uuid4())
    crear_perfil(cliente_http, sub)
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub, aud="otro-modulo"))
    assert r.status_code == 200


# ------------------------------------------------------------ M1 no disponible

def test_si_m1_no_responde_da_503_y_no_401(cliente_http, monkeypatch):
    def sin_m1(token):
        raise PyJWKClientConnectionError("no se pudo conectar")

    monkeypatch.setattr(security, "obtener_clave", sin_m1)
    sub = str(uuid.uuid4())
    r = cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub))
    cuerpo = es_problema(r, 503)
    assert r.headers["Retry-After"]
    assert "M1" in cuerpo["detail"]


def test_clave_desconocida_sigue_siendo_401(cliente_http, monkeypatch):
    # Si M1 responde pero el token no coincide con ninguna clave, el problema es el token
    def sin_clave(token):
        raise security.jwt.PyJWKClientError("no hay una clave con ese kid")

    monkeypatch.setattr(security, "obtener_clave", sin_clave)
    sub = str(uuid.uuid4())
    es_problema(cliente_http.get(f"/api/v1/clientes/{sub}", headers=encabezados(["CLIENTE"], sub)), 401)
