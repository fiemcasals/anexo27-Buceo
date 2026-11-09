import { describe, expect, it } from 'vitest'
import { escribirFiltros, leerFiltros } from './plantel'
import { ORDENES } from './pantallas-del-revisor'

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

  it('la página cero o negativa cae en la primera', () => {
    expect(leerFiltros('?pagina=0').pagina).toBe(1)
    expect(leerFiltros('?pagina=-2').pagina).toBe(1)
  })

  it('un número con dígitos de más no se acepta: Infinity o 1e20 romperían la ida y vuelta', () => {
    const enorme = '9'.repeat(309)
    expect(leerFiltros(`?pagina=${enorme}`).pagina).toBe(1)
    expect(leerFiltros(`?turno=${enorme}`).turno).toBeNull()
    expect(leerFiltros('?pagina=99999999999999999999').pagina).toBe(1)
    expect(leerFiltros('?turno=99999999999999999999').turno).toBeNull()
  })

  it('una página que no es un entero escrito en decimal cae en la primera', () => {
    for (const malo of ['1.5', '', '1abc', '-1', '0x10']) {
      expect(leerFiltros(`?pagina=${malo}`).pagina).toBe(1)
    }
  })

  it('un turno que no es un entero escrito en decimal cae en el arranque', () => {
    for (const malo of ['-1', '1.5', '0x10', '1abc', '']) {
      expect(leerFiltros(`?turno=${malo}`).turno).toBeNull()
    }
  })
})

describe('los órdenes por grado y las pilas', () => {
  it('los dos órdenes por grado viajan en la dirección y vuelven iguales', () => {
    for (const orden of ['grado_antiguo', 'grado_moderno']) {
      const f = { buscar: '', filtro: 'todos', turno: null, orden, pagina: 1 }
      expect(leerFiltros(escribirFiltros(f))).toEqual(f)
    }
  })

  it('el desplegable ofrece los dos grados y las pilas con su nombre nuevo', () => {
    const rotulos = Object.fromEntries(ORDENES.map(o => [o.clave, o.rotulo]))
    expect(rotulos.grado_antiguo).toBe('Grado (más antiguo)')
    expect(rotulos.grado_moderno).toBe('Grado (más moderno)')
    expect(rotulos.pila_rapida).toBe('Pre-revisado por enfermero')
    expect(rotulos.pila_cruda).toBe('Sin revisar por nadie')
  })
})
