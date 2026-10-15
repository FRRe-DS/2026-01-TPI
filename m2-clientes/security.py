from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

# Ajusta el puerto (8080) si tu Keycloak corre en uno distinto
KEYCLOAK_CERTS_URL = "http://localhost:8080/realms/ds-2026-realm/protocol/openid-connect/certs"

# Configura el cliente para descargar las firmas de Keycloak
jwks_client = PyJWKClient(KEYCLOAK_CERTS_URL)
security = HTTPBearer()

def validar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Obtiene la clave pública de Keycloak para este token específico
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Desencripta y valida matemáticamente el token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False} # Desactivamos la verificación de audiencia por ahora para facilitar el desarrollo
        )
        
        # Si llega hasta aquí, el token es 100% válido y devuelve los datos del usuario
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido o corrupto")