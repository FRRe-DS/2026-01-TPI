# T05 · Front: panel del operador (ver un cliente, bloquear y levantar)

| | |
|---|---|
| **Dificultad** | Fácil-media |
| **Depende de** | T06 (un usuario `operador-demo` en Keycloak). Mientras tanto, se puede crear a mano en tu Keycloak |
| **Fecha objetivo** | PR abierto el lunes 16/11 |
| **Rama sugerida** | `feature/t05-panel-operador` |

## Qué es y para qué sirve

La API ya permite que un **operador** (alguien de soporte) bloquee y desbloquee cuentas de clientes (etapa 3). Pero hoy eso solo se puede hacer desde Swagger. Tu tarea es una pantalla en el front para eso: el operador inicia sesión y, en vez del perfil de cliente, ve un panel donde busca a un cliente, ve su estado y lo bloquea o desbloquea.

Toda la parte de la API **ya está hecha y probada**: esta tarea es solo front.

## Lo que tenés que saber antes

- **Cómo funcionan los bloqueos:** leé la sección 2 del PDF de cambios del 7/11, o las reglas de bloqueos en `AGENTS.md` y en `m2-clientes/README.md` ("Decisiones de la etapa 3").
- **Las operaciones de la API** que vas a usar (todas exigen rol `OPERADOR`):
  - `GET /api/v1/clientes/{clienteId}`: el perfil;
  - `GET /api/v1/clientes/{clienteId}/estado-cuenta`: `ACTIVO` o `BLOQUEADO`, con los bloqueos vigentes;
  - `GET /api/v1/clientes/{clienteId}/bloqueos?vigente=true|false&page=0&size=10`: el historial;
  - `POST /api/v1/clientes/{clienteId}/bloqueos` con `{"motivo": "...", "hasta": "2026-11-20T18:00:00-03:00"}` (`hasta` es opcional) y el encabezado `Idempotency-Key`;
  - `PATCH /api/v1/clientes/{clienteId}/bloqueos/{bloqueoId}` con `{"motivo": "..."}`: lo levanta.
- **Modelos para copiar:**
  - `frontend/src/components/DireccionesCard.jsx`: lista, modal y errores;
  - `frontend/src/components/EstadoCuentaAviso.jsx`: cómo se muestran los bloqueos;
  - `frontend/src/api.js`: ya tiene `obtenerEstadoCuenta`.

## Pasos

1. **Detectar si el usuario es operador:** el token trae los roles en `keycloak.tokenParsed.realm_access.roles`. Agregá en `api.js` una función `esOperador()` que diga si incluye `"OPERADOR"`.
2. En `App.jsx`, si es operador mostrá `<PanelOperador />` en lugar de la pantalla del cliente, porque un operador no tiene perfil propio. Mantené el encabezado con el nombre y el botón de salir.
3. En `api.js`, agregá `listarBloqueos`, `crearBloqueo` (con `Idempotency-Key`) y `levantarBloqueo`.
4. Creá `components/PanelOperador.jsx` con:
   - un campo para pegar el **clienteId** y un botón "Buscar";
   - los datos del cliente (nombre, teléfono) y su estado con un `Badge` verde o rojo;
   - el formulario **"Bloquear cuenta"**: motivo (obligatorio) y "hasta" opcional (`TextInput type="datetime-local"`).

     El navegador da algo como `2026-11-20T18:00`, sin zona horaria, y la API la exige (si no, `400`). Convertilo con `new Date(valor).toISOString()`, que la da en UTC.
   - la lista de bloqueos (vigentes y anteriores) y, en cada vigente, un botón **"Levantar"** que pide el motivo en un modal.
5. **Errores:**
   - cliente inexistente (`404`): "No existe un cliente con ese id";
   - `422`: "La fecha de fin tiene que ser futura";
   - `409`: "Ese bloqueo ya no está vigente".
6. Después de bloquear o levantar, recargá el estado y la lista.

## Cómo probarlo

1. Con todo levantado, entrá al front con `cliente-demo` y creá su perfil. Su clienteId está en Keycloak (Users → `cliente-demo` → ID).
2. Cerrá sesión y entrá con `operador-demo`: tiene que aparecer el panel.
3. Buscá el clienteId, bloquealo y levantalo. En otra ventana, privada o de otro navegador, entrá como `cliente-demo` y fijate que aparece y desaparece el aviso rojo.
4. `npm run build` sin errores.

## Terminado cuando

- [ ] Un operador ve el panel; un cliente sigue viendo su perfil como antes.
- [ ] Se puede buscar un cliente, bloquearlo (con y sin fecha de fin) y levantar el bloqueo.
- [ ] Los errores muestran mensajes claros.
- [ ] `npm run build` funciona y el CI está en verde.
- [ ] Hay captura en el PR, y `frontend/README.md` y el tablero están actualizados.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea, `frontend/src/App.jsx`, `frontend/src/api.js` y `frontend/src/components/DireccionesCard.jsx`. Necesito un componente `PanelOperador.jsx` en React + Mantine para que un usuario con rol `OPERADOR` busque un cliente por id, vea su estado de cuenta, lo bloquee y levante bloqueos usando la API (las rutas están en la guía). Explicame primero cómo `App.jsx` decide qué mostrar y cómo leer los roles del token. Después hagamos el componente por partes.

## Qué contar en la presentación

- Qué es un operador y por qué solo él puede bloquear (roles).
- Cómo el front decide qué pantalla mostrar según el rol del token.
- Demo: bloquear a un cliente y ver el aviso del lado del cliente.
