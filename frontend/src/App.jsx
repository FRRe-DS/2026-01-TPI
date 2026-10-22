// Pantalla principal: muestra el perfil del cliente logueado.
// - Si todavía no tiene perfil (la API responde 404), muestra el formulario para crearlo (POST).
// - Si ya lo tiene, muestra el mismo formulario cargado para editarlo (PATCH),
//   y debajo sus direcciones frecuentes y sus preferencias.
// El contrato no tiene baja del perfil, así que no hay botón para eliminarlo.
import { useEffect, useState } from 'react'
import {
  AppShell, Alert, Badge, Button, Container, Group, Loader, Stack, Text, Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import keycloak from './keycloak'
import { miClienteId, obtenerCliente, crearCliente, actualizarCliente } from './api'
import ClienteForm from './components/ClienteForm'
import DireccionesCard from './components/DireccionesCard'
import PreferenciasCard from './components/PreferenciasCard'

export default function App() {
  const [cliente, setCliente] = useState(null) // el perfil guardado, o null si no hay
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)

  const usuario = keycloak.tokenParsed?.preferred_username

  async function cargarPerfil() {
    setCargando(true)
    setError(null)
    try {
      setCliente(await obtenerCliente(miClienteId()))
    } catch (e) {
      if (e.status === 404) setCliente(null) // todavía no creó su perfil
      else setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  // Al abrir la página, traemos el perfil
  useEffect(() => {
    cargarPerfil()
  }, [])

  async function guardar(datos) {
    if (cliente) {
      const cambios = soloCambios(cliente, datos)
      if (Object.keys(cambios).length === 0) {
        notifications.show({ message: 'No hay cambios para guardar' })
        return
      }
      setCliente(await actualizarCliente(cliente.clienteId, cambios))
      notifications.show({ color: 'teal', message: 'Perfil actualizado' })
    } else {
      setCliente(await crearCliente(datos))
      notifications.show({ color: 'teal', message: 'Perfil creado' })
    }
  }

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Container size="md" h="100%">
          <Group h="100%" justify="space-between">
            <Title order={3}>Movilidad · Clientes</Title>
            <Group gap="sm">
              <Text size="sm" c="dimmed" visibleFrom="xs">{usuario}</Text>
              <Button
                variant="default"
                size="xs"
                onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
              >
                Cerrar sesión
              </Button>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>

      <AppShell.Main>
        <Container size="md" py="md">
          {cargando && (
            <Group justify="center" py="xl"><Loader /></Group>
          )}

          {!cargando && error && (
            <Alert color="red" title="No se pudo cargar el perfil">
              <Stack gap="sm" align="flex-start">
                <Text size="sm">{error}</Text>
                <Button size="xs" variant="light" color="red" onClick={cargarPerfil}>Reintentar</Button>
              </Stack>
            </Alert>
          )}

          {!cargando && !error && (
            <Stack>
              <div>
                <Group gap="sm">
                  <Title order={2}>{cliente ? 'Mi perfil' : 'Creá tu perfil'}</Title>
                  {cliente && (
                    <Badge color={cliente.estado === 'ACTIVO' ? 'teal' : 'red'} variant="light">
                      {cliente.estado === 'ACTIVO' ? 'Cuenta activa' : 'Cuenta bloqueada'}
                    </Badge>
                  )}
                </Group>
                <Text c="dimmed">
                  {cliente
                    ? 'Revisá y actualizá tus datos, direcciones y preferencias de viaje.'
                    : 'Todavía no tenés un perfil de cliente. Completá tus datos para empezar a viajar.'}
                </Text>
              </div>

              <ClienteForm
                key={cliente?.actualizadoEn ?? 'nuevo'}
                inicial={cliente}
                textoBoton={cliente ? 'Guardar cambios' : 'Crear perfil'}
                onGuardar={guardar}
              />

              {/* Direcciones y preferencias necesitan que el perfil exista (si no, la API da 404) */}
              {cliente && <DireccionesCard clienteId={cliente.clienteId} />}
              {cliente && <PreferenciasCard clienteId={cliente.clienteId} />}
            </Stack>
          )}
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

// Para el PATCH: solo los campos que cambiaron respecto del perfil guardado
function soloCambios(guardado, datos) {
  const cambios = {}
  for (const [campo, valor] of Object.entries(datos)) {
    // undefined = campo vacío: el contrato no permite borrar un dato con PATCH, así que no se manda
    if (valor !== undefined && guardado[campo] !== valor) cambios[campo] = valor
  }
  return cambios
}
