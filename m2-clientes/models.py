from pydantic import BaseModel, EmailStr
from typing import List, Optional

class Direccion(BaseModel):
    etiqueta: str  # Ej: "Casa", "Trabajo"
    calle: str
    numero: str
    ciudad: str
    es_principal: bool = False

class Preferencias(BaseModel):
    viaje_silencioso: bool = False
    temperatura_aire: str = "Media"
    musica: Optional[str] = None

class Cliente(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    telefono: str
    direcciones: List[Direccion] = []
    preferencias: Preferencias = Preferencias()