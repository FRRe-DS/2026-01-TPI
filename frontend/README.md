# Front de M2 · Clientes

Página web para que un cliente inicie sesión con Keycloak y cree, vea y edite su perfil usando la API de M2, según el contrato común (`contratos/m2_clientes/openapi.yml`). Las direcciones frecuentes y las preferencias se vuelven a agregar en la etapa 2.

**Tecnologías:** React 19 + Vite (proyecto y servidor de desarrollo) + Mantine (componentes visuales) + keycloak-js (login).

## Requisitos

- **Node.js LTS** (22 o 24): https://nodejs.org. Trae `npm`, el instalador de librerías de JavaScript.
- Keycloak, MongoDB y la API de M2 corriendo (ver el README principal).

## Configuración de Keycloak (una sola vez)

El front necesita su propio cliente **público** en Keycloak: un cliente público no tiene secreto, porque todo lo que está en el navegador lo puede ver cualquiera.

1. Entrar a http://localhost:8080 → Administration Console (`admin` / `ds2026`) → realm **ds-2026-realm**.
2. **Clients → Create client**
   - Client ID: `m2-frontend` → Next
   - Client authentication: **Off** · Standard flow: **On** → Next
   - Valid redirect URIs: `http://localhost:5173/*`
   - Valid post logout redirect URIs: `http://localhost:5173/*`
   - Web origins: `http://localhost:5173` → Save
3. Usuario para probar: **Users → cliente-demo → Credentials → Reset password**, poner una contraseña y desmarcar *Temporary*.

## Correrlo

```powershell
cd C:\Proyectos\2026-01-TPI\frontend
npm install      # solo la primera vez, o cuando cambie package.json
npm run dev
```

Abrir http://localhost:5173: redirige al login de Keycloak y, al entrar, vuelve a la app.

## Estructura

```
frontend/
├── index.html                 # página base
├── vite.config.js             # configuración de Vite (puerto 5173)
├── .env.example               # URLs configurables (RNF-06)
└── src/
    ├── main.jsx               # hace el login y arranca la app
    ├── keycloak.js            # conexión con Keycloak
    ├── api.js                 # llamadas a la API de M2 con el token (rutas del contrato)
    ├── App.jsx                # pantalla principal: carga el perfil por el sub del token, lo crea o lo edita (PATCH)
    └── components/
        └── ClienteForm.jsx    # formulario de datos personales
```
