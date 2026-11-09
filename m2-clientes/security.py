# Autenticación y autorización.
#
# - El token lo emite M1 (hoy, el Keycloak local) y se manda como "Authorization: Bearer <token>".
# - Se valida la firma con las claves públicas de M1 (JWKS) y el vencimiento.
# - Los roles salen del token. Cada operación declara cuáles admite (CLIENTE, OPERADOR, SERVICIO),
#   igual que en el "security" del contrato. Los nombres se comparan exactos, con mayúsculas.
# - Scopes (contrato, acordado con el Grupo 17 en FRRe-DS/2026-TPI#18): cada operación exige además
#   un scope en el mismo renglón que sus roles: clientes:read (lecturas), clientes:write (escrituras)
#   y clientes.estado:read (solo obtenerEstadoCuenta). Se controla si EXIGIR_SCOPES está activo:
#   está apagado por defecto mientras los Keycloak que usamos no emitan esos scopes.
# - La audiencia ("aud") se verifica solo si JWT_AUDIENCE tiene valor (m2-clientes cuando el realm la emita).
# - Si no se pueden bajar las claves de M1 (JWKS), la culpa no es del token: 503, no 401.
# - En los tokens de CLIENTE, el "sub" es el clienteId. En los de SERVICIO, identifica la cuenta del módulo.
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

import config

CLIENTE = "CLIENTE"
OPERADOR = "OPERADOR"
SERVICIO = "SERVICIO"

# Scopes del contrato (OAuth2Bearer)
LEER = "clientes:read"
ESCRIBIR = "clientes:write"
LEER_ESTADO = "clientes.estado:read"

_jwks_client = PyJWKClient(config.JWKS_URL, cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class Usuario:
    sub: str
    roles: set[str] = field(default_factory=set)
    scopes: set[str] = field(default_factory=set)


def obtener_clave(token: str):
    """Clave pública con la que se firmó el token. Los tests la reemplazan por una propia."""
    return _jwks_client.get_signing_key_from_jwt(token).key


def _roles_del_token(payload: dict) -> set[str]:
    # Keycloak pone los roles del realm en realm_access.roles. Aceptamos también un claim "roles"
    # en la raíz, por si el formato que se acuerde para M1 (#9) los pone ahí.
    roles = set(payload.get("realm_access", {}).get("roles", []) or [])
    roles.update(payload.get("roles", []) or [])
    return roles


def _scopes_del_token(payload: dict) -> set[str]:
    # OAuth2 (y Keycloak) manda los scopes en un solo texto separado por espacios: "openid clientes:read"
    scope = payload.get("scope") or ""
    return set(scope.split()) if isinstance(scope, str) else set()


def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Usuario:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Falta el token de acceso.")
    token = credenciales.credentials
    try:
        clave = obtener_clave(token)
    except PyJWKClientConnectionError:
        # M1 no responde: el token puede estar bien, así que no es un 401 (contrato: 503)
        raise HTTPException(status_code=503, detail="No se pudo obtener de M1 la clave para validar el token.",
                            headers={"Retry-After": str(config.RETRY_AFTER_SEGUNDOS)})
    except Exception:
        raise HTTPException(status_code=401, detail="El token no es válido.")
    try:
        kwargs = {}
        if config.JWT_ISSUER:
            kwargs["issuer"] = config.JWT_ISSUER
        if config.JWT_AUDIENCE:
            kwargs["audience"] = config.JWT_AUDIENCE
        opciones = {"verify_aud": bool(config.JWT_AUDIENCE)}
        payload = jwt.decode(token, clave, algorithms=["RS256"], options=opciones, **kwargs)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token venció.")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="El token no está emitido para M2.")
    except Exception:
        raise HTTPException(status_code=401, detail="El token no es válido.")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="El token no tiene sub.")
    return Usuario(sub=payload["sub"], roles=_roles_del_token(payload), scopes=_scopes_del_token(payload))


def requiere_roles(*roles_admitidos: str, scope: str):
    """Dependencia que deja pasar solo a quien tenga alguno de los roles y, además, el scope indicado.

    Rol y scope van juntos, como en el mismo renglón del "security" del contrato. El scope se exige
    solo si EXIGIR_SCOPES está activo; igual es obligatorio declararlo en cada operación.
    """

    def verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        habilitantes = usuario.roles.intersection(roles_admitidos)
        if not habilitantes:
            raise HTTPException(status_code=403, detail="Tu rol no permite esta operación.")
        if config.EXIGIR_SCOPES and scope not in usuario.scopes:
            raise HTTPException(status_code=403, detail=f"El token no trae el scope {scope}.")
        # Nos quedamos solo con los roles que esta operación admite
        return Usuario(sub=usuario.sub, roles=habilitantes, scopes=usuario.scopes)

    verificar.scope = scope  # para que las pruebas comparen cada operación con el contrato
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
