# Bloqueos administrativos (RF-2.6): los registra y los levanta un OPERADOR.
# Un cliente con al menos un bloqueo vigente queda BLOQUEADO y no puede pedir ni reservar viajes
# (M5 y M9 lo consultan en el estado de cuenta).
#
# Reglas:
# - Un bloqueo está vigente si no fue levantado y no pasó su "hasta". No se guarda: se calcula al
#   leer, así uno con fecha de fin vence solo, sin un proceso que lo actualice.
# - Nunca se borran: levantar uno registra quién, cuándo y por qué.
# - Solo se levanta lo vigente: uno ya levantado o vencido devuelve 409.
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo import DESCENDING

import database
from errores import ErrorDominio
from models import Bloqueo, BloqueoNuevo, EstadoCliente, LevantamientoBloqueo
from rutas.comunes import IdempotencyKey, Page, Size, a_json, ahora, buscar_perfil_o_404, no_encontrado, paginar
from security import OPERADOR, Usuario, requiere_roles

router = APIRouter(prefix="/api/v1/clientes/{clienteId}/bloqueos", tags=["Estado de cuenta"])

# Más nuevos primero; el _id desempata si dos se crearon en el mismo instante
ORDEN = [("creadoEn", DESCENDING), ("_id", DESCENDING)]


# ------------------------------------------------------------ Vigencia (la usan también perfil y estado de cuenta)

def esta_vigente(doc: dict, momento: datetime) -> bool:
    if doc.get("levantadoEn"):
        return False
    hasta = doc.get("hasta")
    return hasta is None or hasta > momento


def filtro_vigentes(momento: datetime) -> dict:
    """Condición de MongoDB equivalente a esta_vigente."""
    return {
        "levantadoEn": {"$exists": False},
        "$or": [{"hasta": {"$exists": False}}, {"hasta": {"$gt": momento}}],
    }


def filtro_no_vigentes(momento: datetime) -> dict:
    return {"$or": [{"levantadoEn": {"$exists": True}}, {"hasta": {"$lte": momento}}]}


def bloqueos_vigentes(cliente_id: str) -> list[dict]:
    filtro = {"clienteId": cliente_id, **filtro_vigentes(ahora())}
    return list(database.coleccion_bloqueos().find(filtro).sort(ORDEN))


def estado_del_cliente(cliente_id: str) -> EstadoCliente:
    filtro = {"clienteId": cliente_id, **filtro_vigentes(ahora())}
    hay = database.coleccion_bloqueos().find_one(filtro, projection={"_id": 1})
    return EstadoCliente.BLOQUEADO if hay else EstadoCliente.ACTIVO


def a_bloqueo(doc: dict, momento: datetime | None = None) -> Bloqueo:
    return Bloqueo(
        bloqueoId=doc["_id"],
        motivo=doc["motivo"],
        vigente=esta_vigente(doc, momento or ahora()),
        desde=doc.get("desde"),
        hasta=doc.get("hasta"),
        creadoEn=doc["creadoEn"],
        creadoPor=doc["creadoPor"],
        levantadoEn=doc.get("levantadoEn"),
        levantadoPor=doc.get("levantadoPor"),
        motivoLevantamiento=doc.get("motivoLevantamiento"),
    )


def a_milisegundos_utc(fecha: datetime) -> datetime:
    """Como la guarda MongoDB: en UTC y con milisegundos, así el POST devuelve lo mismo que el GET."""
    fecha = fecha.astimezone(timezone.utc)
    return fecha.replace(microsecond=fecha.microsecond // 1000 * 1000)


def _buscar_bloqueo_o_404(cliente_id: str, bloqueo_id: str) -> dict:
    # Se filtra también por clienteId: un bloqueo de otro cliente es "no encontrado" para esta ruta
    doc = database.coleccion_bloqueos().find_one({"_id": bloqueo_id, "clienteId": cliente_id})
    if not doc:
        raise no_encontrado("El bloqueo no existe para este cliente.")
    return doc


# ------------------------------------------------------------ Endpoints (solo OPERADOR)

@router.get("", operation_id="listarBloqueos")
def listar_bloqueos(
    clienteId: UUID,
    vigente: bool | None = None,
    page: Page = 0,
    size: Size = 20,
    usuario: Usuario = Depends(requiere_roles(OPERADOR)),
):
    """Historial de bloqueos del cliente; con `vigente` se filtran los vigentes o los que ya no lo están."""
    cliente_id = str(clienteId)
    buscar_perfil_o_404(cliente_id)
    momento = ahora()
    filtro = {"clienteId": cliente_id}
    if vigente is True:
        filtro.update(filtro_vigentes(momento))
    elif vigente is False:
        filtro.update(filtro_no_vigentes(momento))
    docs, datos = paginar(database.coleccion_bloqueos(), filtro, ORDEN, page, size)
    return {"items": [a_json(a_bloqueo(d, momento)) for d in docs], **datos}


@router.post("", operation_id="crearBloqueo", status_code=201)
def crear_bloqueo(
    clienteId: UUID,
    datos: BloqueoNuevo,
    idempotency_key: IdempotencyKey,
    usuario: Usuario = Depends(requiere_roles(OPERADOR)),
):
    # Por ahora la Idempotency-Key solo se exige: evitar el duplicado en un reintento queda para la etapa 5.
    cliente_id = str(clienteId)
    buscar_perfil_o_404(cliente_id)
    momento = ahora()
    doc = {
        "_id": str(uuid.uuid4()),
        "clienteId": cliente_id,
        "motivo": datos.motivo,
        "desde": momento,
        "creadoEn": momento,
        "creadoPor": usuario.sub,
    }
    if datos.hasta is not None:
        hasta = a_milisegundos_utc(datos.hasta)
        if hasta <= momento:
            raise ErrorDominio(422, "/errores/fin-de-bloqueo-pasado", "El fin del bloqueo ya pasó",
                               "La fecha `hasta` tiene que ser posterior al momento actual.")
        doc["hasta"] = hasta
    database.coleccion_bloqueos().insert_one(doc)
    return JSONResponse(a_json(a_bloqueo(doc, momento)), status_code=201,
                        headers={"Location": f"/api/v1/clientes/{cliente_id}/bloqueos/{doc['_id']}"})


@router.get("/{bloqueoId}", operation_id="obtenerBloqueo")
def obtener_bloqueo(clienteId: UUID, bloqueoId: UUID, usuario: Usuario = Depends(requiere_roles(OPERADOR))):
    cliente_id = str(clienteId)
    buscar_perfil_o_404(cliente_id)
    return a_json(a_bloqueo(_buscar_bloqueo_o_404(cliente_id, str(bloqueoId))))


@router.patch("/{bloqueoId}", operation_id="levantarBloqueo")
def levantar_bloqueo(clienteId: UUID, bloqueoId: UUID, datos: LevantamientoBloqueo,
                     usuario: Usuario = Depends(requiere_roles(OPERADOR))):
    """No borra el bloqueo: registra quién, cuándo y por qué lo levantó."""
    cliente_id, bloqueo_id = str(clienteId), str(bloqueoId)
    buscar_perfil_o_404(cliente_id)
    momento = ahora()
    # Se actualiza solo si sigue vigente, en una sola operación: si dos operadores lo levantan a la vez,
    # uno gana y el otro recibe 409
    resultado = database.coleccion_bloqueos().update_one(
        {"_id": bloqueo_id, "clienteId": cliente_id, **filtro_vigentes(momento)},
        {"$set": {"levantadoEn": momento, "levantadoPor": usuario.sub, "motivoLevantamiento": datos.motivo}},
    )
    if resultado.matched_count == 0:
        doc = _buscar_bloqueo_o_404(cliente_id, bloqueo_id)
        detalle = ("El bloqueo ya fue levantado." if doc.get("levantadoEn")
                   else "El bloqueo ya venció: su fecha `hasta` pasó.")
        raise ErrorDominio(409, "/errores/bloqueo-no-vigente", "El bloqueo no está vigente", detalle)
    return a_json(a_bloqueo(_buscar_bloqueo_o_404(cliente_id, bloqueo_id), momento))
