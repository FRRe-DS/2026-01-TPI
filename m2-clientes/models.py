# Modelos del perfil, con los nombres y las reglas del contrato acordado
# (contratos/m2_clientes/openapi.yml: ClienteNuevo, ClienteCambios y Cliente).
from datetime import date, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Nombre = Annotated[str, StringConstraints(min_length=1, max_length=100)]
# Teléfono en formato E.164, por ejemplo +5493624000000
Telefono = Annotated[str, StringConstraints(pattern=r"^\+[1-9][0-9]{6,14}$")]


class EstadoCliente(str, Enum):
    ACTIVO = "ACTIVO"        # puede solicitar y reservar viajes
    BLOQUEADO = "BLOQUEADO"  # tiene al menos un bloqueo administrativo vigente


class ClienteNuevo(BaseModel):
    """Cuerpo de POST /api/v1/clientes."""
    model_config = ConfigDict(extra="forbid")  # additionalProperties: false

    nombre: Nombre
    apellido: Nombre
    telefono: Telefono
    fechaNacimiento: date | None = None

    @model_validator(mode="after")
    def sin_nulos(self):
        if "fechaNacimiento" in self.model_fields_set and self.fechaNacimiento is None:
            raise ValueError("fechaNacimiento no puede ser null; si no la tenés, no la mandes")
        return self


class ClienteCambios(BaseModel):
    """Cuerpo de PATCH /api/v1/clientes/{clienteId}: solo los campos que cambian."""
    model_config = ConfigDict(extra="forbid")

    nombre: Nombre | None = None
    apellido: Nombre | None = None
    telefono: Telefono | None = None
    fechaNacimiento: date | None = None

    @model_validator(mode="after")
    def al_menos_un_campo_y_sin_nulos(self):
        if not self.model_fields_set:
            raise ValueError("Mandá al menos un campo para cambiar")
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


class Cliente(BaseModel):
    """Perfil que devuelve la API."""
    clienteId: str
    nombre: str
    apellido: str
    telefono: str
    fechaNacimiento: date | None = None
    estado: EstadoCliente
    creadoEn: datetime
    actualizadoEn: datetime


class Salud(BaseModel):
    estado: str = Field(default="ok")
