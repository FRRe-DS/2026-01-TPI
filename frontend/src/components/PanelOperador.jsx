// Panel del operador (RF-2.6): permite buscar un cliente por su clienteId,
// consultar su estado de cuenta, registrar bloqueos administrativos y levantarlos.
// Los bloqueos nunca se borran: quedan en el historial del cliente.
import { useState } from 'react'
import {
  Alert, Badge, Button, Card, Group, Loader, Modal, Pagination, Stack, Text, TextInput, Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import {
  obtenerCliente, obtenerEstadoCuenta, listarBloqueos, crearBloqueo, levantarBloqueo,
} from '../api'

const POR_PAGINA = 10
const formatoFecha = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' })

export default function PanelOperador() {
  const [busqueda, setBusqueda] = useState('')
  const [cliente, setCliente] = useState(null)
  const [estadoCuenta, setEstadoCuenta] = useState(null)
  const [paginaBloqueos, setPaginaBloqueos] = useState(null)
  const [numeroPagina, setNumeroPagina] = useState(0)
  const [buscando, setBuscando] = useState(false)
  const [errorBusqueda, setErrorBusqueda] = useState(null)

  // Formulario para bloquear cuenta
  const [motivoBloqueo, setMotivoBloqueo] = useState('')
  const [hastaBloqueo, setHastaBloqueo] = useState('')
  const [bloqueando, setBloqueando] = useState(false)

  // Modal para levantar un bloqueo vigente
  const [aLevantar, setALevantar] = useState(null)
  const [motivoLevante, setMotivoLevante] = useState('')
  const [levantando, setLevantando] = useState(false)

  async function cargarDatosCliente(id, page = 0) {
    const [perfil, estado, bloqueos] = await Promise.all([
      obtenerCliente(id),
      obtenerEstadoCuenta(id),
      listarBloqueos(id, { page, size: POR_PAGINA }),
    ])
    setCliente(perfil)
    setEstadoCuenta(estado)
    setPaginaBloqueos(bloqueos)
    setNumeroPagina(page)
  }

  async function buscar(evento) {
    evento.preventDefault()
    const id = busqueda.trim()
    if (!id) return

    setBuscando(true)
    setErrorBusqueda(null)
    setCliente(null)
    setEstadoCuenta(null)
    setPaginaBloqueos(null)

    try {
      await cargarDatosCliente(id, 0)
    } catch (e) {
      setErrorBusqueda(e.status === 404 ? 'No existe un cliente con ese id' : e.message)
    } finally {
      setBuscando(false)
    }
  }

  async function cambiarPagina(nuevaPagina) {
    if (!cliente) return
    try {
      const bloqueos = await listarBloqueos(cliente.clienteId, { page: nuevaPagina, size: POR_PAGINA })
      setPaginaBloqueos(bloqueos)
      setNumeroPagina(nuevaPagina)
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudo cargar la página', message: e.message })
    }
  }

  async function registrarBloqueo(evento) {
    evento.preventDefault()
    const motivo = motivoBloqueo.trim()
    if (!motivo || !cliente) return

    setBloqueando(true)
    const cuerpo = { motivo }
    // El navegador entrega "YYYY-MM-DDTHH:mm" sin zona horaria; toISOString() lo pasa a UTC con zona horaria.
    if (hastaBloqueo) {
      cuerpo.hasta = new Date(hastaBloqueo).toISOString()
    }

    try {
      await crearBloqueo(cliente.clienteId, cuerpo)
      notifications.show({ color: 'teal', message: 'Cuenta bloqueada' })
      setMotivoBloqueo('')
      setHastaBloqueo('')
      await cargarDatosCliente(cliente.clienteId, 0)
    } catch (e) {
      const mensaje = e.status === 422 ? 'La fecha de fin tiene que ser futura' : e.message
      notifications.show({ color: 'red', title: 'No se pudo bloquear la cuenta', message: mensaje })
    } finally {
      setBloqueando(false)
    }
  }

  function abrirModalLevantar(bloqueo) {
    setALevantar(bloqueo)
    setMotivoLevante('')
  }

  async function confirmarLevantar(evento) {
    evento.preventDefault()
    const motivo = motivoLevante.trim()
    if (!motivo || !cliente || !aLevantar) return

    setLevantando(true)
    try {
      await levantarBloqueo(cliente.clienteId, aLevantar.bloqueoId, motivo)
      notifications.show({ color: 'teal', message: 'Bloqueo levantado' })
      setALevantar(null)
      setMotivoLevante('')
      await cargarDatosCliente(cliente.clienteId, numeroPagina)
    } catch (e) {
      const mensaje = e.status === 409 ? 'Ese bloqueo ya no está vigente' : e.message
      notifications.show({ color: 'red', title: 'No se pudo levantar el bloqueo', message: mensaje })
      if (e.status === 409) {
        setALevantar(null)
        await cargarDatosCliente(cliente.clienteId, numeroPagina)
      }
    } finally {
      setLevantando(false)
    }
  }

  const estadoActual = estadoCuenta?.estado ?? cliente?.estado

  return (
    <Stack>
      <div>
        <Title order={2}>Panel del operador</Title>
        <Text c="dimmed">
          Buscá un cliente por su identificador para consultar su estado de cuenta y gestionar bloqueos.
        </Text>
      </div>

      {/* Buscador por clienteId */}
      <Card withBorder padding="lg">
        <form onSubmit={buscar}>
          <Group align="flex-end">
            <TextInput
              style={{ flex: 1 }}
              label="ID del cliente (clienteId)"
              placeholder="Pegá el UUID del cliente"
              required
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
            <Button type="submit" loading={buscando}>Buscar</Button>
          </Group>
        </form>
      </Card>

      {buscando && <Group justify="center" py="md"><Loader /></Group>}

      {!buscando && errorBusqueda && (
        <Alert color="red" variant="light" title="No se encontró el cliente">
          <Text size="sm">{errorBusqueda}</Text>
        </Alert>
      )}

      {!buscando && cliente && (
        <>
          {/* Ficha resumida del cliente y estado de cuenta */}
          <Card withBorder padding="lg">
            <Group justify="space-between" align="flex-start">
              <div>
                <Group gap="sm">
                  <Title order={4}>{cliente.nombre} {cliente.apellido}</Title>
                  <Badge color={estadoActual === 'ACTIVO' ? 'teal' : 'red'} variant="light">
                    {estadoActual === 'ACTIVO' ? 'ACTIVO' : 'BLOQUEADO'}
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed" mt={4}>
                  Teléfono: {cliente.telefono} · ID: {cliente.clienteId}
                </Text>
              </div>
            </Group>
          </Card>

          {/* Formulario para registrar un bloqueo */}
          <Card withBorder padding="lg">
            <Title order={4} mb="md">Bloquear cuenta</Title>
            <form onSubmit={registrarBloqueo}>
              <Stack>
                <TextInput
                  label="Motivo"
                  placeholder="Ej.: Reclamo por incumplimiento de normas"
                  required
                  maxLength={500}
                  value={motivoBloqueo}
                  onChange={(e) => setMotivoBloqueo(e.target.value)}
                />
                <TextInput
                  type="datetime-local"
                  label="Hasta (opcional)"
                  description="Dejalo vacío si el bloqueo rige hasta que se levante manualmente."
                  value={hastaBloqueo}
                  onChange={(e) => setHastaBloqueo(e.target.value)}
                />
                <Group justify="flex-end">
                  <Button type="submit" color="red" loading={bloqueando}>
                    Bloquear cuenta
                  </Button>
                </Group>
              </Stack>
            </form>
          </Card>

          {/* Historial de bloqueos (vigentes y anteriores) */}
          <Card withBorder padding="lg">
            <Title order={4} mb="md">Bloqueos registrados</Title>

            {paginaBloqueos && paginaBloqueos.totalElementos === 0 && (
              <Text c="dimmed" size="sm">Este cliente no tiene bloqueos en su historial.</Text>
            )}

            <Stack gap="xs">
              {paginaBloqueos?.items.map((b) => (
                <Card key={b.bloqueoId} withBorder padding="sm">
                  <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <Stack gap={4} style={{ minWidth: 0 }}>
                      <Group gap="xs">
                        <Badge size="sm" variant="light" color={b.vigente ? 'red' : 'gray'}>
                          {b.vigente ? 'Vigente' : b.levantadoEn ? 'Levantado' : 'Vencido'}
                        </Badge>
                        <Text size="xs" c="dimmed">
                          Desde {formatoFecha.format(new Date(b.desde))}
                          {b.hasta
                            ? ` · hasta el ${formatoFecha.format(new Date(b.hasta))}`
                            : ' · hasta que se levante'}
                        </Text>
                      </Group>
                      <Text size="sm" fw={500}>{b.motivo}</Text>
                      {!b.vigente && b.motivoLevantamiento && (
                        <Text size="xs" c="dimmed">
                          Levante: {b.motivoLevantamiento}
                          {b.levantadoEn ? ` (${formatoFecha.format(new Date(b.levantadoEn))})` : ''}
                        </Text>
                      )}
                    </Stack>

                    {b.vigente && (
                      <Button
                        size="xs"
                        variant="light"
                        color="teal"
                        onClick={() => abrirModalLevantar(b)}
                      >
                        Levantar
                      </Button>
                    )}
                  </Group>
                </Card>
              ))}
            </Stack>

            {paginaBloqueos && paginaBloqueos.totalPaginas > 1 && (
              <Group justify="center" mt="md">
                <Pagination
                  size="sm"
                  total={paginaBloqueos.totalPaginas}
                  value={numeroPagina + 1}
                  onChange={(p) => cambiarPagina(p - 1)}
                />
              </Group>
            )}
          </Card>
        </>
      )}

      {/* Modal para confirmar levante */}
      <Modal
        opened={aLevantar !== null}
        onClose={() => setALevantar(null)}
        title="Levantar bloqueo"
      >
        <form onSubmit={confirmarLevantar}>
          <Stack>
            <Text size="sm" c="dimmed">
              Bloqueo: {aLevantar?.motivo}
            </Text>
            <TextInput
              label="Motivo del levante"
              placeholder="Ej.: Reclamo resuelto con el cliente"
              required
              maxLength={500}
              value={motivoLevante}
              onChange={(e) => setMotivoLevante(e.target.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setALevantar(null)}>Cancelar</Button>
              <Button type="submit" color="teal" loading={levantando}>Confirmar</Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}