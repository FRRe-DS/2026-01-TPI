# Módulo 2 - Gestión de Clientes (TPI 2026)

Microservicio de clientes de la plataforma de movilidad. Implementa el contrato común de M2,
acordado entre el Grupo 1 y el Grupo 17: [`../contratos/m2_clientes/openapi.yml`](../contratos/m2_clientes/openapi.yml).

Hoy cubre las **etapas 1 a 3**: salud, perfil (RF-2.1), direcciones frecuentes (RF-2.2), preferencias (RF-2.3)
y estado de cuenta con bloqueos (RF-2.6). De la etapa 4 están las calificaciones al conductor (RF-2.5), que
consultan a M6 con un conector todavía provisorio; falta el historial de viajes (RF-2.4, tarea T02).

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
| `JWT_AUDIENCE` | Audiencia esperada del token (`aud`; vacío = no se verifica). Con un realm que la emita: `m2-clientes` | vacío |
| `EXIGIR_SCOPES` | Exigir el scope de cada operación, como dice el contrato. Activarlo solo con un Keycloak que emita `clientes:read`, `clientes:write` y `clientes.estado:read` | `false` |
| `CORS_ORIGINS` | Orígenes del front, separados por coma | `http://localhost:5173` |

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.py` | Arma la app: middleware, manejo de errores y rutas |
| `rutas/comunes.py` | Lo que comparten las rutas: `Idempotency-Key`, paginación, búsqueda del perfil, fecha actual |
| `rutas/salud.py`, `perfil.py`, `direcciones.py`, `preferencias.py`, `estado_cuenta.py`, `bloqueos.py`, `calificaciones.py` | Endpoints, un archivo por recurso del contrato. `bloqueos.py` tiene también la regla de vigencia que usan el perfil y el estado de cuenta |
| `integraciones/m6.py` | Conector a M6 (Viajes). **Provisorio:** `obtener_viaje` tiene la firma definitiva pero responde `503` hasta que T02 la implemente |
| `models.py` | Modelos del perfil con los nombres y las reglas del contrato |
| `security.py` | Validación del token y de los roles (`CLIENTE`, `OPERADOR`, `SERVICIO`) |
| `errores.py` | Respuestas de error en formato `application/problem+json` (RFC 9457) |
| `middleware.py` | `X-Request-Id`, límite de 1 MiB (`413`) y `Content-Type` JSON (`415`) |
| `config.py` | Configuración por variables de entorno |
| `database.py` | Conexión a MongoDB (el `_id` de cada perfil es el `clienteId`) |
| `tests/` | Pruebas automáticas: de API (validan cada respuesta contra el contrato) y unitarias (`test_unitarias.py`, funciones sueltas sin HTTP) |
| `requirements.txt` | Librerías de Python (usar Python 3.12 o 3.13) |
| `requirements-dev.txt` | Librerías para las pruebas |
| `docker-compose.yml` | MongoDB local y, con `--profile api`, la API en un contenedor |
| `Dockerfile`, `.dockerignore` | Imagen de la API: Python 3.13 slim, usuario sin privilegios, healthcheck contra `/health`. No copia el `.env` ni los tests |

## Decisiones de la etapa 1

- **`clienteId` = `sub` del token**, como dice el contrato. Se usa como `_id` en MongoDB, así que un usuario
  no puede tener dos perfiles (un segundo `POST` da `409`).
- **Roles exactos, en mayúsculas.** Se leen de `realm_access.roles` (Keycloak) y de un claim `roles` en la raíz,
  por si el formato que se acuerde para M1 (issue #9 del Grupo 17) los pone ahí.
- **`estado`:** desde la etapa 3 se calcula a partir de los bloqueos vigentes (ver abajo).
- **`Idempotency-Key` se exige en el `POST`**, pero todavía no se guarda: un reintento con la misma clave
  da `409` en vez de la respuesta original. Se completa en la etapa 5.
- **Sin baja del perfil:** el contrato no la tiene (RF-2.1 pide crear, consultar y actualizar).

## Decisiones de la etapa 2

- **Direcciones en su propia colección** (`direcciones`, con el `clienteId` del dueño e índice por cliente y fecha),
  porque se listan paginadas y se editan de a una. **Las preferencias van dentro del perfil** (campo `preferencias`),
  porque son una por cliente.
- **Listado de direcciones: las más nuevas primero.** El contrato no fija el orden.
- **Una dirección de otro cliente da `404`** para la ruta pedida (al `CLIENTE` antes le corta el `403` por no ser el dueño).
- **`PUT` de preferencias reemplaza todo:** lo que no se manda (por ejemplo, las observaciones) se borra.
- **Las fechas se recortan a milisegundos** antes de guardarlas, porque MongoDB no guarda más precisión;
  así lo que devuelve un `POST` es igual a lo que devuelve después un `GET`.

## Decisiones de la etapa 3

- **Bloqueos en su propia colección** (`bloqueos`, con el `clienteId` del bloqueado e índice por cliente y fecha).
  Nunca se borran: levantar uno agrega `levantadoEn`, `levantadoPor` y `motivoLevantamiento`.
- **`vigente` no se guarda, se calcula al leer:** un bloqueo está vigente si no fue levantado y no pasó su `hasta`.
  Así uno con fecha de fin vence solo, sin un proceso que lo actualice.
- **`estado` del cliente:** `BLOQUEADO` si tiene al menos un bloqueo vigente; si no, `ACTIVO`. Se calcula igual en el
  estado de cuenta y en el perfil. Puede tener varios bloqueos a la vez (por motivos distintos).
- **`desde` es el momento en que se registra:** el contrato no deja elegir el inicio.
- **`hasta` tiene que venir con zona horaria** (si no, `400`) y ser futura (si no, `422` con
  `type: /errores/fin-de-bloqueo-pasado`). Se guarda en UTC y con milisegundos.
- **Solo se levanta lo vigente:** uno ya levantado o ya vencido da `409` (`type: /errores/bloqueo-no-vigente`).
  La actualización es condicional, así que si dos operadores lo levantan a la vez, uno recibe `409`.
- **Un bloqueo de otro cliente da `404`** para la ruta pedida, igual que las direcciones.
- **`SERVICIO` solo entra al estado de cuenta.** Su `sub` nombra al módulo, así que no se aplica la regla de dueño.
- **`Idempotency-Key` en `crearBloqueo`:** se exige, pero un reintento crea otro bloqueo. Se completa en la etapa 5.

## Decisiones de las calificaciones (etapa 4, tarea T03)

- **Colección propia** (`calificaciones`) con un **índice único por `(clienteId, viajeId)`**. El duplicado lo frena
  MongoDB al guardar, no un "if ya existe" en el código: si llegan dos pedidos a la vez, el `if` dejaría pasar los
  dos (RNF-08). El `DuplicateKeyError` se convierte en `409` (`type: /errores/calificacion-duplicada`). Hay otro
  índice por `(clienteId, creadoEn)` para el listado.
- **Los índices se crean al arrancar la API.** Si la API arranca antes que MongoDB, el único no existe hasta
  reiniciarla. Con `docker compose --profile api` no pasa, porque la API espera a que MongoDB esté listo.
- **Se le pregunta a M6** (`obtener_viaje`) con el mismo token que mandó el cliente. Viaje inexistente o de otro
  cliente: `404` en los dos casos, para no revelar que el viaje de otro existe. No `COMPLETED`: `422`
  (`type: /errores/viaje-no-completado`). M6 sin responder: `503`.
- **El conductor sale de M6** (`driverId`), nunca del cuerpo: el modelo rechaza un `conductorId` con `400`.
- **`puntaje` estricto:** el contrato dice entero, así que `"5"`, `4.5` o `true` dan `400`
  (sin `strict`, Pydantic tomaría `true` como 1 estrella).
- **`viajeId` en su forma normal** (UUID en minúsculas) antes de guardarlo: escribirlo en mayúsculas no esquiva el
  índice único.
- **Listado: las más nuevas primero.** El contrato no fija el orden.
- **`Idempotency-Key`:** se exige; un reintento choca con el índice único y da `409`. Se completa en la etapa 5.
- **`integraciones/m6.py` es provisorio:** solo tiene la firma de `obtener_viaje`, para poder programar y probar
  esto antes de T02. Las pruebas reemplazan esa función por un M6 simulado.

## Seguridad: scopes, audiencia y M1 (contrato del 9/11)

El contrato con scopes lo acordamos con el Grupo 17 (issue #7) y está en FRRe-DS/2026-TPI#18.

- **Rol y scope juntos:** cada operación declara en `requiere_roles(..., scope=...)` el mismo rol y scope que
  su renglón de `security`. Las lecturas piden `clientes:read`, las escrituras `clientes:write` y
  `obtenerEstadoCuenta` pide `clientes.estado:read` a todos (CLIENTE, OPERADOR y SERVICIO). Ese scope no
  sirve para nada más: es el que reciben M5 y M9 (RNF-19). El parámetro `scope` es obligatorio, y una prueba
  compara cada ruta con el contrato.
- **`EXIGIR_SCOPES` apagado por defecto:** el Keycloak local y el de la cátedra todavía no emiten esos scopes.
  Si se exigieran, todo daría `403`. Se activa cuando el realm los tenga (tarea T06 o el realm del Grupo 17).
- **Audiencia por configuración:** el contrato no la fija. Con `JWT_AUDIENCE=m2-clientes`, un token sin esa
  audiencia da `401`.
- **M1 caído da `503`, no `401`:** si no se pueden bajar las claves (JWKS), el token puede estar bien, así que
  se responde `503` con `Retry-After`. Si M1 responde pero el token no coincide con ninguna clave, sigue
  siendo `401`.
- **El front** pide los scopes solo si se configura `VITE_KEYCLOAK_SCOPE`: un Keycloak que no los tiene
  rechaza el inicio de sesión.
