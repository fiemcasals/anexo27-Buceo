import { defineConfig } from 'vitest/config'

// Sólo la lógica pura se prueba acá. Las pantallas se verifican corriendo la
// aplicación. El entorno por defecto es node: el único módulo que necesita un
// DOM (comprimir-imagen) lo declara en su propio archivo de test.
export default defineConfig({
  test: {
    environment: 'node',
    // Fija la zona horaria para que el test de fechas cace el corrimiento de
    // un dia en cualquier maquina, incluso una que corra en UTC.
    env: { TZ: 'America/Argentina/Buenos_Aires' },
    include: ['src/**/*.test.js'],
  },
})
