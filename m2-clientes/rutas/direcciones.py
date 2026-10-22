# Direcciones frecuentes (RF-2.2): orígenes y destinos favoritos o recientes.
# Se guardan con sus propios datos (texto y, si vienen, coordenadas), sin depender de M4.
# Las RECIENTE las carga el cliente, igual que las FAVORITA (acordado con el Grupo 17).
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pymongo import DESCENDING

import database
from models import Direccion, DireccionCambios, DireccionNueva, TipoDireccion
from rutas.comunes import IdempotencyKey, Page, Size, a_json, ahora, buscar_perfil_o_404, no_encontrado, paginar
from security import CLIENTE, OPERADOR, Usuario, requiere_roles, verificar_dueno

router = APIRouter(prefix="/api/v1/clientes/{clienteId}/direcciones", tags=["Direcciones"])

# Más nuevas primero; el _id desempata si dos se crearon en el mismo instante
ORDEN = [("creadoEn", DESCENDING), ("_id", DESCENDING)]


def a_direccion(doc: dict) -> Direccion:
    return Direccion(
        direccionId=doc["_id"],
        tipo=doc["tipo"],
        alias=doc.get("alias"),
        texto=doc["texto"],
        coordenadas=doc.get("coordenadas"),
        creadoEn=doc["creadoEn"],
    )


def _preparar(cliente_id: str, usuario: Usuario):
    """Pasos comunes: el cliente solo opera sobre lo suyo y el perfil tiene que existir."""
    verificar_dueno(usuario, cliente_id)
    buscar_perfil_o_404(cliente_id)


def _buscar_direccion_o_404(cliente_id: str, direccion_id: str) -> dict:
    # Se filtra también por clienteId: una dirección de otro cliente es "no encontrada" para esta ruta
    doc = database.coleccion_direcciones().find_one({"_id": direccion_id, "clienteId": cliente_id})
    if not doc:
        raise no_encontrado("La dirección no existe para este cliente.")
    return doc


@router.get("", operation_id="listarDirecciones")
def listar_direcciones(
    clienteId: UUID,
    tipo: TipoDireccion | None = None,
    page: Page = 0,
    size: Size = 20,
    usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR)),
):
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    filtro = {"clienteId": cliente_id}
    if tipo:
        filtro["tipo"] = tipo.value
    docs, datos = paginar(database.coleccion_direcciones(), filtro, ORDEN, page, size)
    return {"items": [a_json(a_direccion(d)) for d in docs], **datos}


@router.post("", operation_id="crearDireccion", status_code=201)
def crear_direccion(
    clienteId: UUID,
    datos: DireccionNueva,
    idempotency_key: IdempotencyKey,
    usuario: Usuario = Depends(requiere_roles(CLIENTE)),
):
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    doc = {
        "_id": str(uuid.uuid4()),
        "clienteId": cliente_id,
        **datos.model_dump(mode="json", exclude_unset=True),
        "creadoEn": ahora(),
    }
    database.coleccion_direcciones().insert_one(doc)
    return JSONResponse(a_json(a_direccion(doc)), status_code=201,
                        headers={"Location": f"/api/v1/clientes/{cliente_id}/direcciones/{doc['_id']}"})


@router.get("/{direccionId}", operation_id="obtenerDireccion")
def obtener_direccion(clienteId: UUID, direccionId: UUID,
                      usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR))):
    cliente_id = str(clienteId)
    _preparar(cliente_id, usuario)
    return a_json(a_direccion(_buscar_direccion_o_404(cliente_id, str(direccionId))))


@router.patch("/{direccionId}", operation_id="actualizarDireccion")
def actualizar_direccion(clienteId: UUID, direccionId: UUID, cambios: DireccionCambios,
                         usuario: Usuario = Depends(requiere_roles(CLIENTE))):
    """Actualiza solo los campos enviados."""
    cliente_id, direccion_id = str(clienteId), str(direccionId)
    _preparar(cliente_id, usuario)
    _buscar_direccion_o_404(cliente_id, direccion_id)
    database.coleccion_direcciones().update_one(
        {"_id": direccion_id, "clienteId": cliente_id},
        {"$set": cambios.model_dump(mode="json", exclude_unset=True)},
    )
    return a_json(a_direccion(_buscar_direccion_o_404(cliente_id, direccion_id)))


@router.delete("/{direccionId}", operation_id="eliminarDireccion", status_code=204)
def eliminar_direccion(clienteId: UUID, direccionId: UUID,
                       usuario: Usuario = Depends(requiere_roles(CLIENTE))):
    cliente_id, direccion_id = str(clienteId), str(direccionId)
    _preparar(cliente_id, usuario)
    _buscar_direccion_o_404(cliente_id, direccion_id)
    database.coleccion_direcciones().delete_one({"_id": direccion_id, "clienteId": cliente_id})
    return Response(status_code=204)
