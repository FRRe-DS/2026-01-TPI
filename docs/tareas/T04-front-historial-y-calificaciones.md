# T04 · Front: historial de viajes y botón "Calificar"

| | |
|---|---|
| **Dificultad** | Media |
| **Depende de** | T02 (endpoint de historial) y T03 (calificaciones). Para empezar no hace falta esperarlos: podés armar la pantalla con datos de ejemplo |
| **Fecha objetivo** | PR abierto el lunes 16/11 |
| **Rama sugerida** | `feature/t04-front-historial` |

## Qué es y para qué sirve

Hoy el front muestra el perfil, las direcciones y las preferencias del cliente. Falta que pueda **ver sus viajes** y **calificar al conductor** de los que terminaron. Es la parte visible de T02 y T03: lo que se muestra en la demo.

## Lo que tenés que saber antes

- **El front** está hecho con React y una librería de componentes llamada Mantine (https://mantine.dev).
- **Modelo para copiar:** `frontend/src/components/DireccionesCard.jsx`. Es una tarjeta con lista paginada, un modal para cargar datos y avisos de error. La tuya va a ser muy parecida.
- **Todas las llamadas a la API** van en `frontend/src/api.js`. Mirá cómo están hechas `listarDirecciones` y `crearDireccion`; esta última manda `Idempotency-Key` con `crypto.randomUUID()`.
- **Lo que devuelve la API:** `ViajeResumen` y `Calificacion` en el contrato (`contratos/m2_clientes/openapi.yml`), y las guías de [T02](T02-historial-de-viajes.md) y [T03](T03-calificaciones.md).

## Pasos

1. En `api.js`, agregá:
   - `listarViajes(clienteId, { page, size })` → `GET /api/v1/clientes/{clienteId}/viajes`;
   - `calificarConductor(clienteId, { viajeId, puntaje, comentario })` → `POST .../calificaciones` con `Idempotency-Key`;
   - `listarCalificaciones(clienteId, { page, size })` → `GET .../calificaciones`.
2. Creá `components/HistorialCard.jsx`:
   - una lista paginada de viajes (5 por página), las más nuevas primero;
   - por cada viaje: fecha, origen → destino, auto o moto y el estado con un `Badge` de color (verde COMPLETED, gris CANCELLED, azul IN_PROGRESS);
   - si el viaje está `COMPLETED` y `calificado` es `false`, un botón **"Calificar"**. Si ya está calificado, un texto "Ya calificaste este viaje".
3. El botón abre un `Modal` con:
   - el componente `Rating` de Mantine (1 a 5 estrellas);
   - un `Textarea` para el comentario, de hasta 500 caracteres;
   - el botón "Enviar".

   Al guardar, mostrá una notificación verde y recargá la lista, así el viaje pasa a "Ya calificaste".
4. **Manejo de errores** (con `e.status` de `ErrorApi`):
   - `503`: "El servicio de viajes no responde. Probá de nuevo en un rato." Es esperable, porque depende de M6.
   - `409`: "Ya calificaste este viaje."
   - `422`: "Solo se pueden calificar viajes terminados."
5. **Estado vacío:** si no hay viajes, un texto amable ("Todavía no hiciste viajes").
6. Agregá la tarjeta en `App.jsx`, debajo de las preferencias, solo cuando el cliente ya tiene perfil (como las otras tarjetas).
7. Si querés, una sección "Mis calificaciones" con `listarCalificaciones`: puntaje, comentario y fecha.

## Cómo probarlo

1. Levantá Keycloak, MongoDB, la API (con T02 y T03 mergeados o en tu rama), el M6 simulado de T01 y el front.
2. Entrá con `cliente-demo`: tienen que aparecer los 6 viajes de ejemplo.
3. Calificá uno terminado. El botón tiene que desaparecer.
4. Cortá el M6 simulado y recargá: tiene que salir el aviso del `503`, sin que la página se rompa.
5. `npm run build` tiene que terminar sin errores.

## Terminado cuando

- [ ] Se ven los viajes, paginados.
- [ ] Se puede calificar un viaje terminado, una sola vez.
- [ ] Los errores `503`, `409` y `422` muestran un mensaje claro.
- [ ] `npm run build` funciona y el CI está en verde.
- [ ] Hay captura de pantalla en el PR, y `frontend/README.md` y el tablero están actualizados.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea, `frontend/src/api.js` y `frontend/src/components/DireccionesCard.jsx` como modelo. Necesito un componente `HistorialCard.jsx` en React + Mantine que liste los viajes del cliente con paginación y tenga un botón "Calificar" que abra un modal con el componente `Rating`. Explicame primero cómo funciona `DireccionesCard.jsx` (`useState`, `useEffect` y cómo llama a la API). Después armemos el componente por partes: primero la lista, después el modal y al final los errores.

## Qué contar en la presentación

- Cómo el front habla con la API (`api.js`) y por qué todas las llamadas pasan por ahí.
- Qué ve el usuario cuando todo anda y qué ve cuando M6 no responde.
- Demo: ver los viajes y calificar uno.
