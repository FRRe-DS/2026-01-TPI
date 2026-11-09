# T03 · Calificar al conductor después de un viaje (RF-2.5)

| | |
|---|---|
| **Dificultad** | Media |
| **Depende de** | La función `obtener_viaje` de T02. Para empezar no hace falta esperarla: en las pruebas se simula |
| **Destraba** | T04 (el botón "Calificar" del front) y el campo `calificado` del historial de T02 |
| **Fecha objetivo** | PR abierto el lunes 16/11 |
| **Rama sugerida** | `feature/t03-calificaciones` |

## Qué es y para qué sirve

Después de un viaje **terminado**, el cliente puede ponerle de **1 a 5 estrellas** al conductor, con un comentario opcional. Reglas de la consigna y del contrato:

- Solo se califica un viaje **completado** del que el cliente fue pasajero. Eso se le pregunta a M6.
- **Una sola calificación por viaje.** Si el cliente intenta calificar dos veces el mismo viaje, el segundo intento da `409` (conflicto). Lo garantiza la base con un **índice único**.
- El conductor calificado **sale de la respuesta de M6**, no de lo que manda el cliente. Así nadie puede calificar a otro conductor.

Es como la encuesta del final de una compra: solo te la mandan si la compra se entregó, y una vez.

## Lo que tenés que saber antes

- **El contrato:** en `contratos/m2_clientes/openapi.yml` buscá `calificarConductor`, `listarCalificaciones`, `obtenerCalificacion` y los esquemas `CalificacionNueva`, `Calificacion` y `PaginaCalificaciones`.
- **Modelos para copiar:** `m2-clientes/rutas/direcciones.py` y `m2-clientes/rutas/bloqueos.py` (un POST con `Idempotency-Key` y errores propios), y sus pruebas.
- **El índice único:** mirá cómo `rutas/perfil.py` captura `DuplicateKeyError` para devolver `409`. En `AGENTS.md` está la trampa: si no lo capturás, termina en `503`.

## Pasos

1. **Modelos** en `models.py`: `CalificacionNueva` y `Calificacion`, con los nombres y las reglas del contrato:
   - `viajeId` es un UUID y `puntaje` un entero de 1 a 5;
   - `comentario` es opcional, de hasta 500 caracteres;
   - `extra="forbid"` y sin `null`, como los demás modelos.
2. **Base** en `database.py`:
   - la función `coleccion_calificaciones()`;
   - en `asegurar_indices()`, un índice **único** por `(clienteId, viajeId)` y otro por `(clienteId, creadoEn)` para el listado.

   Agregá la colección al fixture `base_en_memoria` de `tests/conftest.py`. Cambiar cómo se guardan los datos requiere el OK de Lucas: mostrale el diseño antes.
3. **Rutas** en `rutas/calificaciones.py`:
   - **`POST`** (solo `CLIENTE`, con `verificar_dueno`, perfil existente e `Idempotency-Key`):
     1. `viaje = m6.obtener_viaje(viajeId, autorizacion)`;
     2. si devuelve `None`, responde `404`;
     3. si `viaje["clientId"]` no es el cliente, `404`;
     4. si `viaje["state"]` no es `COMPLETED`, `422` con `type` `/errores/viaje-no-completado`;
     5. guarda con `conductorId = viaje["driverId"]` y `creadoEn = ahora()`;
     6. si choca con el índice único (`DuplicateKeyError`), `409` con `type` `/errores/calificacion-duplicada`;
     7. responde `201` con el encabezado `Location`.
   - **`GET` del listado** (`CLIENTE` dueño u `OPERADOR`): paginado, las más nuevas primero.
   - **`GET` de una**: buscada por `_id` y `clienteId`; la de otro cliente da `404`.
4. Registrá el router en `main.py`.
5. Avisale a quien tenga T02 que ya existe la colección, así completa el campo `calificado` del historial.

## Pruebas (`tests/test_calificaciones.py`)

- Simulá M6 con `monkeypatch` sobre `integraciones.m6.obtener_viaje`, para que devuelva un viaje `COMPLETED`, uno `IN_PROGRESS`, uno de otro cliente o `None`.
- Casos:
  - calificar bien da `201` y la respuesta cumple `validar("Calificacion", ...)`;
  - calificar dos veces da `409`;
  - un viaje no completado da `422`;
  - un viaje inexistente o ajeno da `404`;
  - un puntaje de 0 o 6, o un campo de más, da `400`;
  - un `OPERADOR` no puede calificar (`403`) pero sí listar;
  - un cliente ajeno da `403`;
  - M6 caído da `503`;
  - el conductor guardado es el que dijo M6 aunque el cliente mande otro.
- Agregá tus operaciones al `test_codigos_usados_estan_en_el_contrato`.

## Cómo probarlo a mano

Con el M6 simulado (T01) corriendo:
1. Listá los viajes del cliente (T02) o pedile a M6 `GET /trips?clientId=...` y copiá el `id` de uno `COMPLETED`.
2. En Swagger, con el token del cliente: `POST .../calificaciones` con `{"viajeId": "...", "puntaje": 5, "comentario": "Muy amable"}`.
3. Repetilo: tiene que dar `409`. Probá también con uno `IN_PROGRESS`: tiene que dar `422`.

## Terminado cuando

- [ ] Las tres operaciones responden como dice el contrato.
- [ ] No se puede calificar dos veces el mismo viaje, y lo garantiza el índice único.
- [ ] El conductor sale de M6, no del cuerpo.
- [ ] Las pruebas nuevas pasan, y también todas las anteriores.
- [ ] README de `m2-clientes` y tablero actualizados.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea y `rutas/bloqueos.py` como modelo. Tengo que hacer las calificaciones al conductor en FastAPI + MongoDB: `POST`, el listado y el detalle, con un índice único por cliente y viaje. El viaje se valida con `integraciones.m6.obtener_viaje(viaje_id, autorizacion)`, que hace otra persona. En las pruebas lo simulo con `monkeypatch`. Explicame primero qué es un índice único y por qué es mejor que revisar antes de insertar. Después armemos el modelo, la ruta y las pruebas de a una cosa por vez.

## Qué contar en la presentación

- Las tres reglas: solo viajes completados, una calificación por viaje, el conductor sale de M6.
- Por qué el duplicado lo frena la base con un índice único y no un `if` en el código: si llegan dos pedidos al mismo tiempo, el `if` puede dejar pasar los dos (RNF-08, concurrencia).
- Demo: calificar, intentar de nuevo (`409`) e intentar con un viaje en curso (`422`).
