# Perfil del cliente (RF-2.1): crear, consultar y actualizar.
# El contrato no tiene baja ni listado de clientes.
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

import database
from errores import ErrorDominio
from models import Cliente, ClienteCambios, ClienteNuevo, EstadoCliente
from rutas.comunes import IdempotencyKey, a_json, ahora, buscar_perfil_o_404
from security import CLIENTE, OPERADOR, Usuario, requiere_roles, verificar_dueno

router = APIRouter(prefix="/api/v1/clientes", tags=["Perfil"])


def a_cliente(doc: dict) -> Cliente:
    return Cliente(
        clienteId=doc["_id"],
        nombre=doc["nombre"],
        apellido=doc["apellido"],
        telefono=doc["telefono"],
        fechaNacimiento=date.fromisoformat(doc["fechaNacimiento"]) if doc.get("fechaNacimiento") else None,
        # Etapa 3: el estado se calcula a partir de los bloqueos vigentes. Por ahora, siempre ACTIVO.
        estado=EstadoCliente.ACTIVO,
        creadoEn=doc["creadoEn"],
        actualizadoEn=doc["actualizadoEn"],
    )


@router.post("", operation_id="crearCliente", status_code=201,
             response_model=Cliente, response_model_exclude_none=True)
def crear_cliente(
    datos: ClienteNuevo,
    idempotency_key: IdempotencyKey,
    usuario: Usuario = Depends(requiere_roles(CLIENTE)),
):
    """Crea el perfil del cliente cuyo clienteId es el sub del token. Si ya existe, 409."""
    # Por ahora la Idempotency-Key solo se exige: un segundo intento devuelve 409 (etapa 5).
    momento = ahora()
    doc = {
        "_id": usuario.sub,
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "telefono": datos.telefono,
        "creadoEn": momento,
        "actualizadoEn": momento,
    }
    if datos.fechaNacimiento:
        doc["fechaNacimiento"] = datos.fechaNacimiento.isoformat()
    try:
        database.coleccion_clientes().insert_one(doc)
    except DuplicateKeyError:
        raise ErrorDominio(409, "/errores/cliente-existente", "El cliente ya tiene un perfil",
                           "Ya existe un perfil para este usuario. Usá PATCH para modificarlo.")
    return JSONResponse(a_json(a_cliente(doc)), status_code=201,
                        headers={"Location": f"/api/v1/clientes/{usuario.sub}"})


@router.get("/{clienteId}", operation_id="obtenerCliente",
            response_model=Cliente, response_model_exclude_none=True)
def obtener_cliente(clienteId: UUID, usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR))):
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    return a_json(a_cliente(buscar_perfil_o_404(cliente_id)))


@router.patch("/{clienteId}", operation_id="actualizarCliente",
              response_model=Cliente, response_model_exclude_none=True)
def actualizar_cliente(clienteId: UUID, cambios: ClienteCambios,
                       usuario: Usuario = Depends(requiere_roles(CLIENTE))):
    """Actualiza solo los campos enviados."""
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    buscar_perfil_o_404(cliente_id)
    nuevos = cambios.model_dump(exclude_unset=True)
    if "fechaNacimiento" in nuevos:
        nuevos["fechaNacimiento"] = nuevos["fechaNacimiento"].isoformat()
    nuevos["actualizadoEn"] = ahora()
    database.coleccion_clientes().update_one({"_id": cliente_id}, {"$set": nuevos})
    return a_json(a_cliente(buscar_perfil_o_404(cliente_id)))
