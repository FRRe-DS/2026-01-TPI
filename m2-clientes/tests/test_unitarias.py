# Pruebas unitarias (RNF-07): funciones sueltas, sin pasar por la API ni por HTTP.
# Cubren la lógica propia que las pruebas de API no llegan a ejercitar del todo:
# lectura de roles del token, regla de dueño, paginación, fechas, X-Request-Id y reglas de los modelos.
import time
import uuid
from datetime import timezone

import jwt
import mongomock
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

import security
from conftest import token
from middleware import _FORMATO_REQUEST_ID
from models import ClienteCambios, ClienteNuevo, Coordenadas, DireccionNueva, Preferencias
from rutas.comunes import ahora, paginar
from security import CLIENTE, OPERADOR, SERVICIO, Usuario, requiere_roles, usuario_actual, verificar_dueno


def credencial(t: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=t)


# ------------------------------------------------------------ Roles del token

def test_roles_de_keycloak_en_realm_access():
    assert security._roles_del_token({"realm_access": {"roles": ["CLIENTE", "offline_access"]}}) == {"CLIENTE", "offline_access"}


def test_roles_en_la_raiz_del_token():
    # Por si el formato que se acuerde para M1 (issue #9) pone los roles en "roles"
    assert security._roles_del_token({"roles": ["SERVICIO"]}) == {"SERVICIO"}


def test_roles_en_los_dos_lugares_se_juntan():
    payload = {"realm_access": {"roles": ["CLIENTE"]}, "roles": ["OPERADOR"]}
    assert security._roles_del_token(payload) == {"CLIENTE", "OPERADOR"}


@pytest.mark.parametrize("payload", [{}, {"realm_access": {}}, {"realm_access": {"roles": None}}, {"roles": None}])
def test_token_sin_roles_no_falla(payload):
    assert security._roles_del_token(payload) == set()


# ------------------------------------------------------------ Validación del token

def test_token_valido_devuelve_sub_y_roles():
    sub = str(uuid.uuid4())
    usuario = usuario_actual(credencial(token(["CLIENTE"], sub)))
    assert usuario.sub == sub and usuario.roles == {"CLIENTE"}


def test_token_con_roles_en_la_raiz(monkeypatch):
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(security, "obtener_clave", lambda _t: privada.public_key())
    t = jwt.encode({"sub": "m9-reservas", "roles": ["SERVICIO"], "exp": int(time.time()) + 60}, privada, algorithm="RS256")
    assert usuario_actual(credencial(t)) == Usuario(sub="m9-reservas", roles={"SERVICIO"})


def test_token_firmado_con_otra_clave_da_401():
    otra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    t = jwt.encode({"sub": "x", "exp": int(time.time()) + 60}, otra, algorithm="RS256")
    with pytest.raises(HTTPException) as e:
        usuario_actual(credencial(t))
    assert e.value.status_code == 401


def test_token_sin_sub_da_401(monkeypatch):
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(security, "obtener_clave", lambda _t: privada.public_key())
    t = jwt.encode({"exp": int(time.time()) + 60}, privada, algorithm="RS256")
    with pytest.raises(HTTPException) as e:
        usuario_actual(credencial(t))
    assert e.value.status_code == 401


def test_token_hs256_hoy_no_se_acepta():
    # M9 firma con HS256 mientras M1 sea simulado (issue #9). Hoy solo se acepta RS256:
    # esta prueba se cambia cuando se agregue ese soporte en la etapa 3.
    t = jwt.encode({"sub": "m9-reservas", "roles": ["SERVICIO"], "exp": int(time.time()) + 60}, "clave-compartida", algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        usuario_actual(credencial(t))
    assert e.value.status_code == 401


def test_sin_credenciales_da_401():
    with pytest.raises(HTTPException) as e:
        usuario_actual(None)
    assert e.value.status_code == 401


# ------------------------------------------------------------ Roles por operación y regla de dueño

def test_requiere_roles_se_queda_solo_con_los_admitidos():
    verificar = requiere_roles(CLIENTE, OPERADOR)
    assert verificar(Usuario(sub="a", roles={CLIENTE, SERVICIO})).roles == {CLIENTE}


def test_requiere_roles_sin_ninguno_admitido_da_403():
    with pytest.raises(HTTPException) as e:
        requiere_roles(OPERADOR)(Usuario(sub="a", roles={CLIENTE}))
    assert e.value.status_code == 403


def test_cliente_dueno_pasa():
    verificar_dueno(Usuario(sub="abc", roles={CLIENTE}), "abc")


def test_cliente_no_dueno_da_403():
    with pytest.raises(HTTPException) as e:
        verificar_dueno(Usuario(sub="abc", roles={CLIENTE}), "otro")
    assert e.value.status_code == 403


def test_operador_puede_ver_cualquiera_si_la_operacion_lo_admite():
    usuario = requiere_roles(CLIENTE, OPERADOR)(Usuario(sub="abc", roles={CLIENTE, OPERADOR}))
    verificar_dueno(usuario, "otro")


def test_operador_no_saltea_la_regla_si_la_operacion_es_solo_de_cliente():
    # Alguien con CLIENTE y OPERADOR, en una operación solo de CLIENTE, se trata como cliente
    usuario = requiere_roles(CLIENTE)(Usuario(sub="abc", roles={CLIENTE, OPERADOR}))
    with pytest.raises(HTTPException) as e:
        verificar_dueno(usuario, "otro")
    assert e.value.status_code == 403


# ------------------------------------------------------------ Paginación

@pytest.fixture
def coleccion():
    col = mongomock.MongoClient()["u"]["c"]
    col.insert_many([{"_id": i, "n": i} for i in range(5)])
    return col


@pytest.mark.parametrize("page,size,esperado,total_paginas", [
    (0, 2, [0, 1], 3),
    (2, 2, [4], 3),
    (3, 2, [], 3),       # página más allá del final: vacía, no error
    (0, 100, [0, 1, 2, 3, 4], 1),
    (0, 5, [0, 1, 2, 3, 4], 1),
])
def test_paginar(coleccion, page, size, esperado, total_paginas):
    docs, datos = paginar(coleccion, {}, [("n", 1)], page, size)
    assert [d["n"] for d in docs] == esperado
    assert datos == {"page": page, "size": size, "totalElementos": 5, "totalPaginas": total_paginas}


def test_paginar_sin_resultados():
    docs, datos = paginar(mongomock.MongoClient()["u"]["vacia"], {}, [("n", 1)], 0, 20)
    assert docs == [] and datos["totalElementos"] == 0 and datos["totalPaginas"] == 0


# ------------------------------------------------------------ Fechas

def test_ahora_es_utc_y_con_milisegundos():
    # MongoDB guarda milisegundos: si no se recorta, el POST y el GET devuelven fechas distintas
    momento = ahora()
    assert momento.tzinfo == timezone.utc
    assert momento.microsecond % 1000 == 0


# ------------------------------------------------------------ X-Request-Id

@pytest.mark.parametrize("valor,valido", [
    ("abc-123", True), ("a.b_c-D", True), ("x" * 128, True),
    ("", False), ("x" * 129, False), ("con espacio", False), ("ñandú", False), ("a/b", False),
])
def test_formato_x_request_id(valor, valido):
    assert bool(_FORMATO_REQUEST_ID.match(valor)) is valido


# ------------------------------------------------------------ Reglas de los modelos

@pytest.mark.parametrize("telefono,valido", [
    ("+5493624000000", True), ("+1234567", True),
    ("5493624000000", False), ("+0123456789", False), ("+54 362 400", False), ("+123456", False),
])
def test_telefono_en_formato_e164(telefono, valido):
    datos = {"nombre": "Ana", "apellido": "Gómez", "telefono": telefono}
    if valido:
        ClienteNuevo(**datos)
    else:
        with pytest.raises(ValidationError):
            ClienteNuevo(**datos)


def test_cambios_vacios_o_con_null_se_rechazan():
    with pytest.raises(ValidationError):
        ClienteCambios()
    with pytest.raises(ValidationError):
        ClienteCambios(nombre=None)
    assert ClienteCambios(nombre="Ana").model_dump(exclude_unset=True) == {"nombre": "Ana"}


@pytest.mark.parametrize("lat,lon,valido", [(-27.45, -58.98, True), (90, 180, True), (91, 0, False), (0, -181, False)])
def test_coordenadas_dentro_de_rango(lat, lon, valido):
    if valido:
        Coordenadas(latitud=lat, longitud=lon)
    else:
        with pytest.raises(ValidationError):
            Coordenadas(latitud=lat, longitud=lon)


def test_direccion_no_acepta_campos_fuera_del_contrato():
    with pytest.raises(ValidationError):
        DireccionNueva(tipo="FAVORITA", texto="Casa", idM4="123")


def test_preferencias_por_defecto_son_listas_vacias():
    assert Preferencias.por_defecto().model_dump(exclude_none=True) == {"tiposVehiculo": [], "canales": [], "accesibilidad": []}


def test_preferencias_sin_repetidos():
    with pytest.raises(ValidationError):
        Preferencias(tiposVehiculo=["AUTO", "AUTO"], canales=[], accesibilidad=[])
