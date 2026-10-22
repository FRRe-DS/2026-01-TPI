// Todas las llamadas a la API de M2 pasan por acá.
// Antes de cada pedido renovamos el token si está por vencer
// y lo mandamos en el encabezado Authorization.
// Las rutas y los nombres de campo siguen el contrato común de M2
// (contratos/m2_clientes/openapi.yml).
import keycloak from './keycloak'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Error de la API con su código HTTP, para poder distinguir, por ejemplo, un 404
export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje)
    this.status = status
  }
}

async function pedir(metodo, ruta, cuerpo, encabezadosExtra = {}) {
  // Si al token le quedan menos de 30 segundos, pide uno nuevo a Keycloak
  await keycloak.updateToken(30)

  const encabezados = { Authorization: `Bearer ${keycloak.token}`, ...encabezadosExtra }
  if (cuerpo !== undefined) encabezados['Content-Type'] = 'application/json'

  let respuesta
  try {
    respuesta = await fetch(API_URL + ruta, {
      method: metodo,
      headers: encabezados,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    })
  } catch {
    throw new ErrorApi(0, `No se pudo conectar con la API en ${API_URL}. ¿Está corriendo uvicorn?`)
  }

  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    throw new ErrorApi(respuesta.status, mensajeDeError(respuesta, datos))
  }
  return datos
}

// Los errores llegan en formato problem+json (RFC 9457): { title, detail, status, ... }
function mensajeDeError(respuesta, datos) {
  const texto = datos?.detail ?? datos?.title ?? `Error ${respuesta.status}`
  const requestId = respuesta.headers.get('X-Request-Id')
  // El X-Request-Id sirve para buscar el pedido en los logs de la API
  return requestId && respuesta.status >= 500 ? `${texto} (pedido ${requestId})` : texto
}

// El clienteId es el "sub" del token del cliente logueado
export const miClienteId = () => keycloak.tokenParsed?.sub

export const obtenerCliente = (clienteId) => pedir('GET', `/api/v1/clientes/${clienteId}`)

// Idempotency-Key: el contrato la exige en los POST para que un reintento no duplique el alta
export const crearCliente = (cliente) =>
  pedir('POST', '/api/v1/clientes', cliente, { 'Idempotency-Key': crypto.randomUUID() })

// PATCH: se mandan solo los campos que cambiaron
export const actualizarCliente = (clienteId, cambios) =>
  pedir('PATCH', `/api/v1/clientes/${clienteId}`, cambios)
