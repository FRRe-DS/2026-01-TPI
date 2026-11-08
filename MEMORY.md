# MEMORY.md — M2 Clientes (Grupo 1, TPI DS 2026)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Contrato común de M2 acordado con el Grupo 17 (PR #16 de `FRRe-DS/2026-17-TPI`) y **publicado**: `FRRe-DS/2026-TPI#5` se fusionó en `main` de la cátedra el 21/10. Copia en `contratos/m2_clientes/openapi.yml`.
- Ramas: las etapas se integran en `desarrollo-m2`; `main` recibió todo lo hecho hasta el 22/10 (PR #6). Lo que sigue va a `desarrollo-m2` y después otro merge a `main`. Siempre merge commit.
- Etapas 1 (perfil, PR #2) y 2 (direcciones y preferencias, PR #3): probadas en real el 21 y el 22/10 (Keycloak, MongoDB, front y Swagger como OPERADOR).
- Etapa 3 (estado de cuenta y bloqueos, RF-2.6) + aviso de cuenta bloqueada en el front: PR #8, mergeado en `desarrollo-m2` (7/11). Falta probarla en real.
- CI con GitHub Actions (PR #9): pytest + build del front en cada push y PR.
- Dockerfiles de la API y del front + `--profile api` en el compose de `m2-clientes` (7/11). Probados con bases equivalentes (sin las imágenes oficiales ni MongoDB real): falta probarlos en la PC con Docker Desktop.
- Pruebas: 214 casos = 157 de API + 57 unitarias. Las de API no son unitarias: prueban la app entera con base y tokens simulados.
- Pantalla de bienvenida (PR #5). Crear cuenta requiere el registro y el rol por defecto CLIENTE en el realm.
- **Keycloak de la cátedra (3/11):** `FRRe-DS/2026-TPI/keycloak`, realm `ds-2026-realm` con roles por módulo (`clientes-be`…), scopes `clientes:read/write` sin asignar a nadie, sin roles de persona ni `aud`. El profe: `grupo-01` es nuestra aplicación y los usuarios se crean asociados a ella; los scopes de M2 los definimos con el Grupo 17.
- **Contrato (commit 360caad del profe):** agregó `OAuth2Bearer` con scopes. Errores a corregir en un PR conjunto: `cleintes` → `clientes`, `tokenUrl` (`/protocol/openid-connect/token`) y rol + scope en el mismo renglón de `security` (si no, son alternativas).
- **Issue #7 de nuestro repo (Grupo 17, 7/11):** acordando roles + scopes, PR de corrección, realm de desarrollo común del Grupo 17 (roles, audiencia `m2-clientes`, scopes, usuarios) y mantener `/health`. Respondimos de acuerdo y propusimos `clientes.estado:read` para M5 y M9. Esperando respuesta.
- Otros módulos: M5 sin contrato. M6 publicó el suyo (roles `CLIENT`/`SYSTEM`, distintos de los nuestros). M9 lo publicó el 6/11: rechaza reservas con `CLIENTE_NO_HABILITADO` según nuestro estado de cuenta.
- M9 iba a firmar con HS256 mientras M1 fuera simulado (issue #9, 20/10). Ahora la cátedra da Keycloak con cuentas `grupo-NN` (RS256): confirmar con M9 antes de agregar HS256.

## Aprendizajes y errores a evitar
- Verificar contra la consigna textual (README de `FRRe-DS/2026-TPI`) antes de marcar algo como "falta":
  - RF-2.1 no pide baja del perfil.
  - RF-2.3 no pide confort.
  - M5 recibe el tipo de vehículo en cada solicitud (RF-5.1).
- Revisar las convenciones de la cátedra antes de pedir cambios: todos los contratos usan `title: DS 2026 API`.
- El Keycloak de `keycloak/` es una adaptación hecha por Matías del TPI **2025** de la cátedra (`ds-2025-realm`, otro proyecto). No es el M1 de 2026.
- El realm trae los roles `Cliente`, `Conductor` y `Operador`, pero el contrato exige `CLIENTE`, `OPERADOR` y `SERVICIO`: hay que crearlos a mano (README, paso 3b2).
- Git desde Linux: usar `git -c core.autocrlf=true`, si no todo aparece modificado. Para crear ramas y commitear hace falta permiso de borrado (archivos `.lock`).
- Los errores de validación de FastAPI se convierten a 400; el 422 queda para reglas de negocio.
- `DuplicateKeyError` es un `PyMongoError`: capturarlo en el endpoint, si no da 503.
- Starlette solo lista en `Allow` los métodos de la primera ruta que coincide; el manejador del 405 los junta todos con `ruta.matches(scope)`, porque desde FastAPI 0.143 `include_router` envuelve las rutas.
- MongoDB guarda milisegundos: usar `ahora()` de `rutas/comunes.py`, si no el POST y el GET devuelven fechas distintas.

## Decisiones (y por qué)
- **Adoptamos el contrato del Grupo 17:** cumple todos los RF y resuelve mejor los RNF-03, 09, 13 y 14. Además, RNF-02 pide dos implementaciones por módulo con el mismo contrato.
- **`clienteId` = `sub`, usado como `_id` en MongoDB:** lo pide el contrato y garantiza un solo perfil por usuario.
- **Roles en `realm_access.roles` y en un claim `roles` en la raíz:** sirve con Keycloak y con lo que se acuerde en el #9.
- **Bloqueos (etapa 3):** colección propia; `vigente` se calcula al leer (no levantado y sin pasar `hasta`); `estado` = `BLOQUEADO` si hay alguno vigente. Levantar uno ya levantado o vencido da 409 (lo eligió el usuario). El panel de operador en el front queda para cuando haya usuarios OPERADOR.
- **`Idempotency-Key`** se exige pero no se guarda hasta la etapa 5.
- **Una sola base: MongoDB** (confirmado por el usuario el 22/10). Se descartó MySQL; Redis y RabbitMQ quedan para el TP2.
- **Direcciones en su propia colección; preferencias dentro del perfil:** las direcciones se paginan y editan de a una; las preferencias son 1 a 1.
- **`main.py` dividido en `rutas/`** (un archivo por recurso): crece con cada etapa.
- **Listado de direcciones: más nuevas primero** (el contrato no fija orden). Una dirección de otro cliente da 404.
- **No tocamos el realm** (`keycloak/`): es de Matías; los pasos manuales están en el README.
- **Trabajo por etapas en `desarrollo-m2`:** cada etapa se integra ahí y después pasa a `main` con un PR.

## Próximos pasos
1. Cuando el Grupo 17 responda: PR del contrato a la cátedra; adaptar la API (verificar `aud` y scopes, rol + scope juntos); Docker (Dockerfiles, compose único con el realm del Grupo 17, publicar en GHCR con GitHub Actions).
2. Probar la etapa 3 en real (bloquear desde Swagger con `grupo-01`, ver el aviso en el front).
3. Probar los contenedores en la PC; después, mensajes al profe y al consorcio.
4. Etapa 4: calificaciones e historial con un mock de M6 (2 s, 1 reintento en GET, 503).
5. Etapa 5: idempotencia real (guardar clave, hash del cuerpo y respuesta).
6. Seguir el issue #7 (nuestro repo) y la respuesta de M5 y M9.
