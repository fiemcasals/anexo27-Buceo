import { describe, it, expect } from 'vitest'
import {
  LUGARES,
  textoDeFecha,
  filaDeRol,
  loQueSeManda,
} from './decisiones-del-administrador'

// Estas cuatro cosas deciden lo que el administrador ve y lo que el servidor
// recibe. Van en funciones puras y con tabla escrita a mano porque el defecto
// mas grave del plan 2 fue justamente una decision de presentacion sin test:
// un recuadro verde que decia "no falta nada" cuando faltaba todo.

describe('los tres lugares del ciclo', () => {
  it('son tres y en el orden del ciclo', () => {
    expect(LUGARES).toEqual(['FIRST', 'SECOND', 'COMPLEMENTARY'])
  })
})

describe('textoDeFecha', () => {
  // La distincion que importa: "no la cargue todavia" tiene que leerse
  // distinto de una fecha. Un ciclo incompleto es el estado normal, asi que
  // esto se ve todos los dias.
  const tabla = [
    [null, 'Sin cargar'],
    [undefined, 'Sin cargar'],
    ['', 'Sin cargar'],
    ['2026-11-18', '18/11/2026'],
    ['2027-04-20', '20/04/2027'],
    ['2027-08-05', '05/08/2027'],
  ]

  for (const [entrada, esperado] of tabla) {
    it(`${JSON.stringify(entrada)} se muestra como "${esperado}"`, () => {
      expect(textoDeFecha(entrada)).toBe(esperado)
    })
  }

  it('no usa el reloj del navegador para formatear', () => {
    // Un `new Date('2026-11-18')` se interpreta en UTC y al mostrarlo en
    // Buenos Aires (UTC-3) retrocede un dia: el administrador carga el 18 y
    // la pantalla le dice 17. Por eso se parte la cadena en lugar de
    // construir una fecha.
    expect(textoDeFecha('2026-01-01')).toBe('01/01/2026')
    expect(textoDeFecha('2026-12-31')).toBe('31/12/2026')
  })
})

describe('filaDeRol', () => {
  const designados = {
    DOCTOR: [{ email: 'doc@ara.mil.ar', nombre: 'Ferreyra, Elena', rank: 'CT' }],
    NURSE: [],
  }

  it('trae la gente designada', () => {
    expect(filaDeRol(designados, 'DOCTOR').gente).toHaveLength(1)
  })

  it('un rol sin nadie se marca vacio y NO queda como una fila en blanco', () => {
    // La falla que esto ataja: una fila vacia es indistinguible de una lista
    // que no cargo, y el administrador concluye que ya designo al enfermero.
    const fila = filaDeRol(designados, 'NURSE')
    expect(fila.vacia).toBe(true)
    expect(fila.gente).toEqual([])
  })

  it('una llave que no vino se trata como vacia y no revienta', () => {
    expect(filaDeRol({}, 'DOCTOR').vacia).toBe(true)
    expect(filaDeRol(null, 'DOCTOR').vacia).toBe(true)
  })

  it('un rol con gente no esta vacio', () => {
    expect(filaDeRol(designados, 'DOCTOR').vacia).toBe(false)
  })
})

describe('loQueSeManda', () => {
  const original = { FIRST: '2026-11-18', SECOND: null, COMPLEMENTARY: null }

  it('manda solo el lugar que cambio', () => {
    const editado = { ...original, SECOND: '2027-04-20' }
    expect(loQueSeManda(2026, editado, original)).toEqual({
      cycle: 2026,
      SECOND: '2027-04-20',
    })
  })

  it('manda los tres cuando cambiaron los tres', () => {
    const editado = {
      FIRST: '2026-11-25',
      SECOND: '2027-04-20',
      COMPLEMENTARY: '2027-08-05',
    }
    expect(loQueSeManda(2026, editado, original)).toEqual({
      cycle: 2026,
      FIRST: '2026-11-25',
      SECOND: '2027-04-20',
      COMPLEMENTARY: '2027-08-05',
    })
  })

  it('sin cambios devuelve null, y asi el boton no manda un PUT vacio', () => {
    // Un PUT sin ninguna fecha da 400 en el servidor. Si el boton lo mandara
    // igual, el administrador veria un error rojo por no haber tocado nada.
    expect(loQueSeManda(2026, { ...original }, original)).toBeNull()
  })

  it('vaciar un input NO se manda, porque en blanco no significa borrar', () => {
    // Borrar una fecha desinscribe a todos los buzos anotados en ella. No
    // puede ser el efecto de que alguien seleccione el contenido y apriete
    // backspace.
    const editado = { ...original, FIRST: '' }
    expect(loQueSeManda(2026, editado, original)).toBeNull()
  })

  it('vaciar uno y cargar otro manda solo el que se cargo', () => {
    const editado = { FIRST: '', SECOND: '2027-04-20', COMPLEMENTARY: null }
    expect(loQueSeManda(2026, editado, original)).toEqual({
      cycle: 2026,
      SECOND: '2027-04-20',
    })
  })

  it('el ciclo viaja siempre, porque identifica que año se esta cargando', () => {
    const editado = { ...original, FIRST: '2030-11-18' }
    expect(loQueSeManda(2030, editado, original).cycle).toBe(2030)
  })

  it('re-escribir el mismo valor no es un cambio', () => {
    const editado = { ...original, FIRST: '2026-11-18' }
    expect(loQueSeManda(2026, editado, original)).toBeNull()
  })
})
