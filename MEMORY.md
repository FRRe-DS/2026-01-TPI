# MEMORY.md — M2 Clientes (Grupo 1, TPI DS 2026)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Contrato común de M2 acordado con el Grupo 17 (PR #16 de `FRRe-DS/2026-17-TPI`) y **publicado**: `FRRe-DS/2026-TPI#5` se fusionó en `main` de la cátedra el 21/10. Copia en `contratos/m2_clientes/openapi.yml`.
- Ramas: las etapas se integran en `desarrollo-m2`; `main` recibió todo lo hecho hasta el 22/10 (PR #6). Lo que sigue va a `desarrollo-m2` y después otro merge a `main`. Siempre merge commit.
- Etapa 1 (perfil, `/health`, roles, problem+json, `X-Request-Id`, `.env`) + `AGENTS.md` y `MEMORY.md`: PR #2, mergeado en `desarrollo-m2`. Probada en real el 21/10.
- Etapa 2 (direcciones y preferencias, RF-2.2 y RF-2.3): PR #3, mergeado en `desarrollo-m2`. README actualizado (PR #4); probada en real el 22/10 (Keycloak, MongoDB, front y Swagger como OPERADOR): todo OK.
- Pruebas: 153 casos = 105 de API + 48 unitarias (`test_unitarias.py`, en `desarrollo-m2` el 22/10). Las de API no son unitarias: prueban la app entera con base y tokens simulados.
- Pantalla de bienvenida (PR #5): Crear cuenta / Ingresar llevan a Keycloak. Crear cuenta requiere activar el registro y el rol por defecto CLIENTE en el realm.
- **Keycloak de la cátedra (3/11):** `FRRe-DS/2026-TPI/keycloak`, realm `ds-2026-realm` con roles por módulo (`clientes-be`…), scopes `clientes:read/write` sin asignar a nadie, sin roles de persona ni `aud`. El profe: `grupo-01` es nuestra aplicación y los usuarios se crean asociados a ella; los scopes de M2 los definimos con el Grupo 17.
- **Contrato (commit 360caad del profe):** agregó `OAuth2Bearer` con scopes. Errores a corregir en un PR conjunto: `cleintes` → `clientes`, `tokenUrl` (`/protocol/openid-connect/token`) y rol + scope en el mismo renglón de `security` (si no, son alternativas).
- **Issue #7 de nuestro repo (Grupo 17, 7/11):** acordando roles + scopes, PR de corrección, realm de desarrollo común del Grupo 17 (roles, audiencia `m2-clientes`, scopes, usuarios) y mantener `/health`. Respondimos de acuerdo y propusimos `clientes.estado:read` para M5 y M9. Esperando respuesta.
- Pendiente de otros: M5 y M9 sin contrato; M6 publicó el suyo (roles `CLIENT`/`SYSTEM`, distintos de los nuestros).
- M9 firma sus tokens de SERVICIO con HS256 y una clave compartida mientras M1 sea simulado (issue #9, 20/10). Hoy solo aceptamos RS256 por JWKS: hay que soportarlo por configuración antes o durante la etapa 3.

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
- **`estado` siempre `ACTIVO`** hasta la etapa 3; el `Idempotency-Key` se exige pero no se guarda hasta la etapa 5.
- **Una sola base: MongoDB** (confirmado por el usuario el 22/10). Se descartó MySQL; Redis y RabbitMQ quedan para el TP2.
- **Direcciones en su propia colección; preferencias dentro del perfil:** las direcciones se paginan y editan de a una; las preferencias son 1 a 1.
- **`main.py` dividido en `rutas/`** (un archivo por recurso): crece con cada etapa.
- **Listado de direcciones: más nuevas primero** (el contrato no fija orden). Una dirección de otro cliente da 404.
- **No tocamos el realm** (`keycloak/`): es de Matías; los pasos manuales están en el README.
- **Trabajo por etapas en `desarrollo-m2`:** el usuario prefiere integrar todo ahí y mergear a `main` una sola vez al final.

## Próximos pasos
1. Cuando el Grupo 17 responda: PR del contrato a la cátedra; adaptar la API (verificar `aud` y scopes, rol + scope juntos); Docker (Dockerfiles, compose único con el realm del Grupo 17, publicar en GHCR con GitHub Actions).
2. Etapa 3 desde `desarrollo-m2`. Ojo: `test_token_hs256_hoy_no_se_acepta` fija que hoy se rechaza HS256; cambiarla al soportar los tokens de M9.
3. Etapa 3: estado de cuenta y bloqueos (SERVICIO solo en `obtenerEstadoCuenta`, `estado` calculado, aceptar tokens HS256 de M9).
4. Etapa 4: calificaciones e historial con un mock de M6 (2 s, 1 reintento en GET, 503).
5. Etapa 5: idempotencia real (guardar clave, hash del cuerpo y respuesta).
6. Seguir el issue #7 (nuestro repo) y la respuesta de M5 y M9.
