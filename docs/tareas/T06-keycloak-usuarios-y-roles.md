# T06 · Keycloak listo para usar: roles, usuarios de prueba y cliente del front

| | |
|---|---|
| **Dificultad** | Fácil (es configuración, casi no hay código) |
| **Depende de** | Nada |
| **Destraba** | T05 necesita `operador-demo`. Además, todo el equipo se ahorra el paso 3 del README |
| **Fecha objetivo** | Mergeada el viernes 13/11 |
| **Rama sugerida** | `feature/t06-keycloak` |

## Qué es y para qué sirve

**Keycloak** es el programa que maneja el inicio de sesión: usuarios, contraseñas y roles. Cuando alguien entra al front, Keycloak le da un **token**, un "pase" digital, que dice quién es y qué rol tiene (CLIENTE, OPERADOR...). La API mira ese token para decidir qué le deja hacer.

Hoy, cada uno que levanta Keycloak tiene que hacer **a mano** el paso 3 del README: crear el cliente del front, los roles en mayúsculas y la contraseña de `cliente-demo`, y asignar roles. Es fácil equivocarse. Tu tarea es que todo eso **venga ya cargado** en el archivo del realm, así Keycloak arranca listo.

El **realm** es el "espacio" de Keycloak donde viven los usuarios y los roles del proyecto: `ds-2026-realm`. Está guardado en `keycloak/realm-config/ds-2026-realm.json`, y Keycloak lo importa al arrancar por primera vez.

## Lo que tenés que saber antes

- Leé el paso 3 del `README.md` de la raíz: es exactamente lo que tiene que quedar automático.
- **Importante:** Keycloak importa el realm **solo si todavía no existe**. Para probar tus cambios hay que borrar sus datos: `docker compose down -v` en la carpeta `keycloak`. Esto borra tu Keycloak local, no el de nadie más.
- `keycloak/` lo armó Matías y puede venir de la cátedra: **coordiná con Lucas y Matías** antes de cambiarlo.

## Pasos

1. Levantá tu Keycloak local y hacé el paso 3 del README a mano, si no lo hiciste. Agregá además:
   - un usuario **`operador-demo`** con contraseña `ds2026` (no temporal) y rol `OPERADOR`;
   - en *Realm settings → Login*, **User registration: On**, así funciona "Crear cuenta" del front;
   - en *Realm settings → User registration → Default roles*, agregá `CLIENTE`, así los que se registran solos son clientes;
   - el rol `SERVICIO` también para la cuenta de servicio `grupo-01`, así se puede probar como si fuera M5 o M9;
   - *Realm settings → Tokens → Access Token Lifespan* en 1 hora, para que en las pruebas no venza a cada rato;
   - (opcional, si te da el tiempo) los **client scopes** `clientes:read`, `clientes:write` y `clientes.estado:read` asignados como opcionales al cliente `m2-frontend`, y un mapper de audiencia `m2-clientes`. Con eso, la API se puede correr con `EXIGIR_SCOPES=true` y `JWT_AUDIENCE=m2-clientes`, y el front con `VITE_KEYCLOAK_SCOPE`. Coordinalo con Lucas.
2. **Exportá el realm** desde el contenedor, con usuarios incluidos:
   ```powershell
   docker exec -it <nombre-del-contenedor-keycloak> /opt/keycloak/bin/kc.sh export --dir /tmp/export --realm ds-2026-realm --users realm_file
   docker cp <nombre-del-contenedor-keycloak>:/tmp/export/ds-2026-realm-realm.json .\ds-2026-realm-exportado.json
   ```
   El nombre del contenedor lo ves con `docker ps`. Si `kc.sh export` se queja de que el servidor está corriendo, pedile ayuda a la IA con el error exacto.
3. Compará el exportado con `keycloak/realm-config/ds-2026-realm.json` (VS Code: clic derecho → "Compare"). Reemplazá el archivo, o pasá solo los cambios si preferís un cambio más chico. Ojo: el exportado puede traer cosas que no hacen falta.
4. **Probalo desde cero:**
   ```powershell
   cd C:\Proyectos\2026-01-TPI\keycloak
   docker compose down -v
   docker compose up -d
   ```
   Esperá un minuto y verificá:
   - podés entrar al front con `cliente-demo` y con `operador-demo` (contraseña `ds2026`) sin haber tocado nada a mano;
   - el comando del paso 6 del README devuelve un token.
5. Actualizá el paso 3 del README: ahora solo hace falta si alguien quiere entender qué viene configurado, o si usa otro Keycloak.

### Segunda parte (cuando el Grupo 17 lo comparta)

El Grupo 17 está armando un Keycloak de desarrollo común para los dos M2. Cuando esté, probá nuestra API y el front contra él y anotá en el PR qué cambia: URL, nombre del cliente del front, usuarios.

## Terminado cuando

- [ ] Con `docker compose down -v` y `up -d`, Keycloak arranca con los roles, `cliente-demo`, `operador-demo`, el cliente `m2-frontend` y el registro habilitado.
- [ ] Se puede entrar al front sin configurar nada a mano.
- [ ] Ningún secreto nuevo de verdad en el repo. Las contraseñas de prueba (`ds2026`) son solo para desarrollo, como las que ya están en `keycloak/.env`.
- [ ] README (paso 3) y tablero actualizados.

## Prompt para la IA

> Estoy configurando Keycloak 23 para un proyecto de la facultad. Te paso la guía de mi tarea y el paso 3 del README. Necesito que el realm `ds-2026-realm` arranque ya configurado (roles CLIENTE, OPERADOR, SERVICIO y CONDUCTOR; usuarios `cliente-demo` y `operador-demo`; un cliente público `m2-frontend` con PKCE; registro habilitado; CLIENTE como rol por defecto) usando el archivo de importación `realm-config/ds-2026-realm.json`. Explicame primero qué es un realm, un rol y un cliente en Keycloak. Después guiame para exportar el realm desde Docker e importarlo.

## Qué contar en la presentación

- Qué hace Keycloak (M1, identidad) y qué es un token.
- Qué roles hay y quién puede qué en M2.
- Cómo quedó configurado para que cualquiera lo levante con un comando.
