# Preparación de los tests: base en memoria (mongomock) y tokens firmados con una clave de prueba,
# así los tests no necesitan MongoDB ni Keycloak corriendo.
import sys
import time
import uuid
from pathlib import Path

import jwt
import mongomock
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database  # noqa: E402
import security  # noqa: E402
from main import app  # noqa: E402

_CLAVE_PRIVADA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_CLAVE_PUBLICA = _CLAVE_PRIVADA.public_key()


@pytest.fixture(autouse=True)
def base_en_memoria(monkeypatch):
    mongo = mongomock.MongoClient(tz_aware=True)
    db = mongo["test"]
    monkeypatch.setattr(database, "coleccion_clientes", lambda: db["clientes"])
    monkeypatch.setattr(database, "base_disponible", lambda: True)
    monkeypatch.setattr(security, "obtener_clave", lambda token: _CLAVE_PUBLICA)
    return db


@pytest.fixture
def cliente_http():
    # raise_server_exceptions=False: un error inesperado se ve como lo vería el usuario (500)
    return TestClient(app, raise_server_exceptions=False)


def token(roles, sub=None, vence_en=300):
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "realm_access": {"roles": list(roles)},
        "exp": int(time.time()) + vence_en,
    }
    return jwt.encode(payload, _CLAVE_PRIVADA, algorithm="RS256")


def auth(roles, sub=None, **extra):
    encabezados = {"Authorization": f"Bearer {token(roles, sub)}"}
    encabezados.update(extra)
    return encabezados
