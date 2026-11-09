# Tareas del equipo hasta la presentación (jueves 19/11)

Este es el **tablero** de lo que falta de M2 y quién lo hace. Cada tarea tiene su guía en esta carpeta, escrita para alguien que recién empieza y que se va a ayudar con IA.

**Antes de arrancar una tarea:** hacé la [guía de primeros pasos](../primeros-pasos.md). Si no podés levantar el sistema en tu PC, no vas a poder probar lo que hagas.

> Cuando cambie algo (quién la tiene, en qué estado está, el número de PR), actualizá esta tabla en el mismo PR de la tarea. Así este archivo es siempre el registro de quién hizo qué.

## Tablero

| # | Tarea | Dificultad | Depende de | Responsable | Estado | PR |
|---|---|---|---|---|---|---|
| [T01](T01-m6-simulado.md) | M6 simulado: una mini API que devuelve viajes de ejemplo | Fácil | — | _a definir_ | Pendiente | |
| [T02](T02-historial-de-viajes.md) | Historial de viajes del cliente, pedido a M6 (RF-2.4) | Media | T01 para probar a mano | _a definir_ | Pendiente | |
| [T03](T03-calificaciones.md) | Calificar al conductor después de un viaje (RF-2.5) | Media | T02 (función `obtener_viaje`) | _a definir_ | Pendiente | |
| [T04](T04-front-historial-y-calificaciones.md) | Front: historial de viajes y botón "Calificar" | Media | T02 y T03 | _a definir_ | Pendiente | |
| [T05](T05-front-panel-operador.md) | Front: panel del operador (ver un cliente, bloquear y levantar) | Fácil-media | T06 (usuario operador) | _a definir_ | Pendiente | |
| [T06](T06-keycloak-usuarios-y-roles.md) | Keycloak listo para usar: roles, usuarios de prueba y cliente del front | Fácil | — | _a definir_ | Pendiente | |
| [T07](T07-publicar-imagenes-y-compose.md) | Publicar las imágenes en GitHub Packages y levantar todo con un comando | Media | T01 | _a definir_ | Pendiente | |
| [T08](T08-datos-demo-y-presentacion.md) | Datos de demo, diagramas y armado de la presentación | Fácil | Todas (para la presentación) | _a definir_ | Pendiente | |
| [L1](L1-scopes-e-idempotencia.md) | Scopes y audiencia (con el Grupo 17) e idempotencia (etapa 5) | Difícil | — | Lucas | En curso (scopes listos; falta idempotencia) | |
| [L2](L1-scopes-e-idempotencia.md) | Revisar los PR, coordinar con otros grupos y pasar todo a `main` | — | Todas | Lucas | Pendiente | |

Estados posibles: **Pendiente** → **En curso** → **PR abierto** → **Mergeado**.

Si el equipo prefiere usar issues de GitHub para asignar las tareas (y que GitHub avise a cada uno), `crear-issues.ps1` los crea todos de una vez, con GitHub CLI. Es opcional: este tablero sigue siendo el registro.

## Calendario

Las fechas son **tentativas** y se pueden ajustar según cómo avancemos. La única fija es la de la **presentación, el jueves 19/11**.

| Fecha | Qué tiene que estar |
|---|---|
| Lun 9/11 | Reunión de arranque: Lucas muestra el sistema funcionando y se reparten las tareas. |
| Mié 11/11 | Cada uno tiene el sistema corriendo en su PC ([primeros pasos](../primeros-pasos.md)) y leyó la guía de su tarea. |
| Vie 13/11 | **T01**, **T06** y la función `obtener_viaje` de **T02** mergeadas: las demás tareas dependen de ellas. |
| Lun 16/11 | Todas las tareas con el PR abierto y el CI en verde. |
| Mar 17/11 | Todo mergeado en `desarrollo-m2`. Prueba completa del sistema entre todos. |
| Mié 18/11 | `desarrollo-m2` pasa a `main`. Ensayo de la presentación. |
| **Jue 19/11** | **Presentación.** |

Si te trabás más de un día con algo, avisá en el grupo: es preferible pedir ayuda temprano que llegar al 17 sin nada.

## Cómo se trabaja cada tarea

1. **Rama propia** desde `desarrollo-m2`, desde la raíz del repo:
   ```powershell
   git switch desarrollo-m2
   git pull
   git switch -c feature/t01-m6-simulado     # usá el número y el nombre de tu tarea
   ```
2. **Commits chicos** a medida que avanzás (`git add -A`, `git commit -m "..."`, `git push`).
3. **Pruebas:** `python -m pytest` en `m2-clientes` (y `npm run build` en `frontend` si tocaste el front) tienen que pasar antes de abrir el PR.
4. **PR hacia `desarrollo-m2`.** En la descripción contá qué hiciste y cómo se prueba. Lucas lo revisa.

   > **⚠️ Revisá la base del PR.** GitHub propone `main` por defecto. Antes de tocar "Create pull request", cambiá arriba la **base** a `desarrollo-m2` (tiene que decir `base: desarrollo-m2 ← compare: tu-rama`). Si el PR ya está abierto con base `main`, no lo mergees: tocá **Edit** al lado del título y cambiá la base.

5. **El CI tiene que estar en verde** (los tildes al final del PR). Si está en rojo, abrí el detalle en la pestaña Actions, arreglalo y volvé a hacer push.
6. Se mergea con **"Create a merge commit"**.
7. Actualizá esta tabla (estado y número de PR).

## Cómo usar la IA para tu tarea

La IA te puede ahorrar mucho trabajo, pero **en la presentación te van a preguntar qué hiciste y cómo**. La idea es que la uses para entender y para avanzar más rápido, no para entregar algo que no podés explicar.

- **Dale contexto antes de pedirle código.** Pasale tres cosas:
  1. el archivo [`AGENTS.md`](../../AGENTS.md) de la raíz, que explica cómo está hecho el proyecto y sus reglas;
  2. la guía de tu tarea;
  3. el archivo que la guía te indica como modelo.

  Si usás una herramienta que trabaja dentro del repo (Claude Code, Cursor, Copilot, Codex), lee `AGENTS.md` sola.
- **Pedile primero que te explique, después que escriba.** Por ejemplo: *"Explicame qué hace `rutas/direcciones.py`, función por función, como para alguien que recién empieza"*.
- **Pedile las pruebas junto con el código,** y corrélas vos.
- **Si algo falla, pegale el error completo,** no un resumen.
- **No le pegues contraseñas, tokens ni el contenido de archivos `.env`.**
- **Antes del PR, preguntale:** *"¿Esto respeta el contrato `contratos/m2_clientes/openapi.yml` y las reglas de `AGENTS.md`?"*

Cada guía tiene al final un **prompt listo para copiar** y una sección **"Qué contar en la presentación"**.

## Reglas que no se rompen

- **El contrato no se cambia** para que coincida con el código. Si tu tarea necesita algo que el contrato no tiene, avisale a Lucas: el contrato se comparte con el Grupo 17.
- **Nada de secretos nuevos en el repo** (contraseñas, tokens, claves).
- **No se lee la base de otro módulo:** a M6 se le pregunta por su API.
- **Nada de push directo a `main`.**
- **Para agregar una librería** (Python o npm), preguntale antes a Lucas.
