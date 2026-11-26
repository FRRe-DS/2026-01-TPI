
# M6 Simulado – Viajes

## Descripción

Este proyecto implementa una API simulada del módulo M6 (Viajes) utilizando FastAPI.

Su objetivo es permitir que el módulo M2 (Clientes) pueda desarrollar y probar las funcionalidades de historial y consulta de viajes sin depender de que el módulo M6 real esté disponible.

El simulador genera seis viajes ficticios por cliente, con identificadores estables y diferentes estados y tipos de vehículo.

También permite simular demoras y errores del servidor para comprobar cómo responde M2 ante problemas de comunicación.


## Cómo ejecutar el simulador

### 1. Ubicarse en la carpeta del simulador

Desde la carpeta principal del proyecto:

```powershell
cd mocks/m6
```

### 2. Instalar las dependencias

Se necesita Python 3.13.

```powershell
python -m pip install -r requirements.txt
```

### 3. Iniciar el servidor

```powershell
python -m uvicorn main:app --port 3000 --reload
```

### 4. Consultar la API

Una vez iniciado el servidor, se puede acceder a:

- Documentación Swagger: http://127.0.0.1:3000/docs
- Estado del servicio: http://127.0.0.1:3000/health

El simulador utiliza el puerto 3000.


## Endpoints disponibles

### GET /health

Permite comprobar si el simulador está funcionando.

Respuesta normal:

```json
{
  "status": "UP"
}
```

### GET /trips

Devuelve una lista de seis viajes ficticios para el cliente indicado.

Parámetros:
- `clientId`: identificador UUID del cliente (obligatorio).
- `state`: permite filtrar los viajes por estado (opcional).
- `page`: número de página, comienza en 1.
- `pageSize`: cantidad de viajes por página, máximo 100.

Ejemplo:

`GET /trips?clientId=11111111-1111-4111-8111-111111111111&page=2&pageSize=4`

La respuesta contiene `items`, `page`, `pageSize` y `total`.

### GET /trips/{tripId}

Permite consultar un viaje específico mediante su identificador UUID.

Si el viaje existe, devuelve sus datos.

Si no existe, devuelve un error HTTP 404 con formato `application/problem+json`.


## Simulación de errores y demoras

El simulador permite probar cómo responde M2 cuando M6 presenta problemas.

Para configurar estos comportamientos se utilizan dos variables de entorno:

### DEMORA_SEGUNDOS

Indica cuántos segundos debe esperar el simulador antes de responder.

Por defecto, su valor es 0 (sin demora).

Ejemplo en PowerShell:

    $env:DEMORA_SEGUNDOS="5"

Con esta configuración, las respuestas tardarán aproximadamente 5 segundos.

### FALLAR

Permite simular un error del servidor.

Por defecto, está desactivada.

Ejemplo en PowerShell:

    $env:FALLAR="si"

Con esta configuración, los endpoints devuelven un error HTTP 500.

### Volver al funcionamiento normal

Para desactivar ambas simulaciones:

    $env:DEMORA_SEGUNDOS="0"
    $env:FALLAR=""

Las variables deben configurarse antes de iniciar el servidor. Si ya está funcionando, es necesario detenerlo y volver a iniciarlo.
