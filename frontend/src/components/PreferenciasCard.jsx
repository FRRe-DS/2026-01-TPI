// Preferencias del cliente (RF-2.3): tipos de vehículo, canales de comunicación y accesibilidad.
// Guardar reemplaza todas las preferencias (PUT del contrato).
import { useEffect, useState } from 'react'
import { Button, Card, Checkbox, Group, Loader, SimpleGrid, Stack, Text, Textarea, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'

import { obtenerPreferencias, guardarPreferencias } from '../api'

// Valores del contrato (enums) con su texto para mostrar
const VEHICULOS = [
  { value: 'AUTO', label: 'Auto' },
  { value: 'MOTO', label: 'Moto' },
]
const CANALES = [
  { value: 'EMAIL', label: 'Email' },
  { value: 'SMS', label: 'SMS' },
  { value: 'PUSH', label: 'Notificaciones en el celular' },
]
const ACCESIBILIDAD = [
  { value: 'SILLA_DE_RUEDAS', label: 'Silla de ruedas' },
  { value: 'ASISTENCIA_VISUAL', label: 'Asistencia visual' },
  { value: 'ASISTENCIA_AUDITIVA', label: 'Asistencia auditiva' },
  { value: 'ANIMAL_DE_ASISTENCIA', label: 'Animal de asistencia' },
]

function Opciones({ label, descripcion, opciones, value, onChange }) {
  return (
    <Checkbox.Group label={label} description={descripcion} value={value} onChange={onChange}>
      <Stack gap="xs" mt="xs">
        {opciones.map((o) => <Checkbox key={o.value} value={o.value} label={o.label} />)}
      </Stack>
    </Checkbox.Group>
  )
}

export default function PreferenciasCard({ clienteId }) {
  const [form, setForm] = useState(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    obtenerPreferencias(clienteId)
      .then((p) => setForm({ ...p, observacionesAccesibilidad: p.observacionesAccesibilidad ?? '' }))
      .catch((e) => notifications.show({ color: 'red', title: 'No se pudieron cargar las preferencias', message: e.message }))
  }, [clienteId])

  const cambiar = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))

  async function guardar(evento) {
    evento.preventDefault()
    setGuardando(true)
    const datos = {
      tiposVehiculo: form.tiposVehiculo,
      canales: form.canales,
      accesibilidad: form.accesibilidad,
    }
    // Las observaciones son opcionales: si están vacías, no se mandan
    if (form.observacionesAccesibilidad.trim()) {
      datos.observacionesAccesibilidad = form.observacionesAccesibilidad.trim()
    }
    try {
      await guardarPreferencias(clienteId, datos)
      notifications.show({ color: 'teal', message: 'Preferencias guardadas' })
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudieron guardar', message: e.message })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Card withBorder padding="lg">
      <Title order={4} mb="md">Preferencias de viaje</Title>
      {!form && <Group justify="center"><Loader size="sm" /></Group>}
      {form && (
        <form onSubmit={guardar}>
          <Stack>
            <SimpleGrid cols={{ base: 1, sm: 3 }}>
              <Opciones label="Vehículo" descripcion="Si no marcás ninguno, cualquiera"
                opciones={VEHICULOS} value={form.tiposVehiculo} onChange={(v) => cambiar('tiposVehiculo', v)} />
              <Opciones label="Avisos por" descripcion="Canales opcionales"
                opciones={CANALES} value={form.canales} onChange={(v) => cambiar('canales', v)} />
              <Opciones label="Accesibilidad" opciones={ACCESIBILIDAD}
                value={form.accesibilidad} onChange={(v) => cambiar('accesibilidad', v)} />
            </SimpleGrid>
            <Textarea label="Observaciones de accesibilidad" maxLength={255} autosize minRows={2}
              placeholder="Por ejemplo: necesito baúl grande para la silla"
              value={form.observacionesAccesibilidad}
              onChange={(e) => cambiar('observacionesAccesibilidad', e.target.value)} />
            <Group justify="space-between">
              <Text size="xs" c="dimmed">{form.observacionesAccesibilidad.length}/255</Text>
              <Button type="submit" loading={guardando}>Guardar preferencias</Button>
            </Group>
          </Stack>
        </form>
      )}
    </Card>
  )
}
