# Calificaciones al conductor (RF-2.5): después de un viaje, el cliente le pone de 1 a 5 estrellas.
#
# Reglas:
# - Solo se califica un viaje COMPLETED del que el cliente fue pasajero. Eso se le pregunta a M6.
# - El conductor sale de la respuesta de M6, no del cuerpo: así nadie puede calificar a otro conductor.
# - Una sola calificación por cliente y viaje. La garantiza el índice único de la base (database.py):
#   un segundo intento choca con el índice y da 409, aunque los dos pedidos lleguen a la vez (RNF-08).
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

import database
from errores import ErrorDominio
from integraciones import m6
from models import Calificacion, CalificacionNueva
from rutas.comunes import IdempotencyKey, Page, Size, a_json, ahora, buscar_perfil_o_404, no_encontrado, paginar
from security import CLIENTE, ESCRIBIR, LEER, OPERADOR, Usuario, requiere_roles, verificar_dueno

router = APIRouter(prefix="/api/v1/clientes/{clienteId}/calificaciones", tags=["Calificaciones"])

# Más nuevas primero; el _id desempata si dos se crearon en el mismo instante
ORDEN = [("creadoEn", DESCENDING), ("_id", DESCENDING)]

# Estado de un viaje terminado, como lo nombra el contrato de M6
VIAJE_COMPLETADO = "COMPLETED"


def a_calificacion(doc: dict) -> Calificacion:
    return Calificacion(
        calificacionId=doc["_id"],
        viajeId=doc["viajeId"],
        conductorId=doc["conductorId"],
        puntaje=doc["puntaje"],
        comentario=doc.get("comentario"),
        creadoEn=doc["creadoEn"],
    )


def _preparar(cliente_id: str, usuario: Usuario):
    """Pasos comunes: el cliente solo opera sobre lo suyo y el perfil tiene que existir."""
    verificar_dueno(usuario, cliente_id)
    buscar_perfil_o_404(cliente_id)


def _buscar_calificacion_o_404(cliente_id: str, calificacion_id: str) -> dict:
    # Se filtra también por clienteId: una calificación de otro cliente es "no encontrada" para esta ruta
    doc = database.coleccion_calificaciones().find_one({"_id": calificacion_id, "clienteId": cliente_id})
    if not doc:
        raise no_encontrado("La calificación no existe para este cliente.")
    return doc


@router.get("", operation_id="listarCalificaciones")
def listar_calificaciones(
    clienteId: UUID,
    page: Page = 0,
    size: Size = 20,
    usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR, scope=LEER)),
):
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    docs, datos = paginar(database.coleccion_calificaciones(), {"clienteId": cliente_id}, ORDEN, page, size)
    return {"items": [a_json(a_calificacion(d)) for d in docs], **datos}


@router.post("", operation_id="calificarConductor", status_code=201)
def calificar_conductor(
    clienteId: UUID,
    datos: CalificacionNueva,
    idempotency_key: IdempotencyKey,
    request: Request,
    usuario: Usuario = Depends(requiere_roles(CLIENTE, scope=ESCRIBIR)),
):
    # Por ahora la Idempotency-Key solo se exige (etapa 5): un reintento choca con el índice único y da 409.
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    viaje_id = str(datos.viajeId)  # forma normal del UUID (minúsculas): así el índice único no se esquiva

    # Se le pregunta a M6 con el mismo token que llegó. Si M6 no responde, obtener_viaje lanza el 503.
    viaje = m6.obtener_viaje(viaje_id, request.headers.get("Authorization", ""))
    # Inexistente o de otro cliente: 404 en los dos casos, para no revelar que el viaje de otro existe
    if viaje is None or viaje.get("clientId") != cliente_id:
        raise no_encontrado("El viaje no existe o no es tuyo.")
    if viaje.get("state") != VIAJE_COMPLETADO:
        raise ErrorDominio(422, "/errores/viaje-no-completado", "El viaje no está completado",
                           "Solo podés calificar un viaje que ya terminó.")

    doc = {
        "_id": str(uuid.uuid4()),
        "clienteId": cliente_id,
        "viajeId": viaje_id,
        "conductorId": viaje["driverId"],  # de M6, nunca del cuerpo
        "puntaje": datos.puntaje,
        "creadoEn": ahora(),
    }
    if datos.comentario is not None:
        doc["comentario"] = datos.comentario
    try:
        database.coleccion_calificaciones().insert_one(doc)
    except DuplicateKeyError:
        # Lo frena el índice único (clienteId, viajeId). Hay que capturarlo acá: si no, termina en 503
        raise ErrorDominio(409, "/errores/calificacion-duplicada", "El viaje ya fue calificado",
                           "Ya calificaste este viaje: se permite una sola calificación por viaje.")
    return JSONResponse(a_json(a_calificacion(doc)), status_code=201,
                        headers={"Location": f"/api/v1/clientes/{cliente_id}/calificaciones/{doc['_id']}"})


@router.get("/{calificacionId}", operation_id="obtenerCalificacion")
def obtener_calificacion(clienteId: UUID, calificacionId: UUID,
                         usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR, scope=LEER))):
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    return a_json(a_calificacion(_buscar_calificacion_o_404(cliente_id, str(calificacionId))))
