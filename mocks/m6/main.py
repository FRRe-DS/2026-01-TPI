
import uuid
import os
import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

viajes_en_memoria = {}


def simular_problemas():
    demora = float(os.getenv("DEMORA_SEGUNDOS", "0"))

    if demora > 0:
        time.sleep(demora)

    if os.getenv("FALLAR", "").lower() == "si":
        return JSONResponse(
            status_code=500,
            content={"error": "Error simulado de M6"},
        )

    return None



@app.get("/health")
def comprobar_salud():
    problema = simular_problemas()

    if problema is not None:
        return problema

    return {"status": "UP"}



def generar_viajes(client_id):
    estados = [
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "IN_PROGRESS",
        "CANCELLED",
        "COMPLETED",
    ]

    viajes = []

    for numero, estado in enumerate(estados, start=1):
        identificador = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{client_id}-{numero}")
        )

        viaje = {
            "id": identificador,
            "state": estado,
            "vehicleType": "MOTORCYCLE" if numero == 6 else "CAR",
            "clientId": client_id,
            "driverId": str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"conductor-{numero}")
            ),
            "originAddress": "Av. 9 de Julio 100, Resistencia",
            "destinationAddress": "Plaza 25 de Mayo, Resistencia",
            "createdAt": (
                datetime.now(timezone.utc) - timedelta(days=numero)
            ).isoformat(),
            "completedAt": (
                datetime.now(timezone.utc) - timedelta(days=numero)
            ).isoformat() if estado == "COMPLETED" else None,
        }

        viajes.append(viaje)
        viajes_en_memoria[identificador] = viaje

    return viajes




@app.get("/trips")
def obtener_viajes(
    clientId: uuid.UUID,
    state: str | None = None,
    page: int = 1,
    pageSize: int = 20,
):

    problema = simular_problemas()

    if problema is not None:
        return problema

    viajes = generar_viajes(str(clientId))

    if state is not None:
        viajes = [viaje for viaje in viajes if viaje["state"] == state]

    if page < 1 or pageSize < 1 or pageSize > 100:
        return {"error": "Parámetros de paginación inválidos"}

    inicio = (page - 1) * pageSize
    fin = inicio + pageSize

    return {
        "items": viajes[inicio:fin],
        "page": page,
        "pageSize": pageSize,
        "total": len(viajes),
    }


@app.get("/trips/{tripId}")
def obtener_viaje_por_id(tripId: uuid.UUID):

    problema = simular_problemas()

    if problema is not None:
        return problema
        
    identificador = str(tripId)

    if identificador not in viajes_en_memoria:
        return JSONResponse(
            status_code=404,
            content={
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
            },
            media_type="application/problem+json",
        )

    return viajes_en_memoria[identificador]


