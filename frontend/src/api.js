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

// ---------------------------------------------------------- Direcciones frecuentes (RF-2.2)

// El listado viene paginado: { items, page, size, totalElementos, totalPaginas }. page empieza en 0.
export const listarDirecciones = (clienteId, { page = 0, size = 20, tipo } = {}) => {
  const params = new URLSearchParams({ page, size })
  if (tipo) params.set('tipo', tipo)
  return pedir('GET', `/api/v1/clientes/${clienteId}/direcciones?${params}`)
}

export const crearDireccion = (clienteId, direccion) =>
  pedir('POST', `/api/v1/clientes/${clienteId}/direcciones`, direccion,
    { 'Idempotency-Key': crypto.randomUUID() })

export const actualizarDireccion = (clienteId, direccionId, cambios) =>
  pedir('PATCH', `/api/v1/clientes/${clienteId}/direcciones/${direccionId}`, cambios)

export const eliminarDireccion = (clienteId, direccionId) =>
  pedir('DELETE', `/api/v1/clientes/${clienteId}/direcciones/${direccionId}`)

// ---------------------------------------------------------- Preferencias (RF-2.3)

export const obtenerPreferencias = (clienteId) =>
  pedir('GET', `/api/v1/clientes/${clienteId}/preferencias`)

// PUT: reemplaza todas las preferencias
export const guardarPreferencias = (clienteId, preferencias) =>
  pedir('PUT', `/api/v1/clientes/${clienteId}/preferencias`, preferencias)

// ---------------------------------------------------------- Estado de cuenta (RF-2.6)

// { clienteId, estado: 'ACTIVO' | 'BLOQUEADO', bloqueosVigentes: [{ motivo, desde, hasta, ... }] }
export const obtenerEstadoCuenta = (clienteId) =>
  pedir('GET', `/api/v1/clientes/${clienteId}/estado-cuenta`)
// ---------------------------------------------------------- Roles y bloqueos (RF-2.6 · Operador)

// Los roles del realm llegan en el token como un arreglo de strings en mayúsculas
export const esOperador = () =>
  Boolean(keycloak.tokenParsed?.realm_access?.roles?.includes('OPERADOR'))

// Listado paginado de bloqueos de un cliente: { items, page, size, totalElementos, totalPaginas }
export const listarBloqueos = (clienteId, { page = 0, size = 10, vigente } = {}) => {
  const params = new URLSearchParams({ page, size })
  if (vigente !== undefined) params.set('vigente', String(vigente))
  return pedir('GET', `/api/v1/clientes/${clienteId}/bloqueos?${params}`)
}

// POST: registra un bloqueo administrativo (hasta es opcional en formato ISO-8601 con zona horaria)
export const crearBloqueo = (clienteId, bloqueo) =>
  pedir('POST', `/api/v1/clientes/${clienteId}/bloqueos`, bloqueo,
    { 'Idempotency-Key': crypto.randomUUID() })

// PATCH: levanta un bloqueo vigente indicando el motivo
export const levantarBloqueo = (clienteId, bloqueoId, motivo) =>
  pedir('PATCH', `/api/v1/clientes/${clienteId}/bloqueos/${bloqueoId}`, { motivo })