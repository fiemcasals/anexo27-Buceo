import { describe, it, expect } from 'vitest'
import { primerMensajeDelCuerpo } from './primer-mensaje-del-cuerpo'

describe('primerMensajeDelCuerpo', () => {
  it('el rechazo atado a study_code (caso real del reemplazo) se muestra', () => {
    expect(primerMensajeDelCuerpo({
      study_code: ['El estudio ya fue revisado por el médico y no puede reemplazarse.'],
    })).toBe('El estudio ya fue revisado por el médico y no puede reemplazarse.')
  })

  it('prefiere non_field_errors y detail sobre un campo cualquiera', () => {
    expect(primerMensajeDelCuerpo({ otro: ['b'], non_field_errors: ['a'] })).toBe('a')
    expect(primerMensajeDelCuerpo({ otro: ['b'], detail: 'c' })).toBe('c')
  })

  it('toma el primer mensaje cuando hay varios', () => {
    expect(primerMensajeDelCuerpo({ x: ['uno', 'dos'], y: ['tres'] })).toBe('uno')
  })

  it('cuerpo vacío o sin texto devuelve cadena vacía, para que valga el genérico', () => {
    expect(primerMensajeDelCuerpo({})).toBe('')
    expect(primerMensajeDelCuerpo({ x: [] })).toBe('')
    expect(primerMensajeDelCuerpo(null)).toBe('')
    expect(primerMensajeDelCuerpo('<html>')).toBe('')
  })

  it('un valor anidado no se vuelve "[object Object]"', () => {
    expect(primerMensajeDelCuerpo({ x: { y: ['anidado'] } })).toBe('anidado')
  })
})
