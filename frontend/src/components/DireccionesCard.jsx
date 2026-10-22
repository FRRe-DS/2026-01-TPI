// Direcciones frecuentes del cliente (RF-2.2): lista paginada con alta, edición y borrado.
// Cada dirección tiene tipo (favorita o reciente), un texto y, opcionalmente, un alias.
// Las coordenadas son opcionales en el contrato y no se cargan desde esta pantalla.
import { useEffect, useState } from 'react'
import {
  ActionIcon, Badge, Button, Card, Group, Loader, Modal, Pagination, SegmentedControl,
  Stack, Text, TextInput, Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import { listarDirecciones, crearDireccion, actualizarDireccion, eliminarDireccion } from '../api'

const POR_PAGINA = 5
const TIPOS = [
  { value: 'FAVORITA', label: 'Favorita' },
  { value: 'RECIENTE', label: 'Reciente' },
]
const VACIA = { tipo: 'FAVORITA', alias: '', texto: '' }

export default function DireccionesCard({ clienteId }) {
  const [pagina, setPagina] = useState(null) // respuesta paginada de la API
  const [numero, setNumero] = useState(0) // página actual (la API empieza en 0)
  const [cargando, setCargando] = useState(true)
  const [editando, setEditando] = useState(null) // null = cerrado; {} = nueva; dirección = editar
  const [form, setForm] = useState(VACIA)
  const [guardando, setGuardando] = useState(false)
  const [aBorrar, setABorrar] = useState(null)

  async function cargar(n = numero) {
    setCargando(true)
    try {
      const datos = await listarDirecciones(clienteId, { page: n, size: POR_PAGINA })
      // Si borramos la última de una página, volvemos a la anterior
      if (datos.items.length === 0 && n > 0) return cargar(n - 1)
      setPagina(datos)
      setNumero(n)
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudieron cargar las direcciones', message: e.message })
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar(0)
  }, [clienteId])

  function abrir(direccion) {
    setEditando(direccion ?? {})
    setForm(direccion
      ? { tipo: direccion.tipo, alias: direccion.alias ?? '', texto: direccion.texto }
      : VACIA)
  }

  async function guardar(evento) {
    evento.preventDefault()
    setGuardando(true)
    // El alias es opcional: si está vacío, no se manda (el contrato no admite null)
    const datos = { tipo: form.tipo, texto: form.texto.trim() }
    if (form.alias.trim()) datos.alias = form.alias.trim()
    try {
      if (editando.direccionId) {
        await actualizarDireccion(clienteId, editando.direccionId, datos)
        notifications.show({ color: 'teal', message: 'Dirección actualizada' })
        await cargar(numero)
      } else {
        await crearDireccion(clienteId, datos)
        notifications.show({ color: 'teal', message: 'Dirección agregada' })
        await cargar(0) // las nuevas aparecen primero
      }
      setEditando(null)
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudo guardar', message: e.message })
    } finally {
      setGuardando(false)
    }
  }

  async function borrar() {
    try {
      await eliminarDireccion(clienteId, aBorrar.direccionId)
      notifications.show({ message: 'Dirección eliminada' })
      setABorrar(null)
      await cargar(numero)
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudo eliminar', message: e.message })
    }
  }

  return (
    <Card withBorder padding="lg">
      <Group justify="space-between" mb="md">
        <Title order={4}>Mis direcciones</Title>
        <Button variant="light" size="xs" onClick={() => abrir(null)}>+ Agregar dirección</Button>
      </Group>

      {cargando && !pagina && <Group justify="center"><Loader size="sm" /></Group>}

      {pagina && pagina.totalElementos === 0 && (
        <Text c="dimmed" size="sm">No cargaste direcciones. Agregá tu casa, tu trabajo o la facu.</Text>
      )}

      <Stack gap="xs">
        {pagina?.items.map((d) => (
          <Card key={d.direccionId} withBorder padding="sm">
            <Group justify="space-between" wrap="nowrap">
              <div style={{ minWidth: 0 }}>
                <Group gap="xs">
                  {d.alias && <Text fw={600}>{d.alias}</Text>}
                  <Badge size="sm" variant="light" color={d.tipo === 'FAVORITA' ? 'teal' : 'gray'}>
                    {d.tipo === 'FAVORITA' ? 'Favorita' : 'Reciente'}
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed" truncate>{d.texto}</Text>
              </div>
              <Group gap={4} wrap="nowrap">
                <Button variant="subtle" size="xs" onClick={() => abrir(d)}>Editar</Button>
                <ActionIcon variant="subtle" color="red" aria-label="Eliminar dirección" onClick={() => setABorrar(d)}>
                  ✕
                </ActionIcon>
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>

      {pagina && pagina.totalPaginas > 1 && (
        <Group justify="center" mt="md">
          {/* Mantine numera desde 1 y la API desde 0 */}
          <Pagination size="sm" total={pagina.totalPaginas} value={numero + 1} onChange={(p) => cargar(p - 1)} />
        </Group>
      )}

      <Modal opened={editando !== null} onClose={() => setEditando(null)}
        title={editando?.direccionId ? 'Editar dirección' : 'Nueva dirección'}>
        <form onSubmit={guardar}>
          <Stack>
            <SegmentedControl data={TIPOS} value={form.tipo}
              onChange={(tipo) => setForm((f) => ({ ...f, tipo }))} />
            <TextInput label="Alias" placeholder="Casa, Trabajo…" maxLength={50} value={form.alias}
              onChange={(e) => setForm((f) => ({ ...f, alias: e.target.value }))} />
            <TextInput label="Dirección" placeholder="Av. Sarmiento 1234, Resistencia, Chaco" required
              maxLength={255} value={form.texto}
              onChange={(e) => setForm((f) => ({ ...f, texto: e.target.value }))} />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEditando(null)}>Cancelar</Button>
              <Button type="submit" loading={guardando}>Guardar</Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal opened={aBorrar !== null} onClose={() => setABorrar(null)} title="¿Eliminar la dirección?">
        <Text size="sm">{aBorrar?.alias ? `${aBorrar.alias}: ` : ''}{aBorrar?.texto}</Text>
        <Group justify="flex-end" mt="lg">
          <Button variant="default" onClick={() => setABorrar(null)}>Cancelar</Button>
          <Button color="red" onClick={borrar}>Eliminar</Button>
        </Group>
      </Modal>
    </Card>
  )
}
