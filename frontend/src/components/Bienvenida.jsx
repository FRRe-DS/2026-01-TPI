// Pantalla de bienvenida: es lo primero que ve quien no inició sesión.
// Los botones llevan a Keycloak (que hace de M1): el usuario y la contraseña se escriben siempre
// en la pantalla de Keycloak, nunca en la nuestra (OpenID Connect con PKCE).
// "Crear cuenta" necesita el registro de usuarios activado en el realm (Realm settings → Login → User registration).
import { useState } from 'react'
import {
  Badge, Box, Button, Container, Group, Paper, SimpleGrid, Stack, Text, ThemeIcon, Title,
} from '@mantine/core'

import keycloak from '../keycloak'

const FUNCIONES = [
  { letra: '1', titulo: 'Tu perfil', texto: 'Tus datos de contacto, siempre al día.' },
  { letra: '2', titulo: 'Direcciones frecuentes', texto: 'Casa, trabajo o la facu, listas para pedir un viaje.' },
  { letra: '3', titulo: 'Tus preferencias', texto: 'Auto o moto, cómo te avisamos y qué accesibilidad necesitás.' },
]

export default function Bienvenida() {
  const [yendo, setYendo] = useState(null) // 'ingresar' | 'registrar' mientras redirige

  function ir(accion) {
    setYendo(accion)
    // Al volver de Keycloak, el usuario aterriza de nuevo en esta página, ya con sesión
    const opciones = { redirectUri: window.location.origin }
    const destino = accion === 'registrar' ? keycloak.register(opciones) : keycloak.login(opciones)
    destino.catch(() => setYendo(null))
  }

  return (
    <Box mih="100vh" style={{ display: 'flex', alignItems: 'center' }} bg="var(--mantine-color-body)">
      <Container size="lg" py={48} w="100%">
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing={48} verticalSpacing={40} style={{ alignItems: 'center' }}>
          <Stack gap="lg">
            <Badge variant="light" size="lg" w="fit-content">Movilidad · Clientes</Badge>
            <Title order={1} fz={{ base: 34, sm: 44 }} lh={1.1}>
              Viajá a donde quieras, como te gusta.
            </Title>
            <Text size="lg" c="dimmed" maw={460}>
              Creá tu cuenta para guardar tus datos, tus lugares de siempre y tus preferencias de viaje.
            </Text>
            <Group gap="sm" mt="sm">
              <Button size="md" onClick={() => ir('registrar')} loading={yendo === 'registrar'} disabled={yendo === 'ingresar'}>
                Crear cuenta
              </Button>
              <Button size="md" variant="default" onClick={() => ir('ingresar')} loading={yendo === 'ingresar'} disabled={yendo === 'registrar'}>
                Ya tengo cuenta, ingresar
              </Button>
            </Group>
            <Text size="sm" c="dimmed">
              El ingreso es seguro: tu contraseña la maneja el servicio de identidad de la plataforma, no esta página.
            </Text>
          </Stack>

          <Stack gap="md">
            {FUNCIONES.map((f) => (
              <Paper key={f.titulo} withBorder radius="md" p="lg">
                <Group wrap="nowrap" align="flex-start" gap="md">
                  <ThemeIcon size={40} radius="xl" variant="light">
                    <Text fw={700}>{f.letra}</Text>
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>{f.titulo}</Text>
                    <Text size="sm" c="dimmed">{f.texto}</Text>
                  </div>
                </Group>
              </Paper>
            ))}
          </Stack>
        </SimpleGrid>
      </Container>
    </Box>
  )
}
