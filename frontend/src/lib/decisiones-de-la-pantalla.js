import { enCastellano } from './fecha-castellano'

// §15.19: el botón de subir sale del ESTADO del punto y no de
// `puede_reemplazarse`, que responde otra pregunta —si el servidor dejaría
// pisar lo que ya hay— y viene en `true` para todo punto sin carga, incluidos
// el que no corresponde y el que todavía no se puede presentar. Atarlo a ese
// campo le pondría botón de subir al Anexo 27 once meses antes de que exista
// un papel que subir. BEFORE_WINDOW NO está acá, a propósito: es lo que prohíbe
// el §15.19 y lo que cuida el test de este archivo.
const ESTADOS_QUE_LLEVAN_BOTON = ['MISSING', 'REJECTED', 'EXPIRED', 'DATE_INVALID']

// Si el punto lleva el botón de subir un estudio.
export function llevaBoton(estudio) {
  return ESTADOS_QUE_LLEVAN_BOTON.includes(estudio.estado)
}

// Los puntos que todavía no se pueden presentar.
export function fueraDeVentana(estado) {
  return estado.estudios.filter(e => e.estado === 'BEFORE_WINDOW')
}

// "Completo" afirma que no queda nada por subir. `faltan` no cuenta los puntos
// fuera de ventana (no son una deuda del buzo), así que por sí solo no alcanza:
// con la ventana a más de un año todos los puntos caen en BEFORE_WINDOW y
// `faltan` da 0 sin que se haya presentado nada.
export function estaCompleto(estado) {
  return estado.faltan === 0 && fueraDeVentana(estado).length === 0
}

// "Faltan 1 estudio" no se escribe así. El vocabulario del §8.3 es
// "Faltan N estudios" y el singular es la única forma que cambia; el cero va en
// plural, que en castellano es lo correcto.
export function cuantosFaltan(faltan) {
  return faltan === 1 ? 'Falta 1 estudio' : `Faltan ${faltan} estudios`
}

// La oración bajo el número grande del contador. Dice lo que es cierto: con
// puntos fuera de ventana y nada más por subir, no dice que no queda nada.
export function oracionDelContador(estado) {
  if (estado.faltan > 0) {
    return 'Una vez subidos y revisados, se notificará por correo la aptitud para '
      + 'presentarse a la habilitación.'
  }
  const fuera = fueraDeVentana(estado)
  if (fuera.length === 0) {
    return 'No queda ningún estudio por subir. Se notificará por correo la aptitud para '
      + 'presentarse a la habilitación.'
  }
  // Las fechas ISO se ordenan como texto; la más próxima es la menor.
  const fechas = fuera.map(e => e.desde_cuando).filter(Boolean).sort()
  const desde = fechas.length > 0 ? enCastellano(fechas[0]) : null
  if (fuera.length === 1) {
    return 'Queda 1 estudio que todavía no se puede presentar.'
      + (desde ? ` Se puede presentar a partir del ${desde}.` : '')
  }
  return `Quedan ${fuera.length} estudios que todavía no se pueden presentar.`
    + (desde ? ` El primero se puede presentar a partir del ${desde}.` : '')
}
