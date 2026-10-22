// Punto de entrada: averigua si ya hay una sesión de Keycloak y decide qué mostrar.
// - Sin sesión: la pantalla de bienvenida, con los botones para ingresar o crear cuenta.
// - Con sesión: la app.
import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

import keycloak from './keycloak'
import App from './App'
import Bienvenida from './components/Bienvenida'

const theme = createTheme({
  primaryColor: 'teal',
  defaultRadius: 'md',
})

const root = ReactDOM.createRoot(document.getElementById('root'))

keycloak
  .init({
    // check-sso: si ya hay sesión la usa; si no, vuelve sin pedir login (no fuerza la pantalla de Keycloak)
    onLoad: 'check-sso',
    pkceMethod: 'S256',
    checkLoginIframe: false,
  })
  .then((autenticado) => {
    root.render(
      <React.StrictMode>
        <MantineProvider theme={theme} defaultColorScheme="auto">
          <Notifications position="top-right" />
          {autenticado ? <App /> : <Bienvenida />}
        </MantineProvider>
      </React.StrictMode>,
    )
  })
  .catch(() => {
    root.render(
      <p style={{ fontFamily: 'sans-serif', padding: 24 }}>
        No se pudo conectar con Keycloak en http://localhost:8080. Revisá que esté corriendo
        (docker compose up -d en la carpeta keycloak) y que exista el cliente m2-frontend.
      </p>,
    )
  })
