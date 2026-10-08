# Plataforma de Movilidad Urbana - Módulo M2: Clientes

**Trabajo Práctico Integrador 2026**  
**Institución:** Universidad Tecnológica Nacional – Facultad Regional Resistencia (UTN FRRe)  
**Cátedra:** Desarrollo de Software  

---

## 👥 Equipo Integrador
*   **Sonza, Matias Javier** - Legajo: 26573
*   *[Nombre del Integrante 2]* - Legajo: *[Legajo 2]*
*   *[Nombre del Integrante 3]* - Legajo: *[Legajo 3]*

---

## 🎯 Descripción del Módulo

El **Módulo M2: Clientes** es un microservicio autónomo responsable de la gestión integral de los usuarios pasajeros de la plataforma. 

*   **RF-2.1 / RF-2.6:** Gestión del ciclo de vida del perfil del cliente, su estado de cuenta y bloqueos administrativos.
*   **RF-2.2 / RF-2.3:** Administración de direcciones frecuentes y preferencias de viaje (tipo de vehículo, accesibilidad).
*   **RF-2.4:** Consulta de historial de viajes resumido (construido de forma asíncrona mediante eventos).
*   **RF-2.5:** Registro idempotente de calificaciones hacia los conductores, previniendo duplicidad de datos.

---

## 🏗️ Arquitectura y Stack Tecnológico

La solución fue diseñada siguiendo la metodología **12-Factor App**, garantizando alta portabilidad, escalabilidad y una clara separación entre el código y la configuración (RNF-06).

*   **Lenguaje y Framework:** Python 3.12+ con **FastAPI** (asíncrono, rápido y con validación Pydantic nativa).
*   **Persistencia Políglota:**
    *   **MySQL:** Almacenamiento relacional estructurado y transaccional para perfiles y estados de cuenta.
    *   **MongoDB:** Almacenamiento documental flexible para preferencias y direcciones (JSON schema).
*   **Mensajería Asíncrona:** **RabbitMQ** para la ingesta de eventos de dominio (ej. `ViajeFinalizado` emitido por M6) sin generar acoplamiento temporal.
*   **Caché:** **Redis** para optimizar la lectura frecuente de datos de perfil, reduciendo la latencia en integraciones con M5 (Despacho) y M9 (Reservas).
*   **Contenedorización:** Imágenes OCI versionadas mediante **Docker** y orquestadas con `docker-compose`.
