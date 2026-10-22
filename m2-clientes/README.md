# Módulo 2 - Gestión de Clientes (TPI 2026)

Microservicio de clientes de la plataforma de movilidad. Implementa el contrato común de M2,
acordado entre el Grupo 1 y el Grupo 17: [`../contratos/m2_clientes/openapi.yml`](../contratos/m2_clientes/openapi.yml).

Hoy cubre la **etapa 1**: salud y perfil del cliente (RF-2.1). Las demás partes del contrato
(direcciones, preferencias, historial, calificaciones, estado de cuenta y bloqueos) vienen en las próximas etapas.

## Cómo instalarlo y correrlo

Las instrucciones completas (requisitos, Keycloak, MongoDB, esta API y el front) están en el README principal:
**[../README.md → Cómo instalarlo y correrlo](../README.md#-cómo-instalarlo-y-correrlo-windows)**

Resumen para correr esta API, con Keycloak y MongoDB ya levantados:

```powershell
cd C:\Proyectos\2026-01-TPI\m2-clientes
.\venv\Scripts\Activate.ps1      # la primera vez: py -3.13 -m venv venv y pip install -r requirements.txt
uvicorn main:app --reload
```

Swagger: http://localhost:8000/docs

Para correr las pruebas (no necesitan Keycloak ni MongoDB):

```powershell
pip install -r requirements-dev.txt   # solo la primera vez
python -m pytest
```

## Configuración

Se lee de variables de entorno o de un archivo `.env` en esta carpeta (RNF-06). Los valores por defecto
sirven para correr todo en la computadora de cada uno; para cambiarlos, copiar `.env.example` como `.env`.

| Variable | Para qué | Por defecto |
|---|---|---|
| `MONGO_URL` | Conexión a MongoDB | `mongodb://localhost:27017` |
| `MONGO_DB` | Nombre de la base | `m2_clientes_db` |
| `MONGO_TIMEOUT_MS` | Cuánto se espera a la base antes de responder `503` | `2000` |
| `JWKS_URL` | Claves públicas de M1 para validar el token | Keycloak local, realm `ds-2026-realm` |
| `JWT_ISSUER` | Emisor esperado del token (vacío = no se verifica) | vacío |
| `CORS_ORIGINS` | Orígenes del front, separados por coma | `http://localhost:5173` |

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.py` | Endpoints de la API |
| `models.py` | Modelos del perfil con los nombres y las reglas del contrato |
| `security.py` | Validación del token y de los roles (`CLIENTE`, `OPERADOR`, `SERVICIO`) |
| `errores.py` | Respuestas de error en formato `application/problem+json` (RFC 9457) |
| `middleware.py` | `X-Request-Id`, límite de 1 MiB (`413`) y `Content-Type` JSON (`415`) |
| `config.py` | Configuración por variables de entorno |
| `database.py` | Conexión a MongoDB (el `_id` de cada perfil es el `clienteId`) |
| `tests/` | Pruebas automáticas; también validan las respuestas contra el contrato |
| `requirements.txt` | Librerías de Python (usar Python 3.12 o 3.13) |
| `requirements-dev.txt` | Librerías para las pruebas |
| `docker-compose.yml` | MongoDB local |

## Decisiones de la etapa 1

- **`clienteId` = `sub` del token**, como dice el contrato. Se usa como `_id` en MongoDB, así que un usuario
  no puede tener dos perfiles (un segundo `POST` da `409`).
- **Roles exactos, en mayúsculas.** Se leen de `realm_access.roles` (Keycloak) y de un claim `roles` en la raíz,
  por si el formato que se acuerde para M1 (issue #9 del Grupo 17) los pone ahí.
- **`estado` siempre `ACTIVO`** hasta la etapa 3, cuando se calcule a partir de los bloqueos vigentes.
- **`Idempotency-Key` se exige en el `POST`**, pero todavía no se guarda: un reintento con la misma clave
  da `409` en vez de la respuesta original. Se completa en la etapa 5.
- **Sin baja del perfil:** el contrato no la tiene (RF-2.1 pide crear, consultar y actualizar).
