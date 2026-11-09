# T07 · Publicar las imágenes en GitHub Packages y levantar todo con un comando

| | |
|---|---|
| **Dificultad** | Media (es configuración de Docker y de GitHub Actions, con poco código) |
| **Depende de** | T01 para sumar el M6 simulado al compose |
| **Fecha objetivo** | PR abierto el lunes 16/11 |
| **Rama sugerida** | `feature/t07-publicar-imagenes` |

## Qué es y para qué sirve

La consigna pide que cada módulo se ejecute con **imágenes OCI reproducibles y versionadas** (RNF-04), y recomienda publicarlas con un pipeline automático (RNF-17). Ya tenemos los `Dockerfile` de la API y del front, pero cada uno tiene que construir las imágenes en su PC.

Esta tarea tiene dos partes:

1. **Publicar las imágenes** en GitHub Packages (GHCR) automáticamente cada vez que se actualiza `main`. Así los otros grupos pueden usar M2 con un `docker pull`, sin compilar nada.
2. **Un compose único** en la raíz del repo, para levantar **todo** con un solo comando: Keycloak, MongoDB, la API, el front y el M6 simulado.

Es como pasar de darle a alguien la receta a darle el plato listo en un táper.

## Lo que tenés que saber antes

- **Imagen y contenedor:** leé la sección 4 del PDF de cambios del 7/11 o el paso 8 del `README.md`.
- **Los Dockerfile:** `m2-clientes/Dockerfile` y `frontend/Dockerfile`. Ya tienen la etiqueta `org.opencontainers.image.source` que GitHub usa para vincular la imagen con el repo.
- **GitHub Actions:** mirá `.github/workflows/ci.yml`, que es el que corre las pruebas. El tuyo va a ser parecido.
- Las imágenes se van a llamar `ghcr.io/frre-ds/m2-clientes-api` y `ghcr.io/frre-ds/m2-clientes-front`.

## Pasos

### Parte 1: workflow de publicación (`.github/workflows/publicar.yml`)

1. Que corra con `push` a `main` y con tags `v*` (por ejemplo `v1.0.0`).
2. Que tenga `permissions: { contents: read, packages: write }`.
3. Que use estas acciones oficiales:
   - `docker/login-action`, con `registry: ghcr.io`, `username: ${{ github.actor }}` y `password: ${{ secrets.GITHUB_TOKEN }}`; no hace falta crear ningún secreto;
   - `docker/metadata-action`, para las etiquetas `latest`, el SHA del commit y la versión del tag;
   - `docker/build-push-action`, una vez por imagen (`context: m2-clientes` y `context: frontend`).
4. Probalo primero en tu rama: agregá tu rama a los disparadores, verificá en la pestaña Actions que publique, y después sacala.
5. **Después de la primera publicación:** la imagen queda privada. Alguien con permisos en la organización `FRRe-DS` (Lucas o el profe) tiene que ir a *Packages → m2-clientes-api → Package settings → Change visibility → Public*, para que los otros grupos la puedan bajar. Anotalo en el PR.

### Parte 2: compose único (`docker-compose.yml` en la raíz)

6. Un solo archivo con todos los servicios: `postgres` y `keycloak` (tomalos de `keycloak/docker-compose.yml`), `mongodb`, `api`, `front` y `m6-simulado`.
   - La API se conecta a `mongodb://mongodb:27017`, a Keycloak por `http://keycloak:8080/...` y a `M6_URL=http://m6-simulado:3000`.
   - El front se publica en el puerto `5173`, como hoy, para que Keycloak acepte la redirección.
   - Las variables sensibles se leen del `keycloak/.env` existente (`env_file`). Nada de contraseñas nuevas escritas en el compose.
   - `depends_on` con `condition: service_healthy` para que todo arranque en orden.
7. **Una trampa conocida:** el token que ve el navegador dice que lo emitió `http://localhost:8080`, pero adentro de Docker Keycloak se llama `keycloak`. La API solo baja las claves de `JWKS_URL` y no verifica el emisor (`JWT_ISSUER` vacío), así que funciona. Si algo falla con el token, empezá por ahí.
8. Agregá una sección al README: "Levantar todo con un comando".
9. **Ejemplo para otros grupos:** un archivo `docs/usar-m2.md` con un compose mínimo que use `image: ghcr.io/frre-ds/m2-clientes-api:latest` y explique qué variables configurar.

## Cómo probarlo

```powershell
cd C:\Proyectos\2026-01-TPI
docker compose up -d --build
docker ps        # todos "healthy" después de un minuto
```

Entrá a http://localhost:5173 y hacé el recorrido completo (login, perfil, historial).

## Terminado cuando

- [ ] Un push a `main` publica las dos imágenes en GHCR (se ven en la página del repo, a la derecha, en "Packages").
- [ ] `docker compose up -d --build` en la raíz levanta todo y el sistema funciona.
- [ ] No quedan secretos nuevos en el repo.
- [ ] README, `docs/usar-m2.md` y tablero actualizados.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea, `.github/workflows/ci.yml` y los dos `Dockerfile`. Necesito un workflow de GitHub Actions que publique dos imágenes en `ghcr.io/frre-ds/...` cuando se hace push a `main` o a un tag `v*`, usando `GITHUB_TOKEN`. Explicame primero qué es un registro de imágenes y qué hace cada acción (login, metadata, build-push). Después armemos el YAML y revisemos juntos los permisos.

## Qué contar en la presentación

- Qué son las imágenes y por qué la consigna pide publicarlas (RNF-04 y RNF-17).
- Cómo se publican solas y cómo otro grupo usa M2 sin compilar nada.
- Demo: levantar el sistema entero con un comando.
