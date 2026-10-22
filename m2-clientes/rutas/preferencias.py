# Preferencias del cliente (RF-2.3): tipos de vehículo, canales de comunicación y accesibilidad.
# Se guardan dentro del documento del perfil (campo "preferencias"), porque son 1 a 1 con el cliente.
from uuid import UUID

from fastapi import APIRouter, Depends

import database
from models import Preferencias
from rutas.comunes import a_json, buscar_perfil_o_404
from security import CLIENTE, OPERADOR, Usuario, requiere_roles, verificar_dueno

router = APIRouter(prefix="/api/v1/clientes/{clienteId}/preferencias", tags=["Preferencias"])


@router.get("", operation_id="obtenerPreferencias")
def obtener_preferencias(clienteId: UUID, usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR))):
    """Si el cliente nunca las guardó, devuelve los valores por defecto (listas vacías)."""
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    perfil = buscar_perfil_o_404(cliente_id)
    guardadas = perfil.get("preferencias")
    return a_json(Preferencias(**guardadas) if guardadas else Preferencias.por_defecto())


@router.put("", operation_id="guardarPreferencias")
def guardar_preferencias(clienteId: UUID, preferencias: Preferencias,
                         usuario: Usuario = Depends(requiere_roles(CLIENTE))):
    """Reemplaza todas las preferencias. Es idempotente: repetirlo deja lo mismo."""
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    buscar_perfil_o_404(cliente_id)
    datos = preferencias.model_dump(mode="json", exclude_none=True)
    database.coleccion_clientes().update_one({"_id": cliente_id}, {"$set": {"preferencias": datos}})
    return a_json(preferencias)
