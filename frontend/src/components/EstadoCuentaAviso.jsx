// Aviso de cuenta bloqueada (RF-2.6): si un operador bloqueó al cliente, le mostramos por qué y hasta cuándo.
// Con la cuenta activa no muestra nada. Bloquear y levantar bloqueos lo hace un OPERADOR, no desde esta pantalla.
import { useEffect, useState } from 'react'
import { Alert, List, Text } from '@mantine/core'

import { obtenerEstadoCuenta } from '../api'

const formato = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' })

export default function EstadoCuentaAviso({ clienteId, estado }) {
  const [bloqueos, setBloqueos] = useState([])

  // Se vuelve a consultar cuando cambia el estado del perfil (por ejemplo, al guardar cambios)
  useEffect(() => {
    if (estado !== 'BLOQUEADO') {
      setBloqueos([])
      return
    }
    obtenerEstadoCuenta(clienteId)
      .then((datos) => setBloqueos(datos.bloqueosVigentes))
      .catch(() => setBloqueos([])) // si falla, igual queda el aviso general de abajo
  }, [clienteId, estado])

  if (estado !== 'BLOQUEADO') return null

  return (
    <Alert color="red" variant="light" title="Tu cuenta está bloqueada">
      <Text size="sm" mb={bloqueos.length ? 'xs' : 0}>
        Por ahora no podés pedir ni reservar viajes. Si creés que es un error, comunicate con soporte.
      </Text>
      {bloqueos.length > 0 && (
        <List size="sm" spacing={4}>
          {bloqueos.map((b) => (
            <List.Item key={b.bloqueoId}>
              {b.motivo}
              <Text span size="sm" c="dimmed">
                {b.hasta ? ` · hasta el ${formato.format(new Date(b.hasta))}` : ' · hasta que se levante'}
              </Text>
            </List.Item>
          ))}
        </List>
      )}
    </Alert>
  )
}
