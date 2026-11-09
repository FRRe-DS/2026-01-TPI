# T08 · Datos de demo, diagramas y armado de la presentación

| | |
|---|---|
| **Dificultad** | Fácil |
| **Depende de** | Nada para empezar. Para cerrar la presentación, de todas las tareas |
| **Fecha objetivo** | Script y diagramas el lunes 16/11; presentación armada para el ensayo del miércoles 18/11 |
| **Rama sugerida** | `feature/t08-demo-y-docs` |

## Qué es y para qué sirve

Tres cosas que hacen que la presentación salga bien:

1. **Datos de demo:** un script que carga en MongoDB clientes con datos realistas (direcciones, preferencias, un bloqueo levantado), así la demo no arranca con todo vacío.
2. **Diagramas:** dibujos simples de cómo está armado el sistema y cómo viaja un pedido. La consigna pide diagramas junto con el código (RNF-20).
3. **La presentación del equipo:** una plantilla con una diapositiva por persona, el guion de la demo y la coordinación del ensayo.

## Lo que tenés que saber antes

- **Cómo se guardan los datos en MongoDB:** al principio de `m2-clientes/database.py` están las colecciones, y en `m2-clientes/rutas/*.py` se ve qué campos tiene cada documento (por ejemplo, la función `crear_direccion`).
- **El sistema en general:** el PDF "Estado del proyecto" y la [guía de primeros pasos](../primeros-pasos.md).
- **Diagramas en Mermaid:** se escriben como texto y GitHub los dibuja solo. Hay un ejemplo en el `README.md` de la raíz (sección "Cómo instalarlo y correrlo").

## Pasos

### 1. Script de datos de demo (`m2-clientes/scripts/cargar_demo.py`)

1. Que reciba un `clienteId` como parámetro, el de `cliente-demo` en tu Keycloak: `python scripts/cargar_demo.py <clienteId>`.
2. Que use `config.py` y `database.py` del proyecto (así toma la misma `MONGO_URL`) y cargue:
   - el perfil, si no existe: nombre, apellido, teléfono `+549362...`;
   - 4 direcciones (Casa, Facultad, Trabajo y una reciente) con direcciones de Resistencia;
   - preferencias (por ejemplo, auto y SMS);
   - un bloqueo **ya levantado**, para que el historial del operador tenga algo.
3. Que **no duplique** si se corre dos veces: borrá antes solo los datos de ese cliente, o revisá si ya existen.
4. Usá los mismos nombres de campos que guarda la API. Si te equivocás en un nombre, la API no los va a ver. Las fechas, con `ahora()` de `rutas/comunes.py`.

### 2. Diagramas (`docs/diagramas.md`)

En Mermaid:
1. **Arquitectura:** front, API de M2, Keycloak, MongoDB, M6 y quién consulta a M2 (M5 y M9).
2. **Secuencia "el cliente ve su perfil":** front → Keycloak (login) → API (token) → MongoDB.
3. **Secuencia "calificar un viaje":** front → API → M6 (¿el viaje terminó?) → MongoDB (índice único).
4. **Secuencia "M9 pregunta si el cliente está habilitado":** M9 → API (rol SERVICIO) → estado de cuenta.

Revisá con quien tenga cada tarea que el diagrama coincida con lo que hizo.

### 3. Presentación

1. Armá la plantilla, en Google Slides o en lo que use el equipo:
   - portada;
   - qué es M2;
   - arquitectura (tu diagrama);
   - una diapositiva por persona: qué hizo, cómo, qué le costó;
   - demo;
   - qué falta.
2. Pedile a cada uno su diapositiva para el lunes 16/11.
3. Escribí el **guion de la demo**, con el orden y quién maneja cada parte:
   1. login como cliente;
   2. perfil;
   3. historial y calificar;
   4. login como operador;
   5. bloquear;
   6. el cliente ve el aviso;
   7. todo levantado con un comando.
4. Coordiná el **ensayo del miércoles 18/11**: que la demo se haga entera, al menos una vez, en la PC que se va a usar.

## Terminado cuando

- [ ] El script carga los datos y se puede correr dos veces sin duplicar.
- [ ] Los 4 diagramas están en `docs/diagramas.md` y se ven bien en GitHub.
- [ ] La presentación tiene la diapositiva de cada uno y el guion de la demo.
- [ ] Se hizo el ensayo.
- [ ] Tablero actualizado.

## Prompt para la IA

> Te paso el `AGENTS.md` de mi proyecto, la guía de mi tarea y los archivos `database.py`, `rutas/perfil.py` y `rutas/direcciones.py`. Necesito un script `scripts/cargar_demo.py` que cargue datos de ejemplo en MongoDB para un cliente, con los mismos campos que guarda la API, sin duplicar si se corre dos veces. Explicame primero cómo se guardan un perfil y una dirección en la base, mirando el código. Después hagamos el script.

> (Para los diagramas) Te paso el README y la guía. Ayudame a escribir en Mermaid un diagrama de secuencia de cómo se califica un viaje: front → API de M2 → M6 → MongoDB, con el caso de error si M6 no responde.

## Qué contar en la presentación

- La arquitectura general, con tu diagrama: es una buena forma de abrir la presentación.
- Cómo se preparó la demo y por qué hace falta tener datos realistas.
