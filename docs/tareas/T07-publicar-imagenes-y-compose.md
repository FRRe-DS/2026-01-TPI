# T07 · Levantar todo con un comando

| | |
|---|---|
| **Dificultad** | Media (es configuración de Docker, con poco código) |
| **Depende de** | T01 para sumar el M6 simulado al compose |
| **Rama sugerida** | `feature/t07-compose` |

## Qué es y para qué sirve

La consigna pide que cada módulo se ejecute con **imágenes OCI reproducibles y versionadas** (RNF-04) y que eso se automatice (RNF-17). Esta tarea tenía dos partes:

1. ✔ **Publicar la imagen de la API** en GitHub Packages (GHCR). **Ya está hecha:** la hizo Joaquín Bregant, alumno de la materia DevOps que nos ayuda con el deploy (PR #20 y #23, `.github/workflows/publicar.yml`). Cuando el CI pasa en verde después de un push a `desarrollo-m2` o `main`, se publica `ghcr.io/frre-ds/2026-01-tpi-api`; ese nombre es la convención de todos los grupos (`<repo>-api`). El paquete ya es público. El front no se publica (Joaquín no lo necesita; si hace falta, se le pide).
2. **Un compose único** en la raíz del repo, para levantar **todo** con un solo comando: Keycloak, MongoDB, la API, el front y el M6 simulado. **Esto es lo que falta.**

Es como pasar de darle a alguien la receta a darle el plato listo en un táper.

> **No hace falta coordinarlo con Joaquín:** el compose es para nosotros (desarrollo, pruebas y la demo). Para el deploy, DevOps va a usar su propio compose que levanta todos los módulos juntos, con nuestra imagen publicada.

## Lo que tenés que saber antes

- **Imagen y contenedor:** leé la sección 4 del PDF de cambios del 7/11 o el paso 8 del `README.md`.
- **Los Dockerfile:** `m2-clientes/Dockerfile` y `frontend/Dockerfile`.
- **El compose que ya existe:** `m2-clientes/docker-compose.yml` levanta MongoDB y, con `--profile api`, la API. El tuyo junta eso con el de `keycloak/`.
- **Cómo se publica la API:** mirá `.github/workflows/publicar.yml`. Corre cuando termina el CI en verde (`workflow_run`), solo para pushes de este repo. Las etiquetas son la rama (`desarrollo-m2`, `main`), `sha-xxxxxxx` y `latest` (solo desde `main`). El front no se publica.

## Pasos

1. Un solo archivo, `docker-compose.yml` en la raíz, con todos los servicios: `postgres` y `keycloak` (tomalos de `keycloak/docker-compose.yml`), `mongodb`, `api`, `front` y `m6-simulado`.
   - La API se construye con `build: ./m2-clientes`, o usa la imagen publicada `ghcr.io/frre-ds/2026-01-tpi-api:desarrollo-m2`.
   - La API se conecta a `mongodb://mongodb:27017`, a Keycloak por `http://keycloak:8080/...` y a `M6_URL=http://m6-simulado:3000`.
   - El front se publica en el puerto `5173`, como hoy, para que Keycloak acepte la redirección.
   - Las variables sensibles se leen del `keycloak/.env` existente (`env_file`). Nada de contraseñas nuevas escritas en el compose.
   - `depends_on` con `condition: service_healthy` para que todo arranque en orden.
2. **Una trampa conocida:** el token que ve el navegador dice que lo emitió `http://localhost:8080`, pero adentro de Docker Keycloak se llama `keycloak`. La API solo baja las claves de `JWKS_URL` y no verifica el emisor (`JWT_ISSUER` vacío), así que funciona. Si algo falla con el token, empezá por ahí.
3. Agregá una sección al README: "Levantar todo con un comando".
4. **Ejemplo para otros grupos:** un archivo `docs/usar-m2.md` con un compose mínimo que use `image: ghcr.io/frre-ds/2026-01-tpi-api:main` y explique qué variables configurar (las de `m2-clientes/.env.example`).

## Cómo probarlo

```powershell
cd C:\Proyectos\2026-01-TPI
docker compose up -d --build
docker ps        # todos "healthy" después de un minuto
```

Entrá a http://localhost:5173 y hacé el recorrido completo (login, perfil, historial).

## Terminado cuando

- [x] Un push publica la imagen de la API en GHCR cuando el CI pasa (PR #20 y #23, Joaquín). El paquete es público.
- [ ] `docker compose up -d --build` en la raíz levanta todo y el sistema funciona.
- [ ] No quedan secretos nuevos en el repo.
- [ ] README, `docs/usar-m2.md` y tablero actualizados.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea, `keycloak/docker-compose.yml`, `m2-clientes/docker-compose.yml` y los dos `Dockerfile`. Necesito un `docker-compose.yml` en la raíz que levante Keycloak (con su Postgres), MongoDB, la API, el front y el M6 simulado, con healthchecks y `depends_on`, leyendo las credenciales de `keycloak/.env`. Explicame primero cómo se comunican los contenedores entre sí (redes y nombres de servicio) y por qué adentro de Docker no sirve `localhost`. Después armemos el archivo.

## Qué contar en la presentación

- Qué son las imágenes y por qué la consigna pide publicarlas (RNF-04 y RNF-17).
- Cómo se publica sola la imagen cuando pasan las pruebas (el workflow de Joaquín) y cómo otro grupo usa M2 sin compilar nada.
- Demo: levantar el sistema entero con un comando.
