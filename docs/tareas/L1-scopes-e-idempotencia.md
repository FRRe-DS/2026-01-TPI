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
1. Aprobar el PR FRRe-DS/2026-TPI#18, que abrió el Grupo 17 con el mismo diff que su #95.
2. Cuando la cátedra lo mergee, actualizar la copia `contratos/m2_clientes/openapi.yml`.
3. En `security.py`:
   - leer el claim `scope`, que es un texto separado por espacios;
   - una dependencia que exija rol **y** scope, con el scope de cada operación como dice el contrato;
   - si falla la descarga de las claves (JWKS), responder `503` con `Retry-After`, no `401`;
   - verificar `aud` (`m2-clientes`) por configuración (`JWT_AUDIENCE`), apagado por defecto mientras el Keycloak de la cátedra no lo tenga.
4. Pruebas: tokens sin scope, con el scope equivocado y sin audiencia.
5. Coordinar con T06 que el realm tenga los scopes asignados: `clientes:read`, `clientes:write` y `clientes.estado:read` al cliente del front; `clientes.estado:read` a las cuentas de M5 y M9. El realm de desarrollo del Grupo 17 ya tiene un cliente público `m2-front` con PKCE.

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
