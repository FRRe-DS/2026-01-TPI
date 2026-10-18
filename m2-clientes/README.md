# Módulo 2 - Gestión de Clientes (TPI 2026)

Microservicio encargado del registro, almacenamiento y consulta de perfiles de clientes, direcciones y preferencias para la plataforma de movilidad.

## Cómo instalarlo y correrlo

Las instrucciones completas (requisitos, Keycloak, MongoDB, esta API y el front) están en el README principal:
**[../README.md → Cómo instalarlo y correrlo](../README.md#-cómo-instalarlo-y-correrlo-windows)**

Resumen para correr esta API, con Keycloak y MongoDB ya levantados:

```powershell
cd C:\Proyectos\2026-01-TPI\m2-clientes
.\venv\Scripts\Activate.ps1      # la primera vez: py -3.13 -m venv venv y pip install -r requirements.txt
uvicorn main:app --reload
```

Swagger: http://localhost:8000/docs

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.py` | Endpoints de la API y configuración de CORS |
| `models.py` | Modelos Pydantic: Cliente, Dirección y Preferencias |
| `database.py` | Conexión a MongoDB |
| `security.py` | Validación del token de Keycloak |
| `requirements.txt` | Librerías de Python (usar Python 3.12 o 3.13) |
| `docker-compose.yml` | MongoDB local |
