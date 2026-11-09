import { describe, expect, it } from 'vitest'
import { nombreConGrado } from './nombre-con-grado'

describe('nombreConGrado', () => {
  it('grado, nombre y APELLIDO en mayúsculas', () => {
    expect(nombreConGrado({ grado: 'CB', nombre: 'Ana', apellido: 'Prueba' }))
      .toBe('CB Ana PRUEBA')
  })

  it('sin grado se omite, sin hueco', () => {
    expect(nombreConGrado({ grado: '', nombre: 'Ana', apellido: 'Prueba' }))
      .toBe('Ana PRUEBA')
  })

  it('las mayúsculas respetan la eñe y los acentos', () => {
    expect(nombreConGrado({ grado: 'ST', nombre: 'José', apellido: 'Muñoz Ávila' }))
      .toBe('ST José MUÑOZ ÁVILA')
  })

  it('sin apellido o sin nada cargado no rompe', () => {
    expect(nombreConGrado({ grado: 'CB', nombre: 'Ana' })).toBe('CB Ana')
    expect(nombreConGrado({})).toBe('')
    expect(nombreConGrado()).toBe('')
    expect(nombreConGrado({ grado: null, nombre: null, apellido: null })).toBe('')
  })
})
