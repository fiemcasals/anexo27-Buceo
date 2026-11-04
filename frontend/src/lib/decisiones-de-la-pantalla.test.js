import { describe, it, expect } from 'vitest'
import {
  llevaBoton, estaCompleto, oracionDelContador, cuantosFaltan,
} from './decisiones-de-la-pantalla'

// Todo está escrito a mano a propósito: un test que derive los estados o los
// resultados de la constante que prueba pasaría con la constante equivocada.

describe('llevaBoton', () => {
  it('cada uno de los nueve estados, con su resultado escrito a mano', () => {
    const esperado = {
      MISSING: true,
      REJECTED: true,
      EXPIRED: true,
      DATE_INVALID: true,
      BEFORE_WINDOW: false,
      IN_REVIEW: false,
      PRE_REVIEWED: false,
      APPROVED: false,
      NOT_REQUIRED: false,
    }
    expect(Object.keys(esperado)).toHaveLength(9)
    for (const [estado, boton] of Object.entries(esperado)) {
      expect(llevaBoton({ estado }), estado).toBe(boton)
    }
  })

  it('el BEFORE_WINDOW no lleva botón (§15.19) aunque puede_reemplazarse sea true', () => {
    // El endpoint devuelve puede_reemplazarse en true para todo punto sin carga.
    expect(llevaBoton({ estado: 'BEFORE_WINDOW', puede_reemplazarse: true })).toBe(false)
  })

  it('un estado desconocido no lleva botón', () => {
    expect(llevaBoton({ estado: 'INVENTADO' })).toBe(false)
  })
})

const est = (estado, extra = {}) => ({ code: 'x', estado, ...extra })

describe('estaCompleto', () => {
  it('sin faltantes y sin puntos fuera de ventana, está completo', () => {
    expect(estaCompleto({ faltan: 0, estudios: [est('APPROVED'), est('IN_REVIEW'), est('NOT_REQUIRED')] }))
      .toBe(true)
  })

  it('con faltantes no está completo', () => {
    expect(estaCompleto({ faltan: 2, estudios: [est('MISSING'), est('MISSING')] })).toBe(false)
  })

  it('con un punto fuera de ventana no está completo, aunque faltan sea 0 (caso "ventana")', () => {
    expect(estaCompleto({ faltan: 0, estudios: [est('APPROVED'), est('BEFORE_WINDOW')] })).toBe(false)
  })

  it('con todos los puntos fuera de ventana (fecha a más de un año) no está completo', () => {
    const estudios = Array.from({ length: 7 }, () => est('BEFORE_WINDOW'))
    expect(estaCompleto({ faltan: 0, total_exigidos: 7, revisados: 0, estudios })).toBe(false)
  })
})

describe('oracionDelContador', () => {
  it('completo: dice que no queda nada por subir', () => {
    expect(oracionDelContador({ faltan: 0, estudios: [est('APPROVED')] })).toBe(
      'No queda ningún estudio por subir. Se notificará por correo la aptitud para '
      + 'presentarse a la habilitación.')
  })

  it('con faltantes, habla de subir y revisar', () => {
    expect(oracionDelContador({ faltan: 1, estudios: [est('MISSING')] })).toBe(
      'Una vez subidos y revisados, se notificará por correo la aptitud para '
      + 'presentarse a la habilitación.')
  })

  it('con un punto fuera de ventana, dice lo cierto y la fecha en castellano', () => {
    const t = oracionDelContador({
      faltan: 0,
      estudios: [est('APPROVED'), est('BEFORE_WINDOW', { desde_cuando: '2027-05-18' })],
    })
    expect(t).toBe('Queda 1 estudio que todavía no se puede presentar. '
      + 'Se puede presentar a partir del 18 de mayo de 2027.')
    expect(t).not.toContain('No queda ningún')
  })

  it('con varios, dice cuántos y la fecha más próxima', () => {
    const t = oracionDelContador({
      faltan: 0,
      estudios: [
        est('BEFORE_WINDOW', { desde_cuando: '2027-12-01' }),
        est('BEFORE_WINDOW', { desde_cuando: '2027-05-18' }),
        est('BEFORE_WINDOW', { desde_cuando: '2027-09-30' }),
      ],
    })
    expect(t).toBe('Quedan 3 estudios que todavía no se pueden presentar. '
      + 'El primero se puede presentar a partir del 18 de mayo de 2027.')
  })

  it('si el punto no trae la fecha, no inventa una', () => {
    expect(oracionDelContador({ faltan: 0, estudios: [est('BEFORE_WINDOW')] }))
      .toBe('Queda 1 estudio que todavía no se puede presentar.')
  })
})

describe('cuantosFaltan', () => {
  it('singular, plural y cero', () => {
    expect(cuantosFaltan(1)).toBe('Falta 1 estudio')
    expect(cuantosFaltan(3)).toBe('Faltan 3 estudios')
    expect(cuantosFaltan(0)).toBe('Faltan 0 estudios')
  })
})
