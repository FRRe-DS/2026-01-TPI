# Tests de direcciones frecuentes (RF-2.2).
import uuid

import pytest

from conftest import auth, crear_perfil, es_problema
from contrato import respuestas_declaradas, validar

CASA = {"tipo": "FAVORITA", "alias": "Casa", "texto": "Av. Sarmiento 1234, Resistencia, Chaco",
        "coordenadas": {"latitud": -27.4512, "longitud": -58.9867}}
FACU = {"tipo": "RECIENTE", "texto": "French 414, Resistencia"}


def ruta(sub, direccion_id=None):
    base = f"/api/v1/clientes/{sub}/direcciones"
    return f"{base}/{direccion_id}" if direccion_id else base


def crear_dir(cliente_http, sub, cuerpo):
    return cliente_http.post(ruta(sub), json=cuerpo,
                             headers=auth(["CLIENTE"], sub, **{"Idempotency-Key": str(uuid.uuid4())}))


@pytest.fixture
def sub(cliente_http):
    """Un cliente con perfil creado."""
    s = str(uuid.uuid4())
    assert crear_perfil(cliente_http, s).status_code == 201
    return s


# ------------------------------------------------------------ Crear

def test_crear_direccion_completa(cliente_http, sub):
    r = crear_dir(cliente_http, sub, CASA)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    validar("Direccion", cuerpo)
    assert cuerpo["alias"] == "Casa" and cuerpo["coordenadas"]["latitud"] == -27.4512
    assert r.headers["Location"] == ruta(sub, cuerpo["direccionId"])


def test_crear_direccion_minima_sin_campos_opcionales(cliente_http, sub):
    cuerpo = crear_dir(cliente_http, sub, FACU).json()
    validar("Direccion", cuerpo)
    assert "alias" not in cuerpo and "coordenadas" not in cuerpo and "usadoEn" not in cuerpo


@pytest.mark.parametrize("cuerpo", [
    {"tipo": "FAVORITA"},                                         # falta texto
    {"tipo": "CASA", "texto": "x"},                               # tipo inválido
    {"tipo": "FAVORITA", "texto": ""},                            # texto vacío
    {"tipo": "FAVORITA", "texto": "x", "alias": "a" * 51},        # alias largo
    {"tipo": "FAVORITA", "texto": "x", "alias": None},            # null
    {"tipo": "FAVORITA", "texto": "x", "coordenadas": {"latitud": 91, "longitud": 0}},
    {"tipo": "FAVORITA", "texto": "x", "idM4": "abc"},            # sin datos internos de M4
])
def test_crear_direccion_invalida_da_400(cliente_http, sub, cuerpo):
    es_problema(crear_dir(cliente_http, sub, cuerpo), 400)


def test_crear_direccion_sin_perfil_da_404(cliente_http):
    s = str(uuid.uuid4())
    es_problema(crear_dir(cliente_http, s, CASA), 404)


def test_crear_direccion_sin_idempotency_key_da_400(cliente_http, sub):
    es_problema(cliente_http.post(ruta(sub), json=CASA, headers=auth(["CLIENTE"], sub)), 400)


def test_operador_no_puede_crear_direccion(cliente_http, sub):
    r = cliente_http.post(ruta(sub), json=CASA, headers=auth(["OPERADOR"], **{"Idempotency-Key": "k"}))
    es_problema(r, 403)


def test_cliente_no_puede_crear_en_otro_perfil(cliente_http, sub):
    r = cliente_http.post(ruta(sub), json=CASA, headers=auth(["CLIENTE"], **{"Idempotency-Key": "k"}))
    es_problema(r, 403)


# ------------------------------------------------------------ Listar

def test_listar_con_paginacion(cliente_http, sub):
    for i in range(5):
        crear_dir(cliente_http, sub, {"tipo": "FAVORITA", "texto": f"Calle {i}"})
    r = cliente_http.get(ruta(sub), params={"page": 1, "size": 2}, headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    cuerpo = r.json()
    validar("PaginaDirecciones", cuerpo)
    assert (cuerpo["page"], cuerpo["size"], cuerpo["totalElementos"], cuerpo["totalPaginas"]) == (1, 2, 5, 3)
    assert len(cuerpo["items"]) == 2


def test_listar_mas_nuevas_primero(cliente_http, sub):
    crear_dir(cliente_http, sub, {"tipo": "FAVORITA", "texto": "Primera"})
    crear_dir(cliente_http, sub, {"tipo": "FAVORITA", "texto": "Segunda"})
    items = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()["items"]
    assert [d["texto"] for d in items] == ["Segunda", "Primera"]


def test_listar_filtra_por_tipo(cliente_http, sub):
    crear_dir(cliente_http, sub, CASA)
    crear_dir(cliente_http, sub, FACU)
    items = cliente_http.get(ruta(sub), params={"tipo": "RECIENTE"}, headers=auth(["CLIENTE"], sub)).json()["items"]
    assert [d["tipo"] for d in items] == ["RECIENTE"]


def test_listar_vacio(cliente_http, sub):
    cuerpo = cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()
    validar("PaginaDirecciones", cuerpo)
    assert cuerpo["items"] == [] and cuerpo["totalElementos"] == 0 and cuerpo["totalPaginas"] == 0


def test_listar_no_mezcla_clientes(cliente_http, sub):
    otro = str(uuid.uuid4())
    crear_perfil(cliente_http, otro)
    crear_dir(cliente_http, otro, CASA)
    assert cliente_http.get(ruta(sub), headers=auth(["CLIENTE"], sub)).json()["items"] == []


@pytest.mark.parametrize("params", [{"page": -1}, {"size": 0}, {"size": 101}, {"tipo": "CASA"}])
def test_listar_con_parametros_invalidos_da_400(cliente_http, sub, params):
    es_problema(cliente_http.get(ruta(sub), params=params, headers=auth(["CLIENTE"], sub)), 400)


def test_operador_lista_direcciones_de_cualquiera(cliente_http, sub):
    crear_dir(cliente_http, sub, CASA)
    r = cliente_http.get(ruta(sub), headers=auth(["OPERADOR"]))
    assert r.status_code == 200 and r.json()["totalElementos"] == 1


def test_servicio_no_puede_listar_direcciones(cliente_http, sub):
    # Confirmado por M9: las direcciones no admiten SERVICIO
    es_problema(cliente_http.get(ruta(sub), headers=auth(["SERVICIO"], "m9-reservas")), 403)


def test_listar_sin_perfil_da_404(cliente_http):
    s = str(uuid.uuid4())
    es_problema(cliente_http.get(ruta(s), headers=auth(["CLIENTE"], s)), 404)


# ------------------------------------------------------------ Consultar, actualizar y eliminar una

def test_obtener_direccion(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    r = cliente_http.get(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200
    validar("Direccion", r.json())
    assert r.json() == creada


def test_direccion_de_otro_cliente_da_404_al_operador(cliente_http, sub):
    otro = str(uuid.uuid4())
    crear_perfil(cliente_http, otro)
    ajena = crear_dir(cliente_http, otro, CASA).json()
    # La dirección existe, pero no es de este cliente: para esta ruta no existe
    es_problema(cliente_http.get(ruta(sub, ajena["direccionId"]), headers=auth(["OPERADOR"])), 404)


def test_direccion_inexistente_da_404(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, uuid.uuid4()), headers=auth(["CLIENTE"], sub)), 404)


def test_direccion_id_que_no_es_uuid_da_400(cliente_http, sub):
    es_problema(cliente_http.get(ruta(sub, "123"), headers=auth(["CLIENTE"], sub)), 400)


def test_patch_cambia_solo_lo_enviado(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    r = cliente_http.patch(ruta(sub, creada["direccionId"]), json={"alias": "Depto"},
                           headers=auth(["CLIENTE"], sub))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    validar("Direccion", cuerpo)
    assert cuerpo["alias"] == "Depto"
    assert cuerpo["texto"] == creada["texto"] and cuerpo["creadoEn"] == creada["creadoEn"]


@pytest.mark.parametrize("cuerpo", [{}, {"texto": None}, {"tipo": "OTRA"}, {"usadoEn": "2026-10-21T10:00:00Z"}])
def test_patch_invalido_da_400(cliente_http, sub, cuerpo):
    creada = crear_dir(cliente_http, sub, CASA).json()
    es_problema(cliente_http.patch(ruta(sub, creada["direccionId"]), json=cuerpo,
                                   headers=auth(["CLIENTE"], sub)), 400)


def test_operador_no_puede_modificar_direccion(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    es_problema(cliente_http.patch(ruta(sub, creada["direccionId"]), json={"alias": "X"},
                                   headers=auth(["OPERADOR"])), 403)


def test_eliminar_direccion(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    r = cliente_http.delete(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"], sub))
    assert r.status_code == 204 and r.content == b""
    assert r.headers["X-Request-Id"]
    es_problema(cliente_http.get(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"], sub)), 404)


def test_eliminar_dos_veces_da_404(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    cliente_http.delete(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"], sub))
    es_problema(cliente_http.delete(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"], sub)), 404)


def test_cliente_no_puede_eliminar_direccion_ajena(cliente_http, sub):
    creada = crear_dir(cliente_http, sub, CASA).json()
    es_problema(cliente_http.delete(ruta(sub, creada["direccionId"]), headers=auth(["CLIENTE"])), 403)


def test_put_sobre_direccion_da_405(cliente_http, sub):
    r = cliente_http.put(ruta(sub, uuid.uuid4()), json=CASA, headers=auth(["CLIENTE"], sub))
    es_problema(r, 405)
    assert r.headers["Allow"] == "GET, PATCH, DELETE"


# ------------------------------------------------------------ Solo códigos declarados en el contrato

@pytest.mark.parametrize("operacion,codigos", [
    ("listarDirecciones", {200, 400, 401, 403, 404, 500, 503}),
    ("crearDireccion", {201, 400, 401, 403, 404, 413, 415, 500, 503}),
    ("obtenerDireccion", {200, 400, 401, 403, 404, 500, 503}),
    ("actualizarDireccion", {200, 400, 401, 403, 404, 413, 415, 500, 503}),
    ("eliminarDireccion", {204, 400, 401, 403, 404, 500, 503}),
])
def test_codigos_usados_estan_en_el_contrato(operacion, codigos):
    assert codigos <= respuestas_declaradas(operacion)
