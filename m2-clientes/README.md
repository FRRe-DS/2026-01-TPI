# Módulo 2 - Gestión de Clientes (TPI 2026)

Microservicio encargado del registro, almacenamiento y consulta de perfiles de clientes, direcciones y preferencias para la plataforma de movilidad.

## Tecnologías Utilizadas
- **Backend:** Python con FastAPI
- **Validación de Datos:** Pydantic (con validación de correos electrónicos)
- **Base de Datos:** MongoDB (ejecutado mediante contenedor Docker)
- **Documentación Automática:** Swagger UI (integrada por FastAPI)

---

## Guía de Inicio Rápido para el Equipo

Si deseas levantar este módulo en tu entorno local, sigue estos pasos:

### 1. Levantar la Base de Datos (Docker)
Asegúrate de tener Docker abierto y ejecuta en la raíz de este módulo:
`docker compose up -d`

### 2. Configurar el Entorno Virtual de Python
Crea y activa tu entorno virtual aislado:
`python -m venv venv`
`.\venv\Scripts\activate`

### 3. Instalar Dependencias
Carga las librerías necesarias especificadas en la receta del proyecto:
`pip install -r requirements.txt`

### 4. Iniciar el Servidor de Desarrollo
`uvicorn main:app --reload`

Una vez activo, ingresa a tu navegador en `http://localhost:8000/docs` para ver y probar la interfaz interactiva de Swagger.

---

## Endpoints Disponibles
- **`POST /api/v1/clientes`**: Registra un nuevo cliente con sus direcciones y preferencias en MongoDB.
- **`GET /api/v1/clientes`**: Devuelve la lista completa de clientes registrados.
- **`GET /api/v1/clientes/{id_mongo}`**: Consulta el perfil detallado de un cliente específico mediante su identificador único.