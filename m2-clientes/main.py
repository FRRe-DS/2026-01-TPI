# API de M2 Clientes: arma la aplicación.
# Sigue el contrato común acordado con el Grupo 17: contratos/m2_clientes/openapi.yml
# Los endpoints están en rutas/, un archivo por recurso del contrato.
#
# Cubierto: salud, perfil (etapa 1), direcciones y preferencias (etapa 2).
# Falta: estado de cuenta y bloqueos (3), calificaciones e historial (4), idempotencia (5).
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
import database
import errores
from middleware import controles_generales
from rutas import direcciones, perfil, preferencias, salud


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    database.asegurar_indices()
    yield


app = FastAPI(
    title="DS 2026 API - M2 Clientes (Grupo 1)",
    version="1.0.0",
    description="Implementación del Grupo 1 del contrato común de M2.",
    lifespan=ciclo_de_vida,
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

for modulo in (salud, perfil, direcciones, preferencias):
    app.include_router(modulo.router)
