import { describe, it, expect } from 'vitest'
import { efectoDelCambioDeFecha } from './efecto-del-cambio-de-fecha'

const estado = (faltan, estudios) => ({ faltan, estudios })
const estudio = (code, est, texto = `Estudio ${code}`) => ({ code, texto, estado: est })

describe('efectoDelCambioDeFecha', () => {
  it('no reporta nada cuando ningún estudio cambió de estado', () => {
    const uno = estado(0, [estudio('b', 'APPROVED'), estudio('c', 'APPROVED')])
    const otro = estado(0, [estudio('b', 'APPROVED'), estudio('c', 'APPROVED')])
    expect(efectoDelCambioDeFecha(uno, otro).cambios).toEqual([])
  })

  it('reporta el estudio que la fecha nueva dejó vencido, con su grupo de antes y de después', () => {
    const antes = estado(0, [estudio('c', 'APPROVED', 'Electroencefalograma')])
    const despues = estado(1, [estudio('c', 'EXPIRED', 'Electroencefalograma')])
    expect(efectoDelCambioDeFecha(antes, despues).cambios).toEqual([{
      code: 'c',
      texto: 'Electroencefalograma',
      estadoAntes: 'APPROVED',
      estadoDespues: 'EXPIRED',
      grupoAntes: 'Revisados',
      grupoDespues: 'Falta subir',
    }])
  })

  it('reporta el cambio aunque el estudio no se mueva de grupo', () => {
    // El caso del §15.19: el Anexo 27 pasa de pedir una carga a no pedirla, y
    // los dos estados viven en "Falta subir". Comparar por grupo lo perdería.
    const antes = estado(1, [estudio('h', 'MISSING')])
    const despues = estado(0, [estudio('h', 'BEFORE_WINDOW')])
    const { cambios } = efectoDelCambioDeFecha(antes, despues)
    expect(cambios).toHaveLength(1)
    expect(cambios[0].grupoAntes).toBe('Falta subir')
    expect(cambios[0].grupoDespues).toBe('Falta subir')
    expect(cambios[0].estadoDespues).toBe('BEFORE_WINDOW')
  })

  it('lleva el contador del backend de los dos lados, sin recalcularlo', () => {
    const antes = estado(4, [estudio('b', 'MISSING')])
    const despues = estado(2, [estudio('b', 'APPROVED')])
    const efecto = efectoDelCambioDeFecha(antes, despues)
    expect(efecto.faltanAntes).toBe(4)
    expect(efecto.faltanDespues).toBe(2)
  })

  it('la primera elección de fecha también es un efecto: sale de "No corresponde"', () => {
    const antes = estado(0, [estudio('b', 'NOT_REQUIRED'), estudio('h', 'NOT_REQUIRED')])
    const despues = estado(2, [estudio('b', 'MISSING'), estudio('h', 'MISSING')])
    const { cambios } = efectoDelCambioDeFecha(antes, despues)
    expect(cambios.map(c => c.grupoAntes)).toEqual(['No corresponde', 'No corresponde'])
    expect(cambios.map(c => c.grupoDespues)).toEqual(['Falta subir', 'Falta subir'])
  })

  it('conserva el orden en que vienen los estudios, que es el de la directiva', () => {
    const antes = estado(0, ['b', 'c', 'd'].map(c => estudio(c, 'APPROVED')))
    const despues = estado(3, ['b', 'c', 'd'].map(c => estudio(c, 'EXPIRED')))
    expect(efectoDelCambioDeFecha(antes, despues).cambios.map(c => c.code))
      .toEqual(['b', 'c', 'd'])
  })

  it('ignora un punto que no estaba antes en lugar de inventarle un estado', () => {
    const antes = estado(0, [estudio('b', 'APPROVED')])
    const despues = estado(1, [estudio('b', 'APPROVED'), estudio('a', 'MISSING')])
    expect(efectoDelCambioDeFecha(antes, despues).cambios).toEqual([])
  })

  it('no se cae si falta alguna de las dos respuestas', () => {
    expect(efectoDelCambioDeFecha(null, null)).toEqual({
      faltanAntes: 0, faltanDespues: 0, cambios: [],
    })
    expect(efectoDelCambioDeFecha(undefined, estado(2, [estudio('b', 'MISSING')])).cambios)
      .toEqual([])
  })
})
