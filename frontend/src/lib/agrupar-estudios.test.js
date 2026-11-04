import { describe, it, expect, vi } from 'vitest'
import { agrupar } from './agrupar-estudios'

// Los títulos y la pertenencia de cada estado están escritos a mano acá, a
// propósito: un test que los derive de la constante que prueba pasaría con el
// mapa equivocado.
const TITULOS = ['Falta subir', 'En revisión', 'Revisados', 'No corresponde']

describe('agrupar', () => {
  it('devuelve los cuatro grupos en el orden del §8.3', () => {
    expect(agrupar([]).map(g => g.titulo)).toEqual(TITULOS)
  })

  it('el vencido y el rechazado van a "Falta subir", porque hay algo que hacer', () => {
    const grupos = agrupar([{ code: 'b', estado: 'EXPIRED' }, { code: 'c', estado: 'REJECTED' }])
    expect(grupos[0].estudios.map(e => e.code)).toEqual(['b', 'c'])
  })

  it('el BEFORE_WINDOW va en "Falta subir" (el §15.19 le quita el rojo y el boton, no el grupo)', () => {
    expect(agrupar([{ code: 'h', estado: 'BEFORE_WINDOW' }])[0].estudios.map(e => e.code))
      .toEqual(['h'])
  })

  it('no deja ningun estado afuera de los cuatro grupos', () => {
    // Si manana se agrega un StudyState, este test lo caza antes que un buzo
    const todos = ['NOT_REQUIRED', 'MISSING', 'BEFORE_WINDOW', 'IN_REVIEW', 'PRE_REVIEWED',
                   'APPROVED', 'REJECTED', 'EXPIRED', 'DATE_INVALID']
    const agrupados = agrupar(todos.map((estado, i) => ({ code: String(i), estado })))
    expect(agrupados.flatMap(g => g.estudios).length).toBe(todos.length)
  })

  it('el que no corresponde va al cuarto grupo y no desaparece', () => {
    const grupos = agrupar([{ code: 'a', estado: 'NOT_REQUIRED' }])
    expect(grupos[3].estudios.map(e => e.code)).toEqual(['a'])
  })

  it('cada uno de los nueve estados cae en el grupo que le toca (tabla escrita a mano)', () => {
    const esperado = {
      MISSING: 'Falta subir',
      REJECTED: 'Falta subir',
      EXPIRED: 'Falta subir',
      DATE_INVALID: 'Falta subir',
      BEFORE_WINDOW: 'Falta subir',
      IN_REVIEW: 'En revisión',
      PRE_REVIEWED: 'En revisión',
      APPROVED: 'Revisados',
      NOT_REQUIRED: 'No corresponde',
    }
    expect(Object.keys(esperado)).toHaveLength(9)
    for (const [estado, titulo] of Object.entries(esperado)) {
      const grupos = agrupar([{ code: 'x', estado }])
      const donde = grupos.filter(g => g.estudios.length > 0).map(g => g.titulo)
      expect(donde, estado).toEqual([titulo])
    }
  })

  it('siempre devuelve los cuatro grupos, con los vacios vacios', () => {
    const grupos = agrupar([{ code: 'a', estado: 'APPROVED' }])
    expect(grupos).toHaveLength(4)
    expect(grupos.map(g => g.estudios.length)).toEqual([0, 0, 1, 0])
  })

  it('conserva el orden en que llegan los estudios dentro de cada grupo', () => {
    const grupos = agrupar([
      { code: '3', estado: 'MISSING' },
      { code: '1', estado: 'BEFORE_WINDOW' },
      { code: '2', estado: 'EXPIRED' },
    ])
    expect(grupos[0].estudios.map(e => e.code)).toEqual(['3', '1', '2'])
  })

  it('devuelve los mismos objetos de estudio, sin copiarlos ni recortarlos', () => {
    const estudio = { code: 'a', estado: 'IN_REVIEW', texto: 'Hemograma', rechazo: null }
    expect(agrupar([estudio])[1].estudios[0]).toBe(estudio)
  })

  it('un estado desconocido cae en "Falta subir" y deja rastro, sin tumbar la pantalla', () => {
    const espia = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const grupos = agrupar([{ code: 'z', estado: 'INVENTADO' }, { code: 'y', estado: 'APPROVED' }])
      expect(grupos[0].titulo).toBe('Falta subir')
      expect(grupos[0].estudios.map(e => e.code)).toEqual(['z'])
      expect(grupos[2].estudios.map(e => e.code)).toEqual(['y'])
      expect(espia).toHaveBeenCalled()
      expect(String(espia.mock.calls[0][0])).toContain('INVENTADO')
    } finally {
      espia.mockRestore()
    }
  })
})
