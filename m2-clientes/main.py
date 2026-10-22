# API de M2 Clientes.
# Sigue el contrato común acordado con el Grupo 17: contratos/m2_clientes/openapi.yml
#
# Etapa 1: salud y perfil del cliente (RF-2.1).
# Las demás partes del contrato (direcciones, preferencias, historial, calificaciones,
# estado de cuenta y bloqueos) se agregan en las próximas etapas.
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

import config
import database
import errores
from errores import ErrorDominio, problema
from middleware import controles_generales
from models import Cliente, ClienteCambios, ClienteNuevo, EstadoCliente, Salud
from security import CLIENTE, OPERADOR, Usuario, requiere_roles, verificar_dueno

app = FastAPI(
    title="DS 2026 API - M2 Clientes (Grupo 1)",
    version="1.0.0",
    description="Implementación del Grupo 1 del contrato común de M2.",
)

errores.registrar(app)
app.middleware("http")(controles_generales)
# CORS va último para que quede por fuera de todo y responda los preflight del navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "Location", "Retry-After"],
)

# Parámetros comunes
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _a_cliente(doc: dict) -> Cliente:
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


def _json_cliente(cliente: Cliente) -> dict:
    return cliente.model_dump(mode="json", exclude_none=True)


def _buscar_o_404(cliente_id: str) -> dict:
    doc = database.coleccion_clientes().find_one({"_id": cliente_id})
    if not doc:
        raise ErrorDominio(404, "about:blank", "No encontrado", "El cliente no tiene perfil.")
    return doc


# ---------------------------------------------------------------- Salud

@app.get("/health", tags=["Salud"], operation_id="verificarSalud", response_model=Salud)
def verificar_salud(request: Request):
    """No exige token. 200 si el servicio y su base responden; si no, 503."""
    if not database.base_disponible():
        return problema(request, 503, "La base de datos de M2 no responde.",
                        headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)})
    return Salud()


# ---------------------------------------------------------------- Perfil (RF-2.1)

@app.post("/api/v1/clientes", tags=["Perfil"], operation_id="crearCliente", status_code=201,
          response_model=Cliente, response_model_exclude_none=True)
def crear_cliente(
    datos: ClienteNuevo,
    idempotency_key: IdempotencyKey,
    usuario: Usuario = Depends(requiere_roles(CLIENTE)),
):
    """Crea el perfil del cliente cuyo clienteId es el sub del token. Si ya existe, 409."""
    # Etapa 5: guardar la Idempotency-Key para devolver la respuesta original en un reintento.
    # Por ahora se exige, como dice el contrato, y un segundo intento devuelve 409.
    ahora = _ahora()
    doc = {
        "_id": usuario.sub,
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "telefono": datos.telefono,
        "creadoEn": ahora,
        "actualizadoEn": ahora,
    }
    if datos.fechaNacimiento:
        doc["fechaNacimiento"] = datos.fechaNacimiento.isoformat()
    try:
        database.coleccion_clientes().insert_one(doc)
    except DuplicateKeyError:
        raise ErrorDominio(409, "/errores/cliente-existente", "El cliente ya tiene un perfil",
                           "Ya existe un perfil para este usuario. Usá PATCH para modificarlo.")
    cliente = _a_cliente(doc)
    return JSONResponse(_json_cliente(cliente), status_code=201,
                        headers={"Location": f"/api/v1/clientes/{usuario.sub}"})


@app.get("/api/v1/clientes/{clienteId}", tags=["Perfil"], operation_id="obtenerCliente",
         response_model=Cliente, response_model_exclude_none=True)
def obtener_cliente(clienteId: UUID, usuario: Usuario = Depends(requiere_roles(CLIENTE, OPERADOR))):
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    return _json_cliente(_a_cliente(_buscar_o_404(cliente_id)))


@app.patch("/api/v1/clientes/{clienteId}", tags=["Perfil"], operation_id="actualizarCliente",
           response_model=Cliente, response_model_exclude_none=True)
def actualizar_cliente(clienteId: UUID, cambios: ClienteCambios,
                       usuario: Usuario = Depends(requiere_roles(CLIENTE))):
    """Actualiza solo los campos enviados."""
    cliente_id = str(clienteId)
    verificar_dueno(usuario, cliente_id)
    _buscar_o_404(cliente_id)
    nuevos = cambios.model_dump(exclude_unset=True)
    if "fechaNacimiento" in nuevos:
        nuevos["fechaNacimiento"] = nuevos["fechaNacimiento"].isoformat()
    nuevos["actualizadoEn"] = _ahora()
    database.coleccion_clientes().update_one({"_id": cliente_id}, {"$set": nuevos})
    return _json_cliente(_a_cliente(_buscar_o_404(cliente_id)))
