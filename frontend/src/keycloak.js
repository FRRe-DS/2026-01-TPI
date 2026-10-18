// Conexión con Keycloak (login).
// keycloak-js se encarga de mandar al usuario a la pantalla de login de Keycloak
// y de traer de vuelta su token. Nunca guardamos contraseñas ni secretos acá.
import Keycloak from 'keycloak-js'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM ?? 'ds-2026-realm',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'm2-frontend',
})

export default keycloak
