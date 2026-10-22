# Autenticación y autorización.
#
# - El token lo emite M1 (hoy, el Keycloak local) y se manda como "Authorization: Bearer <token>".
# - Se valida la firma con las claves públicas de M1 (JWKS) y el vencimiento.
# - Los roles salen del token. Cada operación declara cuáles admite (CLIENTE, OPERADOR, SERVICIO),
#   igual que en el "security" del contrato. Los nombres se comparan exactos, con mayúsculas.
# - En los tokens de CLIENTE, el "sub" es el clienteId. En los de SERVICIO, el "sub" nombra al módulo.
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

import config

CLIENTE = "CLIENTE"
OPERADOR = "OPERADOR"
SERVICIO = "SERVICIO"

_jwks_client = PyJWKClient(config.JWKS_URL, cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class Usuario:
    sub: str
    roles: set[str] = field(default_factory=set)


def obtener_clave(token: str):
    """Clave pública con la que se firmó el token. Los tests la reemplazan por una propia."""
    return _jwks_client.get_signing_key_from_jwt(token).key


def _roles_del_token(payload: dict) -> set[str]:
    # Keycloak pone los roles del realm en realm_access.roles. Aceptamos también un claim "roles"
    # en la raíz, por si el formato que se acuerde para M1 (#9) los pone ahí.
    roles = set(payload.get("realm_access", {}).get("roles", []) or [])
    roles.update(payload.get("roles", []) or [])
    return roles


def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Usuario:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    token = credenciales.credentials
    try:
        opciones = {"verify_aud": False}  # la audiencia se define con M1 (#9)
        kwargs = {"issuer": config.JWT_ISSUER} if config.JWT_ISSUER else {}
        payload = jwt.decode(token, obtener_clave(token), algorithms=["RS256"], options=opciones, **kwargs)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token venció.")
    except Exception:
        raise HTTPException(status_code=401, detail="El token no es válido.")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="El token no tiene sub.")
    return Usuario(sub=payload["sub"], roles=_roles_del_token(payload))


def requiere_roles(*roles_admitidos: str):
    """Dependencia que deja pasar solo a quien tenga alguno de los roles indicados."""

    def verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        habilitantes = usuario.roles.intersection(roles_admitidos)
        if not habilitantes:
            raise HTTPException(status_code=403, detail="Tu rol no permite esta operación.")
        # Nos quedamos solo con los roles que esta operación admite
        return Usuario(sub=usuario.sub, roles=habilitantes)

    return verificar


def verificar_dueno(usuario: Usuario, cliente_id: str):
    """Un CLIENTE solo opera sobre su propio perfil.

    Si la operación también admite OPERADOR o SERVICIO y el usuario tiene ese rol, puede operar
    sobre cualquier cliente. `usuario` es el que devuelve requiere_roles (solo roles admitidos).
    """
    if usuario.roles - {CLIENTE}:
        return
    if usuario.sub != cliente_id:
        raise HTTPException(status_code=403, detail="Solo podés operar sobre tu propio perfil.")
