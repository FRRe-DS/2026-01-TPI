# Historial de viajes del cliente (RF-2.4).
import math
import database
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from integraciones import m6
from models import ViajeResumen, PaginaViajes
from rutas.comunes import Page, Size, a_json, buscar_perfil_o_404
from security import CLIENTE, LEER, OPERADOR, Usuario, requiere_roles, verificar_dueno

router = APIRouter(
    prefix="/api/v1/clientes/{clienteId}/viajes",
    tags=["Historial de viajes"],
)


@router.get("", operation_id="listarHistorialViajes")
def listar_viajes(
    clienteId: UUID,
    request: Request,
    page: Page = 0,
    size: Size = 20,
    usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR, scope=LEER)),
):
    cliente_id = str(clienteId)

    verificar_dueno(usuario, cliente_id)
    buscar_perfil_o_404(cliente_id)

    autorizacion = request.headers.get("Authorization", "")

    respuesta_m6 = m6.listar_viajes(
        cliente_id,
        page,
        size,
        autorizacion,
    )

    viajes = respuesta_m6.get("items", [])

    ids_viajes = [viaje["id"] for viaje in viajes]

    calificados = {
        doc["viajeId"]
        for doc in database.coleccion_calificaciones().find(
            {
                "clienteId": cliente_id,
                "viajeId": {"$in": ids_viajes},
            },
            {"viajeId": 1, "_id": 0},
        )
    }

    items = []

    for viaje in viajes:

        tipo_vehiculo = {
            "CAR": "AUTO",
            "MOTORCYCLE": "MOTO",
        }.get(viaje.get("vehicleType"))

        items.append(
            ViajeResumen(
                viajeId=viaje["id"],
                tipoVehiculo=tipo_vehiculo,
                estado=viaje["state"],
                origen=viaje.get("originAddress"),
                destino=viaje.get("destinationAddress"),
                iniciadoEn=viaje.get("createdAt"),
                finalizadoEn=viaje.get("completedAt"),
                conductorId=viaje.get("driverId"),
                calificado=viaje["id"] in calificados,
            )
        )

    total_elementos = respuesta_m6["total"]
    total_paginas = math.ceil(total_elementos / size)

    return a_json(
        PaginaViajes(
            items=items,
            page=page,
            size=size,
            totalElementos=total_elementos,
            totalPaginas=total_paginas,
        )
    )
