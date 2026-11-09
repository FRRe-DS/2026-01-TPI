# T01 · M6 simulado: una mini API que devuelve viajes de ejemplo

| | |
|---|---|
| **Dificultad** | Fácil |
| **Depende de** | Nada: se puede empezar ya |
| **Destraba** | T02, T03 y T04: sin esto no se pueden probar a mano |
| **Fecha objetivo** | Mergeada el viernes 13/11 |
| **Rama sugerida** | `feature/t01-m6-simulado` |

## Qué es y para qué sirve

M2 tiene que mostrar el **historial de viajes** del cliente y dejarlo **calificar al conductor** de un viaje terminado. Esos datos no son nuestros: los tiene **M6 (Viajes)**, que hacen los grupos 5 y 12. Todavía no tenemos su sistema corriendo, así que vamos a hacer un **M6 de mentira**: una API chiquita que responde igual que M6, con viajes inventados.

Es lo mismo que usar un maniquí para probar ropa: no es una persona, pero tiene la forma justa para probar si la ropa calza.

## Lo que tenés que saber antes

- **Qué es una API:** un programa que recibe pedidos por HTTP (por ejemplo `GET /trips`) y responde con datos en JSON. Pedile a la IA que te lo explique con un ejemplo si no lo tenés claro.
- **Qué responde M6:** está en su contrato, `contratos/m6_viajes/openapi.yml` del repo de la cátedra (https://github.com/FRRe-DS/2026-TPI). Lo que nos importa:
  - `GET /trips?clientId=...&page=1&pageSize=20`: devuelve `{"items": [...], "page": 1, "pageSize": 20, "total": N}`. Cada item es un `TripSummary`: `id`, `state`, `vehicleType`, `clientId`, `driverId`, `originAddress`, `destinationAddress`, `createdAt`, `completedAt`.
  - `GET /trips/{tripId}`: devuelve un `Trip` con `id`, `state`, `clientId`, `driverId` y más datos, o `404` si no existe.
  - Los estados (`state`) son `PENDING_ARRIVAL`, `DRIVER_ARRIVED`, `IN_PROGRESS`, `COMPLETED` y `CANCELLED`. Los vehículos (`vehicleType`), `CAR` y `MOTORCYCLE`.
  - **Ojo: en M6 las páginas empiezan en 1**, no en 0 como en M2.
- **Modelo para copiar:** la API de M2 también está hecha con FastAPI. Mirá `m2-clientes/main.py` y `m2-clientes/rutas/salud.py`, que son cortos.

## Pasos

1. Creá la carpeta `mocks/m6/` en la raíz del repo, con:
   - `main.py`: la app de FastAPI;
   - `requirements.txt`: solo `fastapi` y `uvicorn`, con las mismas versiones que `m2-clientes/requirements.txt`;
   - `README.md`: qué es y cómo se corre.
2. Hacé estos endpoints:
   - `GET /health` → `{"status": "UP"}`.
   - `GET /trips` con los parámetros `clientId`, `state` (opcional), `page` (desde 1) y `pageSize` (máximo 100).
   - `GET /trips/{tripId}`: si no existe, `404` con un cuerpo `application/problem+json`, por ejemplo `{"type": "about:blank", "title": "Not Found", "status": 404}`.
3. **Los datos de ejemplo:** para cualquier `clientId` que te pidan, devolvé siempre los mismos 6 viajes:
   - 3 `COMPLETED`, 1 `IN_PROGRESS`, 1 `CANCELLED` y 1 `COMPLETED` en moto;
   - con direcciones de Resistencia y fechas de los últimos días.

   Para que siempre sean los mismos, generá los `id` con `uuid.uuid5(uuid.NAMESPACE_URL, f"{clientId}-{n}")`. Guardalos en un diccionario en memoria, así después `GET /trips/{tripId}` los encuentra.
4. **Para probar errores**, que lea dos variables de entorno:
   - `DEMORA_SEGUNDOS` (por defecto 0): espera ese tiempo antes de responder. Sirve para ver qué hace M2 cuando M6 tarda (M2 espera solo 2 segundos).
   - `FALLAR` (por defecto vacío): si vale `si`, todas las respuestas son `500`.
5. Que corra en el **puerto 3000**, el que usa el Grupo 5 para M6.
6. Sumá un `Dockerfile` en `mocks/m6/`, copiando la idea de `m2-clientes/Dockerfile`, y agregá el servicio al `m2-clientes/docker-compose.yml` dentro del perfil `api`:
   ```yaml
     m6-simulado:
       profiles: ["api"]
       build: ../mocks/m6
       ports:
         - "3000:3000"
   ```

## Cómo probarlo

```powershell
cd C:\Proyectos\2026-01-TPI\mocks\m6
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --port 3000 --reload
```

Abrí http://localhost:3000/docs y probá `GET /trips` con cualquier UUID como `clientId`. Después copiá un `id` de la respuesta y probá `GET /trips/{tripId}`.

Con `$env:DEMORA_SEGUNDOS=5` antes de `uvicorn`, cada respuesta tarda 5 segundos.

## Terminado cuando

- [ ] `GET /trips?clientId=<uuid>` devuelve 6 viajes, siempre los mismos para el mismo cliente.
- [ ] La paginación funciona: `page=2&pageSize=4` devuelve los 2 últimos.
- [ ] `GET /trips/{id}` devuelve el viaje, y `404` si el id no existe.
- [ ] `DEMORA_SEGUNDOS` y `FALLAR` funcionan.
- [ ] Corre con `docker compose --profile api up -d --build` desde `m2-clientes`.
- [ ] El `README.md` de `mocks/m6/` explica cómo se usa.
- [ ] Actualizaste el tablero (`docs/tareas/README.md`).

## Prompt para la IA

> Estoy en un proyecto de la facultad. Te paso el `AGENTS.md` del proyecto y la guía de mi tarea. Necesito hacer un "M6 simulado" con FastAPI en `mocks/m6/main.py`, que responda `GET /health`, `GET /trips` y `GET /trips/{tripId}` como dice la guía, con datos de ejemplo generados con uuid5 y guardados en memoria. Explicame primero cómo lo vas a armar, después escribí el código paso a paso y explicame cada parte como para alguien que recién empieza. No agregues librerías además de fastapi y uvicorn.

## Qué contar en la presentación

- Por qué hace falta un simulador: M6 es de otro grupo y todavía no está disponible.
- Qué endpoints imita y de dónde salen (el contrato de M6).
- Cómo se usa para probar los errores: que M6 tarde o que falle, y qué hace M2 en esos casos (lo cuenta T02).
