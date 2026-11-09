# L1 · Scopes, audiencia e idempotencia (Lucas)

| | |
|---|---|
| **Dificultad** | Difícil |
| **Depende de** | La respuesta del Grupo 17 (issue #7) para los scopes. La idempotencia no depende de nadie |
| **Fecha objetivo** | PR abierto el lunes 16/11 |

## L1a · Scopes y audiencia

Acordado con el Grupo 17 en el issue #7 (8/11). El cambio del contrato es su PR FRRe-DS/2026-17-TPI#95:
- Cada operación exige **rol y scope juntos** (mismo renglón del `security`).
- Lecturas con `clientes:read`, escrituras con `clientes:write`. Los bloqueos, con esos mismos scopes + OPERADOR.
- `obtenerEstadoCuenta` pide **`clientes.estado:read` a todos** (CLIENTE, OPERADOR y SERVICIO). Ese scope no da acceso a nada más. Los tokens de las personas también lo tienen que traer.
- Si M2 no puede obtener de M1 la clave pública del token, responde **`503`** (hoy responde `401`).
- La audiencia (`aud`) no está en el contrato: es configuración de cada M2, con `m2-clientes` por defecto (confirmado por el Grupo 17 el 9/11).

Pasos:
1. ✔ PR FRRe-DS/2026-TPI#18 aprobado por el Grupo 1 (9/11). Falta el merge de la cátedra.
2. ✔ Copia `contratos/m2_clientes/openapi.yml` actualizada con el archivo del PR #18 (sin esperar el merge: el contenido está acordado; si la cátedra pide cambios, se vuelve a copiar).
3. ✔ En `security.py` (rama `feature/l1-scopes`):
   - se lee el claim `scope` (texto separado por espacios);
   - `requiere_roles(*roles, scope=...)` exige rol **y** scope; el scope es obligatorio en cada ruta;
   - los scopes se exigen solo con `EXIGIR_SCOPES=true` (apagado por defecto mientras los Keycloak no los emitan);
   - si falla la descarga de las claves (JWKS), `503` con `Retry-After`;
   - `aud` se verifica solo si `JWT_AUDIENCE` tiene valor.
4. ✔ Pruebas (`tests/test_seguridad.py`): cada ruta comparada con el contrato, sin el scope `403`, con el scope pasa, `clientes.estado:read` no abre nada más, audiencia y `503` de M1.
5. Pendiente: activar `EXIGIR_SCOPES` y `JWT_AUDIENCE` cuando usemos un realm con scopes y audiencia (T06 o el del Grupo 17), y configurar `VITE_KEYCLOAK_SCOPE` en el front.
6. Coordinar con T06 que el realm tenga los scopes asignados: `clientes:read`, `clientes:write` y `clientes.estado:read` al cliente del front; `clientes.estado:read` a las cuentas de M5 y M9. El realm de desarrollo del Grupo 17 ya tiene un cliente público `m2-front` con PKCE.

## L1b · Idempotencia (etapa 5, RNF-09)

Hoy `Idempotency-Key` se exige pero no se usa: un reintento del mismo `POST` crea otro recurso (por ejemplo, otro bloqueo).

1. Colección `idempotencia`, con:
   - la clave más quién la usó (`sub`) y la operación;
   - un hash del cuerpo;
   - la respuesta guardada (status, cuerpo y `Location`);
   - un índice único y un TTL, por ejemplo 24 h.
2. Misma clave y mismo cuerpo: devolver la respuesta original. Misma clave con otro cuerpo: `422`.
3. Aplicarlo a todos los `POST`: crear perfil, dirección, bloqueo y calificación.
4. Cuidar la concurrencia: dos pedidos iguales al mismo tiempo. El índice único resuelve el empate.
5. Actualizar `AGENTS.md`, que hoy dice que un reintento da `409`.

## L2 · Coordinación, revisión y cierre

- Reunión de arranque (lunes 9/11): mostrar el sistema y asignar las tareas en el [tablero](README.md).
- Revisar los PR de cada uno: que respeten el contrato y `AGENTS.md`, con pruebas y el CI en verde.
- Mensajes pendientes:
  - **al profe:** `grupo-01` con `conductores:*`, cliente público del front, quién crea los usuarios, audiencia;
  - **al consorcio:** los nombres de roles no coinciden (M6 usa `CLIENT`/`SYSTEM`; M2 `CLIENTE`/`SERVICIO`);
  - **recordatorio al Grupo 17.**
- Martes 17/11: todo mergeado en `desarrollo-m2` y prueba completa.
- Miércoles 18/11: PR de `desarrollo-m2` a `main`, ensayo.
- Mantener `MEMORY.md` al día.
