# Piezas que comparten todas las rutas: encabezados, paginación y búsqueda del perfil.
import math
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Header, Query
from pydantic import BaseModel

import database
from errores import ErrorDominio

# Idempotency-Key: obligatoria en los POST del contrato (1 a 255 caracteres).
# Etapa 5: guardarla para devolver la respuesta original en un reintento.
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]

# Paginación del contrato: page desde 0; size 20 por defecto y 100 como máximo
Page = Annotated[int, Query(ge=0, description="Número de página, desde 0.")]
Size = Annotated[int, Query(ge=1, le=100, description="Elementos por página.")]


def ahora() -> datetime:
    # MongoDB guarda las fechas con milisegundos: se recorta acá para que lo que devuelve un POST
    # sea igual a lo que devuelve después un GET
    momento = datetime.now(timezone.utc)
    return momento.replace(microsecond=momento.microsecond // 1000 * 1000)


def a_json(modelo: BaseModel) -> dict:
    """Respuesta sin los campos opcionales vacíos (el contrato no admite null)."""
    return modelo.model_dump(mode="json", exclude_none=True)


def no_encontrado(detalle: str) -> ErrorDominio:
    return ErrorDominio(404, "about:blank", "No encontrado", detalle)


def buscar_perfil_o_404(cliente_id: str) -> dict:
    doc = database.coleccion_clientes().find_one({"_id": cliente_id})
    if not doc:
        raise no_encontrado("El cliente no tiene perfil.")
    return doc


def paginar(coleccion, filtro: dict, orden: list, page: int, size: int) -> tuple[list[dict], dict]:
    """Devuelve los documentos de la página pedida y los datos de paginación del contrato."""
    total = coleccion.count_documents(filtro)
    docs = list(coleccion.find(filtro).sort(orden).skip(page * size).limit(size))
    datos = {
        "page": page,
        "size": size,
        "totalElementos": total,
        "totalPaginas": math.ceil(total / size),
    }
    return docs, datos
