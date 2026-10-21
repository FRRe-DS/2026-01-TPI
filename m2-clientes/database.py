# Conexión a MongoDB.
# El _id de cada perfil es el clienteId, que es el "sub" del token del cliente.
from pymongo import MongoClient

import config

cliente_mongo = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=config.MONGO_TIMEOUT_MS, tz_aware=True)
db = cliente_mongo[config.MONGO_DB]


def coleccion_clientes():
    return db["clientes"]


def base_disponible() -> bool:
    """Devuelve True si MongoDB responde (lo usa /health)."""
    try:
        cliente_mongo.admin.command("ping")
        return True
    except Exception:
        return False
