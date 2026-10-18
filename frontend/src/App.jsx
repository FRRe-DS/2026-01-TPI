// Pantalla principal: muestra el perfil del cliente logueado.
// - Si todavía no tiene perfil, muestra el formulario para crearlo (POST).
// - Si ya lo tiene, muestra el mismo formulario cargado para editarlo (PUT) o eliminarlo (DELETE).
import { useEffect, useState } from 'react'
import {
  AppShell, Alert, Button, Container, Group, Loader, Modal, Stack, Text, Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import keycloak from './keycloak'
import { listarClientes, crearCliente, actualizarCliente, eliminarCliente } from './api'
import ClienteForm from './components/ClienteForm'

export default function App() {
  const [cliente, setCliente] = useState(null) // el perfil guardado, o null si no hay
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [confirmarBorrado, setConfirmarBorrado] = useState(false)

  const usuario = keycloak.tokenParsed?.preferred_username

  async function cargarPerfil() {
    setCargando(true)
    setError(null)
    try {
      const lista = await listarClientes() // la API devuelve solo los clientes de este usuario
      setCliente(lista[0] ?? null)
    } catch (e) {
      setError(e.message)
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
      await actualizarCliente(cliente._id, datos)
      notifications.show({ color: 'teal', message: 'Perfil actualizado' })
    } else {
      await crearCliente(datos)
      notifications.show({ color: 'teal', message: 'Perfil creado' })
    }
    await cargarPerfil()
  }

  async function borrar() {
    try {
      await eliminarCliente(cliente._id)
      notifications.show({ message: 'Perfil eliminado' })
      setConfirmarBorrado(false)
      await cargarPerfil()
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudo eliminar', message: e.message })
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
                <Title order={2}>{cliente ? 'Mi perfil' : 'Creá tu perfil'}</Title>
                <Text c="dimmed">
                  {cliente
                    ? 'Revisá y actualizá tus datos, direcciones y preferencias de viaje.'
                    : 'Todavía no tenés un perfil de cliente. Completá tus datos para empezar a viajar.'}
                </Text>
              </div>

              <ClienteForm
                key={cliente?._id ?? 'nuevo'}
                inicial={cliente}
                textoBoton={cliente ? 'Guardar cambios' : 'Crear perfil'}
                onGuardar={guardar}
              />

              {cliente && (
                <Group justify="flex-end">
                  <Button variant="subtle" color="red" onClick={() => setConfirmarBorrado(true)}>
                    Eliminar mi perfil
                  </Button>
                </Group>
              )}
            </Stack>
          )}
        </Container>
      </AppShell.Main>

      <Modal opened={confirmarBorrado} onClose={() => setConfirmarBorrado(false)} title="¿Eliminar tu perfil?">
        <Text size="sm">Se borran tus datos, direcciones y preferencias. Esta acción no se puede deshacer.</Text>
        <Group justify="flex-end" mt="lg">
          <Button variant="default" onClick={() => setConfirmarBorrado(false)}>Cancelar</Button>
          <Button color="red" onClick={borrar}>Eliminar</Button>
        </Group>
      </Modal>
    </AppShell>
  )
}
