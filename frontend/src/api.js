// Todas las llamadas a la API de M2 pasan por acá.
// Antes de cada pedido renovamos el token si está por vencer
// y lo mandamos en el encabezado Authorization.
import keycloak from './keycloak'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function pedir(metodo, ruta, cuerpo) {
  // Si al token le quedan menos de 30 segundos, pide uno nuevo a Keycloak
  await keycloak.updateToken(30)

  let respuesta
  try {
    respuesta = await fetch(API_URL + ruta, {
      method: metodo,
      headers: {
        Authorization: `Bearer ${keycloak.token}`,
        'Content-Type': 'application/json',
      },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    })
  } catch {
    throw new Error('No se pudo conectar con la API. ¿Está corriendo uvicorn en el puerto 8000?')
  }

  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    throw new Error(mensajeDeError(respuesta.status, datos))
  }
  return datos
}

// Convierte la respuesta de error de FastAPI en un texto legible
function mensajeDeError(status, datos) {
  const detalle = datos?.detail
  if (Array.isArray(detalle)) {
    // Error 422: Pydantic devuelve una lista con cada campo inválido
    return detalle.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join(' · ')
  }
  return detalle ?? `Error ${status}`
}

export const listarClientes = () => pedir('GET', '/api/v1/clientes')
export const crearCliente = (cliente) => pedir('POST', '/api/v1/clientes', cliente)
export const actualizarCliente = (id, cliente) => pedir('PUT', `/api/v1/clientes/${id}`, cliente)
export const eliminarCliente = (id) => pedir('DELETE', `/api/v1/clientes/${id}`)
