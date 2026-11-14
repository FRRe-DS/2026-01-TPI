# Modelos con los nombres y las reglas del contrato acordado (contratos/m2_clientes/openapi.yml).
# Cada clase lleva el mismo nombre que su esquema en components.schemas.
from datetime import date, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

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


def _rechazar_nulos(modelo: BaseModel):
    """El contrato no admite null en ningún campo de entrada: si un campo opcional no se usa, no se manda."""
    nulos = [c for c in modelo.model_fields_set if getattr(modelo, c) is None]
    if nulos:
        raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")


def _sin_repetidos(valores: list, campo: str):
    """uniqueItems: true del contrato."""
    if len(set(valores)) != len(valores):
        raise ValueError(f"{campo} tiene valores repetidos")


# ------------------------------------------------------------------ Direcciones (RF-2.2)

class TipoDireccion(str, Enum):
    FAVORITA = "FAVORITA"
    RECIENTE = "RECIENTE"


class Coordenadas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


Alias = Annotated[str, StringConstraints(max_length=50)]
TextoDireccion = Annotated[str, StringConstraints(min_length=1, max_length=255)]


class DireccionNueva(BaseModel):
    """Cuerpo de POST .../direcciones. Guarda solo datos propios: nada de identificadores de M4 (RF-2.2)."""
    model_config = ConfigDict(extra="forbid")

    tipo: TipoDireccion
    alias: Alias | None = None
    texto: TextoDireccion
    coordenadas: Coordenadas | None = None

    @model_validator(mode="after")
    def sin_nulos(self):
        _rechazar_nulos(self)
        return self


class DireccionCambios(BaseModel):
    """Cuerpo de PATCH .../direcciones/{direccionId}: solo los campos que cambian."""
    model_config = ConfigDict(extra="forbid")

    tipo: TipoDireccion | None = None
    alias: Alias | None = None
    texto: TextoDireccion | None = None
    coordenadas: Coordenadas | None = None

    @model_validator(mode="after")
    def al_menos_un_campo_y_sin_nulos(self):
        if not self.model_fields_set:
            raise ValueError("Mandá al menos un campo para cambiar")
        _rechazar_nulos(self)
        return self


class Direccion(BaseModel):
    direccionId: str
    tipo: TipoDireccion
    alias: str | None = None
    texto: str
    coordenadas: Coordenadas | None = None
    creadoEn: datetime


# ------------------------------------------------------------------ Preferencias (RF-2.3)

class TipoVehiculo(str, Enum):
    AUTO = "AUTO"
    MOTO = "MOTO"


class CanalComunicacion(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class NecesidadAccesibilidad(str, Enum):
    SILLA_DE_RUEDAS = "SILLA_DE_RUEDAS"
    ASISTENCIA_VISUAL = "ASISTENCIA_VISUAL"
    ASISTENCIA_AUDITIVA = "ASISTENCIA_AUDITIVA"
    ANIMAL_DE_ASISTENCIA = "ANIMAL_DE_ASISTENCIA"


class Preferencias(BaseModel):
    """Se usa para el PUT (reemplaza todo) y para la respuesta del GET."""
    model_config = ConfigDict(extra="forbid")

    tiposVehiculo: list[TipoVehiculo]          # vacío = cualquiera
    canales: list[CanalComunicacion]           # vacío = ningún canal opcional
    accesibilidad: list[NecesidadAccesibilidad]
    observacionesAccesibilidad: Annotated[str, StringConstraints(max_length=255)] | None = None

    @model_validator(mode="after")
    def validar(self):
        _rechazar_nulos(self)
        _sin_repetidos(self.tiposVehiculo, "tiposVehiculo")
        _sin_repetidos(self.canales, "canales")
        _sin_repetidos(self.accesibilidad, "accesibilidad")
        return self

    @classmethod
    def por_defecto(cls) -> "Preferencias":
        """Lo que devuelve el GET si el cliente nunca guardó preferencias."""
        return cls(tiposVehiculo=[], canales=[], accesibilidad=[])


# ------------------------------------------------------------ Estado de cuenta y bloqueos (RF-2.6)

Motivo = Annotated[str, StringConstraints(min_length=1, max_length=500)]


class BloqueoNuevo(BaseModel):
    """Cuerpo de POST .../bloqueos. Sin `hasta`, el bloqueo sigue hasta que un operador lo levante."""
    model_config = ConfigDict(extra="forbid")

    motivo: Motivo
    hasta: AwareDatetime | None = None  # con zona horaria: una fecha sin zona es ambigua (400)

    @model_validator(mode="after")
    def sin_nulos(self):
        _rechazar_nulos(self)
        return self


class LevantamientoBloqueo(BaseModel):
    """Cuerpo de PATCH .../bloqueos/{bloqueoId}: por qué se levanta."""
    model_config = ConfigDict(extra="forbid")

    motivo: Motivo


class Bloqueo(BaseModel):
    bloqueoId: str
    motivo: str
    vigente: bool
    desde: datetime | None = None
    hasta: datetime | None = None
    creadoEn: datetime
    creadoPor: str
    levantadoEn: datetime | None = None
    levantadoPor: str | None = None
    motivoLevantamiento: str | None = None


class EstadoCuenta(BaseModel):
    clienteId: str
    estado: EstadoCliente
    bloqueosVigentes: list[Bloqueo]


# ------------------------------------------------------------ Calificaciones (RF-2.5)

# strict: el contrato dice "integer". Sin strict, Pydantic aceptaría "5", 5.0 y hasta true (= 1 estrella)
Puntaje = Annotated[int, Field(strict=True, ge=1, le=5)]
Comentario = Annotated[str, StringConstraints(max_length=500)]


class CalificacionNueva(BaseModel):
    """Cuerpo de POST .../calificaciones. El conductor no viene acá: sale de M6, así nadie califica a otro."""
    model_config = ConfigDict(extra="forbid")

    viajeId: UUID
    puntaje: Puntaje
    comentario: Comentario | None = None

    @model_validator(mode="after")
    def sin_nulos(self):
        _rechazar_nulos(self)
        return self


class Calificacion(BaseModel):
    calificacionId: str
    viajeId: str
    conductorId: str
    puntaje: int
    comentario: str | None = None
    creadoEn: datetime
