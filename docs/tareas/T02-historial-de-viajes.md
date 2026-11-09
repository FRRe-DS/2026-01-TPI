# T02 · Historial de viajes del cliente, pedido a M6 (RF-2.4)

| | |
|---|---|
| **Dificultad** | Media |
| **Depende de** | T01 para probar a mano. Las pruebas automáticas no lo necesitan |
| **Destraba** | T03 usa tu función `obtener_viaje`; T04 muestra el historial en el front |
| **Fecha objetivo** | `integraciones/m6.py` mergeado el viernes 13/11; el endpoint, el lunes 16/11 |
| **Rama sugerida** | `feature/t02-historial` (y si querés, una primera rama solo para `m6.py`) |

## Qué es y para qué sirve

El cliente tiene que poder ver **sus viajes anteriores**. Esos datos los tiene M6, y la consigna dice que M2 los tiene que pedir **por la API de M6**, nunca leyendo su base (RNF-05). Tu tarea tiene dos partes:

1. **El conector a M6** (`integraciones/m6.py`): las funciones que le hacen los pedidos a M6. Si M6 no contesta, M2 no puede quedarse esperando para siempre: espera **2 segundos**, **reintenta una vez** y, si sigue sin respuesta, contesta **`503`** (servicio no disponible). Eso se llama **resiliencia** (RNF-13).
2. **El endpoint** `GET /api/v1/clientes/{clienteId}/viajes`, que usa el conector y transforma la respuesta de M6 al formato de nuestro contrato.

Es como un mozo: no cocina, le pide el plato a la cocina (M6). Si la cocina no contesta, después de un rato vuelve a preguntar una vez, y si tampoco, le avisa al cliente en vez de dejarlo esperando.

## Lo que tenés que saber antes

- **Nuestro contrato:** en `contratos/m2_clientes/openapi.yml` buscá `listarHistorialViajes` y los esquemas `ViajeResumen` y `PaginaViajes`. Esa es la respuesta que tenés que devolver.
- **El contrato de M6:** `GET /trips` y `GET /trips/{tripId}` (resumidos en la guía de [T01](T01-m6-simulado.md)).
- **Modelos para copiar:**
  - `m2-clientes/rutas/direcciones.py`: cómo es un endpoint con roles, dueño, perfil y paginación;
  - `m2-clientes/tests/test_direcciones.py`: cómo se prueba.
- **Reglas del proyecto:** leé en `AGENTS.md` la parte "Datos de otros módulos, solo por su API".

## Pasos

### Parte 1: el conector (`m2-clientes/integraciones/m6.py`)

1. En `config.py` agregá `M6_URL` (por defecto `http://localhost:3000`) y `M6_TIMEOUT_SEGUNDOS` (por defecto `2`). Sumalas también a `.env.example`.
2. Hace falta la librería `httpx` en `requirements.txt` (ya está en `requirements-dev.txt`, con la versión `0.28.1`). **Pedile el OK a Lucas** antes de agregarla.
3. Creá `m2-clientes/integraciones/__init__.py` (vacío) y `m2-clientes/integraciones/m6.py` con dos funciones. Respetá exactamente estos nombres, porque T03 los va a usar:
   ```python
   def listar_viajes(cliente_id: str, page: int, size: int, autorizacion: str) -> dict:
       """GET /trips de M6. page empieza en 0 (como en M2): a M6 se le manda page + 1."""

   def obtener_viaje(viaje_id: str, autorizacion: str) -> dict | None:
       """GET /trips/{id} de M6. Devuelve None si M6 responde 404."""
   ```
   `autorizacion` es el encabezado `Authorization` que llegó a M2 (`"Bearer ..."`). Por ahora se le reenvía igual a M6.
4. **Resiliencia:**
   - timeout de 2 segundos por intento;
   - si hay timeout, error de conexión o un `5xx`, se reintenta **una sola vez**;
   - si vuelve a fallar, se lanza un `ErrorDominio(503, "/errores/dependencia-no-disponible", "M6 no está disponible", "...")`.
5. El contrato pide `Retry-After` también en ese `503`. Hoy `ErrorDominio` no lleva encabezados: agregale un parámetro opcional `headers` y que `manejar_dominio`, en `errores.py`, lo pase a `problema(...)`.

### Parte 2: el endpoint (`m2-clientes/rutas/historial.py`)

6. Copiá la estructura de `listar_direcciones`:
   - roles `CLIENTE` y `OPERADOR`;
   - `verificar_dueno`;
   - `buscar_perfil_o_404`;
   - `page` y `size`.
7. Para reenviar el token, recibí el `Request` de FastAPI y tomá `request.headers["Authorization"]`.
8. Transformá cada `TripSummary` de M6 en un `ViajeResumen`:

   | M6 (`TripSummary`) | M2 (`ViajeResumen`) |
   |---|---|
   | `id` | `viajeId` |
   | `state` | `estado` (sin traducir) |
   | `vehicleType`: `CAR` / `MOTORCYCLE` | `tipoVehiculo`: `AUTO` / `MOTO` |
   | `originAddress` / `destinationAddress` | `origen` / `destino` |
   | `createdAt` / `completedAt` | `iniciadoEn` / `finalizadoEn` (si `completedAt` es null, no se manda) |
   | `driverId` | `conductorId` |
   | — | `calificado`: `true` si existe una calificación del cliente para ese viaje (colección de T03). Hasta que T03 esté, `false` |

9. Paginación:
   - `page` de M2 = `page` de M6 − 1;
   - `totalElementos` = `total` de M6;
   - `totalPaginas` = `ceil(total / size)`.
10. Registrá el router en `main.py`.

### Pruebas

11. `tests/test_historial.py`:
    - En las pruebas del endpoint, reemplazá `integraciones.m6.listar_viajes` con `monkeypatch` por una función que devuelva datos fijos. Así no hace falta M6.
    - Validá la respuesta con `validar("PaginaViajes", cuerpo)`.
    - Probá: cliente dueño `200`, cliente ajeno `403`, operador `200`, sin perfil `404`, M6 caído `503` con `Retry-After`, y conversión de página y vehículo.
12. Pruebas unitarias de `m6.py` con `httpx.MockTransport` (viene con httpx): que reintente una vez, que dé `503` después de dos fallas, que devuelva `None` con un `404` y que sume 1 a la página.
13. Agregá `listarHistorialViajes` al `test_codigos_usados_estan_en_el_contrato` de tu archivo.

## Cómo probarlo a mano

1. Levantá todo como siempre, más el M6 simulado de T01 en el puerto 3000.
2. Con el token de un cliente (desde el front) o de operador (paso 6 del README), probá en Swagger `GET /api/v1/clientes/{clienteId}/viajes`.
3. Cortá el M6 simulado y repetí: tiene que tardar unos 4 segundos y responder `503`.

## Terminado cuando

- [ ] `obtener_viaje` y `listar_viajes` existen con esos nombres (T03 depende de eso).
- [ ] El endpoint devuelve el formato `PaginaViajes` del contrato.
- [ ] Con M6 caído o lento responde `503` con `Retry-After`, y nunca espera más de 2 intentos.
- [ ] Las pruebas nuevas pasan, y también las 214 que ya estaban.
- [ ] README de `m2-clientes` actualizado (endpoint y variable `M6_URL`) y tablero al día.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto (una API en FastAPI), la guía de mi tarea y el archivo `rutas/direcciones.py` como modelo. Tengo que hacer `integraciones/m6.py` con httpx (timeout de 2 s, un reintento, 503 si falla) y el endpoint `GET /api/v1/clientes/{clienteId}/viajes` en `rutas/historial.py`, que transforma la respuesta de M6 al esquema `ViajeResumen` del contrato. Empezá explicándome qué es un timeout y un reintento y por qué hacen falta. Después hacelo por partes: primero `m6.py` con sus pruebas usando `httpx.MockTransport`, y cuando funcione, el endpoint con pruebas que usen `monkeypatch`.

## Qué contar en la presentación

- Por qué M2 no lee la base de M6 (RNF-05) y le pregunta por su API.
- Qué pasa si M6 no responde: 2 segundos, un reintento, `503`. Mostrarlo en vivo cortando el M6 simulado.
- Cómo se traducen los datos de M6 a nuestro contrato (la tabla de arriba).
