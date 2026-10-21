# Configuración de M2 por variables de entorno (RNF-06).
# Si existe un archivo .env en esta carpeta, se leen de ahí; si no, se usan los
# valores por defecto, que sirven para correr todo en la computadora de cada uno.
import os

from dotenv import load_dotenv

load_dotenv()

# Base de datos
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "m2_clientes_db")
# Cuánto espera M2 a la base antes de responder 503 (en milisegundos)
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "2000"))

# Identidad (M1). De acá se bajan las claves públicas para validar la firma del token.
JWKS_URL = os.getenv(
    "JWKS_URL",
    "http://localhost:8080/realms/ds-2026-realm/protocol/openid-connect/certs",
)
# Emisor esperado del token (claim "iss"). Vacío = no se verifica, hasta que M1 lo defina (#9).
JWT_ISSUER = os.getenv("JWT_ISSUER", "")

# Orígenes que pueden llamar a la API desde el navegador (el front), separados por coma
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

# Límite del cuerpo de los pedidos: 1 MiB, como dice el contrato
MAX_BODY_BYTES = 1024 * 1024

# Segundos que se sugieren en Retry-After cuando la base no responde
RETRY_AFTER_SEGUNDOS = 5
