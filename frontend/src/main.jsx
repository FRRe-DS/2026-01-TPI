// Punto de entrada: primero hace login con Keycloak y después muestra la app.
import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

import keycloak from './keycloak'
import App from './App'

const theme = createTheme({
  primaryColor: 'teal',
  defaultRadius: 'md',
})

const root = ReactDOM.createRoot(document.getElementById('root'))

keycloak
  .init({
    onLoad: 'login-required', // si no hay sesión, manda a la pantalla de login
    pkceMethod: 'S256',
    checkLoginIframe: false,
  })
  .then(() => {
    root.render(
      <React.StrictMode>
        <MantineProvider theme={theme} defaultColorScheme="auto">
          <Notifications position="top-right" />
          <App />
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
