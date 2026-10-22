# Tests de preferencias del cliente (RF-2.3).
import uuid

import pytest

from conftest import auth, crear_perfil, es_problema
from contrato import respuestas_declaradas, validar

COMPLETAS = {
    "tiposVehiculo": ["AUTO"],
    "canales": ["EMAIL", "PUSH"],
    "accesibilidad": ["SILLA_DE_RUEDAS"],
    "observacionesAccesibilidad": "Necesito baúl grande para la silla.",
}


def ruta(sub):
    return f"/api/v1/clientes/{sub}/preferencias"


@pytest.fixture
def sub(cliente_http):
    s = str(uuid.uuid4())
    assert crear_perfil(cliente_http, s).status_code == 201
    return s


def test_sin_guardar_devuelve_valores_por_defecto(cliente_http, sub):
    r = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    validar("Preferencias", r.json())
    assert r.json() == {"tiposVehiculo": [], "canales": [], "accesibilidad": []}


def test_guardar_y_consultar(cliente_http, sub):
    r = cliente_http.put(ruta(sub), json=COMPLETAS, headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200, r.text
    validar("Preferencias", r.json())
    assert r.json() == COMPLETAS
    assert cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json() == COMPLETAS


def test_put_reemplaza_todo(cliente_http, sub):
    cliente_http.put(ruta(sub), json=COMPLETAS, headers=auth(["CLIENTE"], sub))
    nuevas = {"tiposVehiculo": [], "canales": ["SMS"], "accesibilidad": []}
    cliente_http.put(ruta(sub), json=nuevas, headers=auth(["CLIENTE"], sub))
    # Las observaciones anteriores no quedan: el PUT reemplaza, no mezcla
    assert cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json() == nuevas


def test_put_repetido_deja_lo_mismo(cliente_http, sub):
    for _ in range(2):
        r = cliente_http.put(ruta(sub), json=COMPLETAS, headers=auth(["CLIENTE"], sub))
        assert r.status_code == 200
    assert cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json() == COMPLETAS


def test_guardar_preferencias_no_cambia_el_perfil(cliente_http, sub):
    antes = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub)).json()
    cliente_http.put(ruta(sub), json=COMPLETAS, headers=auth(["CLIENTE"], sub))
    despues = cliente_http.get(f"/api/v1/clientes/{sub}", headers=auth(["CLIENTE"], sub)).json()
    validar("Cliente", despues)
    assert despues == antes


@pytest.mark.parametrize("cuerpo", [
    {"tiposVehiculo": ["AUTO"], "canales": []},                                    # falta accesibilidad
    {"tiposVehiculo": ["CAMIONETA"], "canales": [], "accesibilidad": []},          # valor fuera del enum
    {"tiposVehiculo": ["AUTO", "AUTO"], "canales": [], "accesibilidad": []},       # repetidos
    {"tiposVehiculo": [], "canales": ["WHATSAPP"], "accesibilidad": []},           # canal que no existe
    {"tiposVehiculo": [], "canales": [], "accesibilidad": [], "observacionesAccesibilidad": "x" * 256},
    {"tiposVehiculo": [], "canales": [], "accesibilidad": [], "observacionesAccesibilidad": None},
    {"tiposVehiculo": [], "canales": [], "accesibilidad": [], "confort": {"musica": "Rock"}},
])
def test_put_invalido_da_400(cliente_http, sub, cuerpo):
    es_problema(cliente_http.put(ruta(sub), json=cuerpo, headers=auth(["CLIENTE"], sub)), 400)


def test_operador_consulta_pero_no_guarda(cliente_http, sub):
    assert cliente_http.get(ruta(sub), headers=auth(["OPERADOR"])).status_code == 200
    es_problema(cliente_http.put(ruta(sub), json=COMPLETAS, headers=auth(["OPERADOR"])), 403)


def test_servicio_no_puede_consultar_preferencias(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub), headers=auth(["SERVICIO"], "m5-despacho")), 403)


def test_cliente_no_ve_preferencias_ajenas(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub), headers=auth(["CLIENTE"])), 403)


def test_sin_perfil_da_404(cliente_http):
    s = str(uuid.uuid4())
    es_problema(cliente_http.get(ruta(s), headers=auth(["CLIENTE"], s)), 404)
    es_problema(cliente_http.put(ruta(s), json=COMPLETAS, headers=auth(["CLIENTE"], s)), 404)


def test_post_sobre_preferencias_da_405(cliente_http, sub):
    r = cliente_http.post(ruta(sub), json=COMPLETAS, headers=auth(["CLIENTE"], sub))
    es_problema(r, 405)
    assert r.headers["Allow"] == "GET, PUT"


@pytest.mark.parametrize("operacion,codigos", [
    ("obtenerPreferencias", {200, 400, 401, 403, 404, 500, 503}),
    ("guardarPreferencias", {200, 400, 401, 403, 404, 413, 415, 500, 503}),
])
def test_codigos_usados_estan_en_el_contrato(operacion, codigos):
    assert codigos <= respuestas_declaradas(operacion)
