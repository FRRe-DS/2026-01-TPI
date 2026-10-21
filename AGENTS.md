# AGENTS.md — M2 Clientes (Grupo 1, TPI Desarrollo de Software 2026)

Microservicio de **clientes** (módulo M2) de una plataforma distribuida de movilidad urbana bajo demanda, hecho por el Grupo 1 para el TPI de Desarrollo de Software 2026 (UTN FRRe). Administra el perfil del cliente, sus direcciones frecuentes, sus preferencias, el historial de viajes (obtenido de M6), las calificaciones a conductores y el estado de cuenta con bloqueos (RF-2.1 a RF-2.6). Es una de las dos implementaciones de M2: la otra es del Grupo 17, y las dos cumplen el **mismo contrato OpenAPI**.

## Stack y estructura

- **API:** Python 3.13 (3.12 también sirve; con 3.14 o más nuevo `pip install` falla), FastAPI 0.143, Pydantic 2.13, PyMongo 4.18, PyJWT 2.15. Corre con uvicorn en el puerto **8000**.
- **Base:** MongoDB 7.0 en Docker.
- **Identidad (M1):** hoy es un Keycloak 23.0.6 local, con Postgres 16.2, en Docker. Realm `ds-2026-realm`. El formato definitivo del token todavía se está acordando entre los grupos (issue #9 de `FRRe-DS/2026-17-TPI`).
- **Front:** React 19, Vite 8, Mantine 9, keycloak-js 26. Corre en el puerto **5173**.
- **Entorno de desarrollo:** Windows con PowerShell. El repo está en `C:\Proyectos\2026-01-TPI`.

| Ruta | Qué es |
|---|---|
| `contratos/m2_clientes/openapi.yml` | **Contrato común de M2**, copia del publicado en la cátedra (`FRRe-DS/2026-TPI`, PR #5). Es la fuente de verdad de rutas, campos, roles y códigos de error. |
| `m2-clientes/main.py` | Endpoints. Hoy cubre la etapa 1: `/health` y el perfil (POST, GET, PATCH). |
| `m2-clientes/security.py` | Validación del token (JWKS de M1), lectura de roles, `requiere_roles` y `verificar_dueno`. |
| `m2-clientes/errores.py` | Errores en formato `application/problem+json` y todos los manejadores de excepciones. |
| `m2-clientes/middleware.py` | `X-Request-Id`, límite de 1 MiB (`413`) y `Content-Type` JSON (`415`). |
| `m2-clientes/config.py` | Toda la configuración, leída de variables de entorno o de `.env` (ver `.env.example`). |
| `m2-clientes/tests/contrato.py` | Valida las respuestas contra los esquemas del contrato. |
| `frontend/src/api.js` | Único lugar donde el front llama a la API. |
| `keycloak/` | Docker Compose y realm de Keycloak. Lo armó otro integrante y puede venir de la cátedra: `keycloak/.env` tiene credenciales de desarrollo y **sí** está versionado. |

## Comandos

Todos en PowerShell, desde la raíz del repo.

```powershell
# Levantar Keycloak y MongoDB (Docker Desktop abierto)
cd keycloak;    docker compose up -d; cd ..
cd m2-clientes; docker compose up -d; cd ..

# API: la primera vez
cd m2-clientes
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# API: correr (Swagger en http://localhost:8000/docs)
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload

# API: pruebas (no necesitan Keycloak ni MongoDB)
python -m pytest

# Front
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # verifica que compile
```

No hay linter ni formateador configurado. No agregues uno sin preguntar.

## Convenciones

- **Idioma:** el código (variables, funciones, archivos), los comentarios, los mensajes de error y los textos del front van en **español**. Los mensajes para el usuario se escriben con voseo ("Solo podés operar sobre tu propio perfil").
- **Nombres:** funciones y variables de Python en `snake_case`. Los campos JSON van en `camelCase`, exactamente como los nombra el contrato (`clienteId`, `fechaNacimiento`, `creadoEn`). Los modelos Pydantic llevan el mismo nombre que el esquema del contrato (`ClienteNuevo`, `ClienteCambios`, `Cliente`).
- **Endpoints:** seguí el patrón de `m2-clientes/main.py`:
  - el decorador con `operation_id` igual al `operationId` del contrato;
  - la dependencia `requiere_roles(...)` con los roles que declara el `security` de esa operación;
  - `verificar_dueno` cuando la ruta lleva `{clienteId}`;
  - `ErrorDominio` para los errores de negocio;
  - `_json_cliente` (con `exclude_none`) para armar la respuesta.
- **Modelos:** `ConfigDict(extra="forbid")` en todos los cuerpos de entrada (equivale a `additionalProperties: false`). En los PATCH, los `null` se rechazan.
- **Pruebas:** seguí el patrón de `m2-clientes/tests/test_perfil.py`: `auth([...roles], sub)` para el token, `es_problema(r, status)` para los errores y `validar("Esquema", cuerpo)` para chequear contra el contrato.
- **Front:** toda llamada nueva va en `frontend/src/api.js`. Los errores llegan como `ErrorApi`, que trae `status`.
- **Comentarios:** que expliquen el porqué, con referencia al RF, al RNF o al contrato cuando aplique.

## Reglas de dominio / trampas conocidas

- **El contrato es compartido con el Grupo 17.** No se agregan, renombran ni sacan rutas, campos, roles ni códigos de respuesta por cuenta propia. Cualquier cambio se acuerda primero con ellos (en un PR de `FRRe-DS/2026-17-TPI`) y después se publica en la cátedra. Si una operación necesita algo que el contrato no tiene, parar y avisar.
- **Solo se devuelven los códigos que el contrato declara para cada operación.** Hay un test que lo verifica; al agregar una operación, sumala a `test_codigos_usados_estan_en_el_contrato`.
- **`clienteId` = `sub` del token, pero solo en tokens de CLIENTE.** En los de SERVICIO, el `sub` es el nombre del módulo (por ejemplo `m9-reservas`). En MongoDB, el `clienteId` es el `_id` del perfil.
- **Roles exactos, en mayúsculas:** `CLIENTE`, `CONDUCTOR`, `OPERADOR`, `SERVICIO`. `SERVICIO` solo se admite en `obtenerEstadoCuenta` (lo usan M5 y M9); en cualquier otra operación da `403`. El realm de Keycloak trae `Cliente`, `Conductor` y `Operador`, que **no** sirven: hay que crear los roles en mayúsculas a mano (paso 3b2 del README).
- **Errores:**
  - Los genéricos usan `type: about:blank` y un `title` fijo en español (ver `TITULOS` en `errores.py`); el 403 es "Sin permiso".
  - Los de dominio (409, 422, 503 de otro módulo) llevan `type` propio, por ejemplo `/errores/cliente-existente`.
  - El esquema `Problema` **no** tiene `errores[]`: el campo con error se nombra en `detail`.
- **Formato inválido da 400, no 422.** Los errores de validación de FastAPI se convierten a `400`. El `422` queda para reglas de negocio (por ejemplo, un viaje no completado) y para reusar una `Idempotency-Key` con otro cuerpo.
- **Un `X-Request-Id` inválido nunca da 400:** se reemplaza por uno generado. Toda respuesta lo devuelve, incluso un `500`.
- **`DuplicateKeyError` es un `PyMongoError`.** Si no se captura en el endpoint, el manejador global lo convierte en `503`.
- **MongoDB no guarda `date`:** `fechaNacimiento` se guarda como texto ISO (`AAAA-MM-DD`). El cliente de Mongo es `tz_aware=True`, así que todas las fechas y horas van en UTC.
- **Datos de otros módulos, solo por su API** (RNF-05): el historial y la validación de viajes salen de la API de M6, nunca de su base, y no se copian a la nuestra. Para hablar con otros módulos: 2 s por intento, un reintento solo en los GET, y si no hay respuesta, `503` con el `type` de dependencia. La espera máxima publicada en el contrato es 4,2 s; cambiarla es cambiar el contrato. M6 todavía no tiene contrato, así que para probar hay que usar un mock.
- **Calificaciones:** el conductor sale de M6, no del cuerpo. Hay una sola por (cliente, viaje), garantizada en la base con índice único; un segundo intento da `409`.
- **Bloqueos:** nunca se borran. Levantar uno es un `PATCH` con motivo, que registra quién y cuándo lo levantó; si ya estaba levantado, `409`. El `estado` del cliente (`ACTIVO` o `BLOQUEADO`) se calcula a partir de los bloqueos vigentes; hasta la etapa 3 es siempre `ACTIVO`.
- **El contrato no tiene** baja del perfil, listado de clientes, `email` en M2 ni `usadoEn` en las direcciones. Las direcciones `RECIENTE` las carga el cliente, igual que las favoritas.
- **Paginación:** `page` empieza en 0; `size` vale 20 por defecto y como máximo 100. La respuesta lleva `items`, `page`, `size`, `totalElementos` y `totalPaginas`.
- **`Idempotency-Key`:** es obligatoria en los POST. Por ahora solo se exige: un reintento con la misma clave da `409`, no la respuesta original. La idempotencia real queda para la etapa 5.
- **Git desde Linux sobre este repo:** los archivos están en CRLF y git los guarda en LF. Desde una shell Linux, usar siempre `git -c core.autocrlf=true ...`; si no, todo el repo aparece como modificado. Desde Windows no hace falta.

## Forma de trabajar

- **El trabajo sigue el plan por etapas,** y cada etapa va en su propia rama `feature/...` con su propio PR hacia `main`:
  1. perfil (hecha);
  2. direcciones y preferencias;
  3. estado de cuenta y bloqueos;
  4. calificaciones e historial (M6);
  5. idempotencia.
- **Planificá antes de tocar código** cuando el cambio afecta más de un archivo, toca el contrato o la integración con otros módulos, o cambia cómo se guardan los datos. Mostrá el plan y esperá el visto bueno.
- **Cambios chicos y completos:** una operación del contrato a la vez, con sus pruebas y su parte en el front si corresponde. No mezcles refactors con funcionalidad nueva.
- **Al terminar, explicá:**
  - qué operaciones del contrato quedaron cubiertas;
  - qué decisiones tomaste que el contrato no fijaba;
  - el resultado de las pruebas;
  - qué pasos manuales hacen falta (por ejemplo, en Keycloak);
  - qué no pudiste verificar.

## Límites

- **Siempre:**
  - trabajar en una rama, nunca en `main`;
  - correr `python -m pytest` y, si tocaste el front, `npm run build`;
  - agregar pruebas para cada operación o regla nueva;
  - mantener los README al día (los endpoints y el estado del módulo);
  - leer la configuración de `config.py` o de variables de entorno.
- **Preguntá antes de:**
  - agregar dependencias (Python o npm) o cambiar versiones;
  - crear archivos o carpetas nuevos fuera de los patrones existentes;
  - cambiar cómo se guardan los datos en MongoDB (estructura de documentos, índices, colecciones);
  - tocar `keycloak/` o el realm;
  - hacer commits, push o abrir PRs;
  - borrar archivos.
- **Nunca:**
  - modificar `contratos/m2_clientes/openapi.yml` para que coincida con el código (es al revés);
  - guardar secretos nuevos en el repo (RNF-06);
  - leer o escribir la base de otro módulo;
  - hacer push a `main` o reescribir su historia;
  - borrar bloqueos o calificaciones;
  - desactivar la validación del token o de roles "para probar".

## Verificación

1. `cd m2-clientes; python -m pytest`: tienen que pasar todas. Las pruebas también validan cada respuesta contra el contrato.
2. Si tocaste el front: `cd frontend; npm run build` sin errores.
3. Revisá en `contratos/m2_clientes/openapi.yml` que la operación coincida: ruta, método, roles en `security`, campos y códigos de respuesta.
4. Prueba manual con todo levantado: entrar al front con `cliente-demo`, hacer el flujo afectado y, para operaciones de OPERADOR, probar en Swagger (`/docs`) con el token de la cuenta `grupo-01` (paso 6 del README).
5. Si algo no se pudo verificar (por ejemplo, algo que depende de M6 o de M1), decilo explícitamente al terminar.
