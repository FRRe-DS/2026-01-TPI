# Valida que las respuestas de la API respeten los esquemas del contrato acordado
# (contratos/m2_clientes/openapi.yml, en la raíz del repo).
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

RUTA_CONTRATO = Path(__file__).resolve().parents[2] / "contratos" / "m2_clientes" / "openapi.yml"


@lru_cache
def _contrato() -> dict:
    return yaml.safe_load(RUTA_CONTRATO.read_text(encoding="utf-8"))


def validar(nombre_esquema: str, datos):
    """Falla si `datos` no cumple components.schemas.<nombre_esquema> del contrato."""
    esquema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/components/schemas/{nombre_esquema}",
        "components": _contrato()["components"],
    }
    Draft202012Validator(esquema, format_checker=FormatChecker()).validate(datos)


def respuestas_declaradas(operation_id: str) -> set[int]:
    """Códigos HTTP que el contrato declara para una operación."""
    for ruta in _contrato()["paths"].values():
        for metodo, op in ruta.items():
            if isinstance(op, dict) and op.get("operationId") == operation_id:
                return {int(c) for c in op["responses"]}
    raise KeyError(operation_id)
