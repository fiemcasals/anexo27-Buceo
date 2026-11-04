import { describe, it, expect } from 'vitest'
import { rangoEnCastellano } from './rango-de-fechas'

describe('rangoEnCastellano', () => {
  it('escribe la 1.ª fecha sembrada sin repetir el mes ni el año', () => {
    expect(rangoEnCastellano('2026-11-18', '2026-11-20'))
      .toBe('Del 18 al 20 de noviembre de 2026')
  })

  it('un rango de un solo día no se escribe como rango', () => {
    expect(rangoEnCastellano('2026-11-18', '2026-11-18')).toBe('El 18 de noviembre de 2026')
  })

  it('repite el mes cuando el rango lo cruza, y el año una sola vez', () => {
    expect(rangoEnCastellano('2026-11-28', '2026-12-02'))
      .toBe('Del 28 de noviembre al 2 de diciembre de 2026')
  })

  it('escribe los dos años cuando el rango cruza el año', () => {
    expect(rangoEnCastellano('2026-12-28', '2027-01-02'))
      .toBe('Del 28 de diciembre de 2026 al 2 de enero de 2027')
  })

  it('no inventa nada si falta alguna de las dos fechas', () => {
    expect(rangoEnCastellano(null, '2026-11-20')).toBe('')
    expect(rangoEnCastellano('2026-11-18', null)).toBe('')
    expect(rangoEnCastellano(null, null)).toBe('')
  })

  it('no deja el cero adelante en el día ni en el mes', () => {
    // '2026-03-01' a mano daría 'Del 01 al 09 de marzo', que no se escribe así.
    expect(rangoEnCastellano('2026-03-01', '2026-03-09'))
      .toBe('Del 1 al 9 de marzo de 2026')
  })

  it('no corre un día por la zona horaria, como no lo corre enCastellano', () => {
    // `new Date('2026-11-18')` se lee como UTC y en Argentina retrocede al 17.
    expect(rangoEnCastellano('2026-11-18', '2026-11-20')).toContain('Del 18 ')
  })
})
