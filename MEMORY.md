# MEMORY.md — M2 Clientes (Grupo 1, TPI DS 2026)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Contrato común de M2 acordado con el Grupo 17 (PR #16 de `FRRe-DS/2026-17-TPI`) y **publicado**: `FRRe-DS/2026-TPI#5` se fusionó en `main` de la cátedra el 21/10. Copia en `contratos/m2_clientes/openapi.yml`.
- Etapa 1 (perfil, `/health`, roles, problem+json, `X-Request-Id`, `.env`) + `AGENTS.md` y `MEMORY.md`: rama `feature/contrato-m2-etapa1`, subida a GitHub y probada en real el 21/10.
- Etapa 2 (direcciones y preferencias, RF-2.2 y RF-2.3): rama `feature/contrato-m2-etapa2`, creada desde la de la etapa 1. 105 tests OK; probada en real el 21/10 (Keycloak, MongoDB y front): todo OK. Sin commitear todavía.
- Pendiente de otros: M5 (grupos 4 y 13) no confirmó si le alcanza con `obtenerEstadoCuenta`; formato del token de M1 abierto en el issue #9 de `2026-17-TPI`; M6 sin contrato.
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
- **Direcciones en su propia colección; preferencias dentro del perfil:** las direcciones se paginan y editan de a una; las preferencias son 1 a 1.
- **`main.py` dividido en `rutas/`** (un archivo por recurso): crece con cada etapa.
- **Listado de direcciones: más nuevas primero** (el contrato no fija orden). Una dirección de otro cliente da 404.
- **No tocamos el realm** (`keycloak/`): es de Matías; los pasos manuales están en el README.
- **Trabajo por etapas,** cada una en su rama `feature/...` con su PR; nunca en `main`.

## Próximos pasos
1. PR de la etapa 1 hacia `main`; commitear la etapa 2, subirla y abrir su PR.
2. Etapa 3: estado de cuenta y bloqueos (SERVICIO solo en `obtenerEstadoCuenta`, `estado` calculado, aceptar tokens HS256 de M9).
3. Etapa 4: calificaciones e historial con un mock de M6 (2 s, 1 reintento en GET, 503).
4. Etapa 5: idempotencia real (guardar clave, hash del cuerpo y respuesta).
5. Seguir el issue #9 (token de M1) y la respuesta de M5.
