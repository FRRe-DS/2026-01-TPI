// Formulario del perfil: datos personales del cliente, con los campos del contrato
// (nombre, apellido, teléfono y fecha de nacimiento).
// Las direcciones frecuentes y las preferencias tienen sus propias operaciones en el contrato;
// se vuelven a agregar al front en la etapa 2.
// Se usa tanto para crear como para editar; recibe los datos iniciales en "inicial".
import { useState } from 'react'
import { Button, Card, Group, SimpleGrid, Stack, TextInput, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'

// Formato E.164: +, código de país y número, sin espacios. Ej: +5493624000000
const FORMATO_TELEFONO = /^\+[1-9][0-9]{6,14}$/

function estadoInicial(inicial) {
  return {
    nombre: inicial?.nombre ?? '',
    apellido: inicial?.apellido ?? '',
    telefono: inicial?.telefono ?? '',
    fechaNacimiento: inicial?.fechaNacimiento ?? '',
  }
}

export default function ClienteForm({ inicial, textoBoton, onGuardar }) {
  const [form, setForm] = useState(() => estadoInicial(inicial))
  const [guardando, setGuardando] = useState(false)

  const cambiar = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))

  // Sacamos espacios y guiones que la gente suele escribir en el teléfono
  const telefonoLimpio = form.telefono.replace(/[\s-]/g, '')
  const telefonoInvalido = telefonoLimpio !== '' && !FORMATO_TELEFONO.test(telefonoLimpio)

  async function enviar(evento) {
    evento.preventDefault()
    if (telefonoInvalido) return
    setGuardando(true)
    try {
      await onGuardar({
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        telefono: telefonoLimpio,
        // La fecha es opcional: si está vacía, no se manda
        fechaNacimiento: form.fechaNacimiento || undefined,
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
        <Card withBorder padding="lg">
          <Title order={4} mb="md">Datos personales</Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput label="Nombre" required maxLength={100} value={form.nombre}
              onChange={(e) => cambiar('nombre', e.target.value)} />
            <TextInput label="Apellido" required maxLength={100} value={form.apellido}
              onChange={(e) => cambiar('apellido', e.target.value)} />
            <TextInput label="Teléfono" required placeholder="+5493624000000"
              description="Con + y código de país, sin espacios"
              error={telefonoInvalido ? 'Usá el formato +5493624000000' : null}
              value={form.telefono}
              onChange={(e) => cambiar('telefono', e.target.value)} />
            <TextInput label="Fecha de nacimiento" type="date"
              description={inicial?.fechaNacimiento ? 'Una vez cargada, se puede cambiar pero no borrar' : 'Opcional'}
              value={form.fechaNacimiento}
              onChange={(e) => cambiar('fechaNacimiento', e.target.value)} />
          </SimpleGrid>
        </Card>

        <Group justify="flex-end">
          <Button type="submit" loading={guardando}>{textoBoton}</Button>
        </Group>
      </Stack>
    </form>
  )
}
