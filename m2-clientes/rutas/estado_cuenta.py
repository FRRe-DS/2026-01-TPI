# Estado de cuenta (RF-2.6): si el cliente está habilitado y qué bloqueos vigentes tiene.
# Es la única operación que admite SERVICIO: la consultan M5 y M9 antes de aceptar un viaje o una reserva.
from uuid import UUID

from fastapi import APIRouter, Depends

from models import EstadoCliente, EstadoCuenta
from rutas.bloqueos import a_bloqueo, bloqueos_vigentes
from rutas.comunes import a_json, ahora, buscar_perfil_o_404
from security import CLIENTE, LEER_ESTADO, OPERADOR, SERVICIO, Usuario, requiere_roles, verificar_dueno

router = APIRouter(prefix="/api/v1/clientes/{clienteId}/estado-cuenta", tags=["Estado de cuenta"])


@router.get("", operation_id="obtenerEstadoCuenta")
def obtener_estado_cuenta(clienteId: UUID,
                          usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR, SERVICIO, scope=LEER_ESTADO))):
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)  # el CLIENTE solo ve el suyo; OPERADOR y SERVICIO, cualquiera
    buscar_perfil_o_404(cliente_id)
    momento = ahora()
    vigentes = [a_bloqueo(d, momento) for d in bloqueos_vigentes(cliente_id)]
    estado = EstadoCliente.BLOQUEADO if vigentes else EstadoCliente.ACTIVO
    return a_json(EstadoCuenta(clienteId=cliente_id, estado=estado, bloqueosVigentes=vigentes))
