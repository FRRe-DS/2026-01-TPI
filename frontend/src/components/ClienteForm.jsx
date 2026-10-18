// Formulario del perfil: datos personales, direcciones frecuentes y preferencias.
// Se usa tanto para crear como para editar; recibe los datos iniciales en "inicial".
import { useState } from 'react'
import {
  ActionIcon, Button, Card, Checkbox, Group, Select, SimpleGrid, Stack, Switch, Text, TextInput, Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import keycloak from '../keycloak'

const DIRECCION_VACIA = { etiqueta: '', calle: '', numero: '', ciudad: '', es_principal: false }

// Arma el estado del formulario a partir del cliente guardado (o vacío si es nuevo)
function estadoInicial(inicial) {
  return {
    nombre: inicial?.nombre ?? '',
    apellido: inicial?.apellido ?? '',
    // Si es un perfil nuevo, proponemos el email con el que inició sesión en Keycloak
    email: inicial?.email ?? keycloak.tokenParsed?.email ?? '',
    telefono: inicial?.telefono ?? '',
    direcciones: inicial?.direcciones ?? [],
    preferencias: {
      viaje_silencioso: inicial?.preferencias?.viaje_silencioso ?? false,
      temperatura_aire: inicial?.preferencias?.temperatura_aire ?? 'Media',
      musica: inicial?.preferencias?.musica ?? '',
    },
  }
}

export default function ClienteForm({ inicial, textoBoton, onGuardar }) {
  const [form, setForm] = useState(() => estadoInicial(inicial))
  const [guardando, setGuardando] = useState(false)

  // Helpers para actualizar una parte del formulario
  const cambiar = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))
  const cambiarPreferencia = (campo, valor) =>
    setForm((f) => ({ ...f, preferencias: { ...f.preferencias, [campo]: valor } }))
  const cambiarDireccion = (indice, campo, valor) =>
    setForm((f) => ({
      ...f,
      direcciones: f.direcciones.map((d, i) => {
        if (campo === 'es_principal') {
          // Solo una dirección puede ser la principal
          return { ...d, es_principal: i === indice ? valor : false }
        }
        return i === indice ? { ...d, [campo]: valor } : d
      }),
    }))
  const agregarDireccion = () =>
    setForm((f) => ({ ...f, direcciones: [...f.direcciones, { ...DIRECCION_VACIA }] }))
  const quitarDireccion = (indice) =>
    setForm((f) => ({ ...f, direcciones: f.direcciones.filter((_, i) => i !== indice) }))

  async function enviar(evento) {
    evento.preventDefault()
    setGuardando(true)
    try {
      await onGuardar({
        ...form,
        // "musica" vacío se manda como null, como espera la API
        preferencias: { ...form.preferencias, musica: form.preferencias.musica || null },
      })
    } catch (e) {
      notifications.show({ color: 'red', title: 'No se pudo guardar', message: e.message })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar}>
      <Stack>
        {/* Datos personales */}
        <Card withBorder padding="lg">
          <Title order={4} mb="md">Datos personales</Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput label="Nombre" required value={form.nombre}
              onChange={(e) => cambiar('nombre', e.target.value)} />
            <TextInput label="Apellido" required value={form.apellido}
              onChange={(e) => cambiar('apellido', e.target.value)} />
            <TextInput label="Email" type="email" required value={form.email}
              onChange={(e) => cambiar('email', e.target.value)} />
            <TextInput label="Teléfono" required value={form.telefono}
              onChange={(e) => cambiar('telefono', e.target.value)} />
          </SimpleGrid>
        </Card>

        {/* Direcciones frecuentes */}
        <Card withBorder padding="lg">
          <Group justify="space-between" mb="md">
            <Title order={4}>Direcciones frecuentes</Title>
            <Button variant="light" size="xs" onClick={agregarDireccion}>+ Agregar dirección</Button>
          </Group>

          {form.direcciones.length === 0 && (
            <Text c="dimmed" size="sm">No cargaste direcciones. Agregá tu casa, tu trabajo o la facu.</Text>
          )}

          <Stack>
            {form.direcciones.map((d, i) => (
              <Card key={i} withBorder padding="md" bg="var(--mantine-color-default-hover)">
                <SimpleGrid cols={{ base: 1, sm: 4 }}>
                  <TextInput label="Etiqueta" placeholder="Casa" required value={d.etiqueta}
                    onChange={(e) => cambiarDireccion(i, 'etiqueta', e.target.value)} />
                  <TextInput label="Calle" required value={d.calle}
                    onChange={(e) => cambiarDireccion(i, 'calle', e.target.value)} />
                  <TextInput label="Número" required value={d.numero}
                    onChange={(e) => cambiarDireccion(i, 'numero', e.target.value)} />
                  <TextInput label="Ciudad" required value={d.ciudad}
                    onChange={(e) => cambiarDireccion(i, 'ciudad', e.target.value)} />
                </SimpleGrid>
                <Group justify="space-between" mt="sm">
                  <Checkbox label="Dirección principal" checked={d.es_principal}
                    onChange={(e) => cambiarDireccion(i, 'es_principal', e.currentTarget.checked)} />
                  <ActionIcon variant="subtle" color="red" aria-label="Quitar dirección"
                    onClick={() => quitarDireccion(i)}>
                    ✕
                  </ActionIcon>
                </Group>
              </Card>
            ))}
          </Stack>
        </Card>

        {/* Preferencias de viaje */}
        <Card withBorder padding="lg">
          <Title order={4} mb="md">Preferencias de viaje</Title>
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <Select
              label="Temperatura del aire"
              data={['Fría', 'Media', 'Cálida']}
              value={form.preferencias.temperatura_aire}
              onChange={(valor) => cambiarPreferencia('temperatura_aire', valor ?? 'Media')}
              allowDeselect={false}
            />
            <TextInput label="Música" placeholder="Rock, sin música…" value={form.preferencias.musica}
              onChange={(e) => cambiarPreferencia('musica', e.target.value)} />
            <Switch label="Prefiero viajar en silencio" mt={{ base: 0, sm: 32 }}
              checked={form.preferencias.viaje_silencioso}
              onChange={(e) => cambiarPreferencia('viaje_silencioso', e.currentTarget.checked)} />
          </SimpleGrid>
        </Card>

        <Group justify="flex-end">
          <Button type="submit" loading={guardando}>{textoBoton}</Button>
        </Group>
      </Stack>
    </form>
  )
}
