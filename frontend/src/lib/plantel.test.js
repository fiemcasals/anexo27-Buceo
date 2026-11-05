import { describe, expect, it } from 'vitest'
import { escribirFiltros, leerFiltros } from './plantel'

describe('filtros del plantel en la dirección', () => {
  it('una dirección vacía da los valores de arranque', () => {
    expect(leerFiltros('')).toEqual(
      { buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 1 })
  })

  it('ida y vuelta: lo que escribe vuelve igual', () => {
    const f = { buscar: 'gómez', filtro: 'pendientes', turno: 3, orden: 'apellido', pagina: 2 }
    expect(leerFiltros(escribirFiltros(f))).toEqual(f)
  })

  it('no escribe lo que está en su valor de arranque, para no ensuciar la dirección', () => {
    expect(escribirFiltros({ buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 1 }))
      .toBe('')
  })

  it('una página o un filtro inventados caen en el valor de arranque', () => {
    expect(leerFiltros('?pagina=cero&filtro=inventado'))
      .toMatchObject({ pagina: 1, filtro: 'todos' })
  })

  it('el turno "sin" sobrevive, que no es un número', () => {
    expect(leerFiltros('?turno=sin').turno).toBe('sin')
  })

  it('el turno "sin" también vuelve de ida y vuelta', () => {
    const f = { buscar: '', filtro: 'todos', turno: 'sin', orden: null, pagina: 1 }
    expect(leerFiltros(escribirFiltros(f))).toEqual(f)
  })

  it('un orden o un turno inventados caen en el valor de arranque', () => {
    expect(leerFiltros('?orden=inventado&turno=abc'))
      .toMatchObject({ orden: null, turno: null })
  })
})
