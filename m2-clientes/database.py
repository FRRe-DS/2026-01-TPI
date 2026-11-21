# Conexión a MongoDB.
#
# Colecciones:
# - clientes: un documento por perfil. El _id es el clienteId (el "sub" del token del cliente).
#   Las preferencias se guardan dentro del perfil, en el campo "preferencias" (relación 1 a 1).
# - direcciones: un documento por dirección frecuente, con el clienteId de su dueño.
#   Van aparte porque se listan paginadas y se editan de a una.
# - bloqueos: un documento por bloqueo administrativo, con el clienteId del bloqueado.
#   Nunca se borran: levantar uno agrega levantadoEn, levantadoPor y motivoLevantamiento.
#   "vigente" no se guarda: se calcula al leer (no levantado y sin pasar su "hasta").
# - calificaciones: una por cliente y viaje, con el conductorId que informó M6 (nunca el del cuerpo).
#   El índice único (clienteId, viajeId) es el que impide calificar dos veces el mismo viaje.
import logging

from pymongo import ASCENDING, DESCENDING, MongoClient

import config

log = logging.getLogger("m2.database")

cliente_mongo = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=config.MONGO_TIMEOUT_MS, tz_aware=True)
db = cliente_mongo[config.MONGO_DB]


def coleccion_clientes():
    return db["clientes"]


def coleccion_direcciones():
    return db["direcciones"]


def coleccion_bloqueos():
    return db["bloqueos"]


def coleccion_calificaciones():
    return db["calificaciones"]


def asegurar_indices():
    """Crea los índices que usan las consultas. Se llama al arrancar la API; si Mongo no está, sigue igual."""
    try:
        # Listado de direcciones de un cliente, más nuevas primero
        coleccion_direcciones().create_index([("clienteId", ASCENDING), ("creadoEn", DESCENDING)])
        # Bloqueos de un cliente, más nuevos primero (listado y cálculo del estado)
        coleccion_bloqueos().create_index([("clienteId", ASCENDING), ("creadoEn", DESCENDING)])
        # Una calificación por cliente y viaje (RF-2.5). Lo controla la base y no un "if" en el código:
        # si llegan dos pedidos a la vez, los dos pasarían el if; el índice deja guardar solo uno (RNF-08)
        coleccion_calificaciones().create_index([("clienteId", ASCENDING), ("viajeId", ASCENDING)], unique=True)
        # Listado de calificaciones de un cliente, más nuevas primero
        coleccion_calificaciones().create_index([("clienteId", ASCENDING), ("creadoEn", DESCENDING)])
    except Exception as exc:  # la API arranca igual; /health va a avisar que la base no responde
        log.warning("No se pudieron crear los índices de MongoDB: %s", exc)


def base_disponible() -> bool:
    """Devuelve True si MongoDB responde (lo usa /health)."""
    try:
        cliente_mongo.admin.command("ping")
        return True
    except Exception:
        return False
