import { describe, it, expect } from 'vitest'
import {
  diaLocal, ordenInicial, ordenVigente, celdaPresentados, celdaTurno, turnoActivo,
  valorDelSelectorDeTurno, celdaUltimaRevision, estadoDeLaFila, conCambio,
  describirDictamen, estadoDelPunto, lineaDelPunto, contadoresDeLaFicha,
  renglonDelEncabezado, estadoAlAprobar, erroresDelDialogo, mensajeDelFallo,
} from './pantallas-del-revisor'

const TURNO_1 = {
  id: 1, slot: 'FIRST', slot_display: '1.ª fecha',
  start_date: '2026-11-18', end_date: '2026-11-20',
}
const TURNO_2 = {
  id: 3, slot: 'SECOND', slot_display: '2.ª fecha',
  start_date: '2026-12-05', end_date: '2026-12-05',
}

describe('diaLocal', () => {
  it('pasa a la hora local, no al día de Greenwich', () => {
    // 01:30 UTC del 6 es la noche del 5 en Argentina (TZ fijada en vitest).
    expect(diaLocal('2026-11-06T01:30:00Z')).toBe('05/11/2026')
    expect(diaLocal('2026-11-06T15:00:00Z')).toBe('06/11/2026')
  })
  it('sin fecha o con basura no devuelve "NaN"', () => {
    expect(diaLocal(null)).toBe('')
    expect(diaLocal('no es una fecha')).toBe('')
  })
})

describe('el orden', () => {
  it('el médico entra por la pila rápida y el enfermero por la cruda', () => {
    expect(ordenInicial('DOCTOR')).toBe('pila_rapida')
    expect(ordenInicial('NURSE')).toBe('pila_cruda')
  })
  it('el de la dirección manda sobre el inicial', () => {
    expect(ordenVigente({ orden: 'apellido' }, 'DOCTOR')).toBe('apellido')
    expect(ordenVigente({ orden: null }, 'NURSE')).toBe('pila_cruda')
  })
})

describe('celdaPresentados', () => {
  it('muestra presentados sobre exigidos', () => {
    expect(celdaPresentados({ presentados: 6, exigidos: 7, turno: TURNO_1 }).texto).toBe('6/7')
    expect(celdaPresentados({ presentados: 8, exigidos: 8, turno: TURNO_1 }).completo).toBe(true)
  })

  it('exigidos null nunca se lee como 0/0 ni como 8/0', () => {
    const celda = celdaPresentados({ presentados: 8, exigidos: null, turno: null })
    expect(celda.texto).toBe('8 subidos · sin turno')
    expect(celda.texto).not.toMatch(/\d\/\d/)
    expect(celda.sinDeterminar).toBe(true)
    // Y no figura como completo: no hay contra qué comparar.
    expect(celda.completo).toBe(false)
  })

  it('un solo estudio subido va en singular', () => {
    expect(celdaPresentados({ presentados: 1, exigidos: null, turno: null }).texto)
      .toBe('1 subido · sin turno')
  })

  it('con turno pero sin fecha de nacimiento no dice "sin turno"', () => {
    expect(celdaPresentados({ presentados: 3, exigidos: null, turno: TURNO_1 }).texto)
      .toBe('3 subidos · sin fecha de nacimiento')
  })
})

describe('el turno', () => {
  it('lugar y fechas en dd/mm/aaaa, nunca ISO', () => {
    expect(celdaTurno(TURNO_1)).toEqual({
      principal: '1.ª fecha', fechas: '18/11/2026 al 20/11/2026',
    })
    expect(celdaTurno(TURNO_2).fechas).toBe('05/12/2026')
  })
  it('sin turno', () => {
    expect(celdaTurno(null)).toEqual({ principal: 'Sin turno', fechas: '' })
  })

  it('el turno activo se nombra, y un id desconocido no cuenta como filtro', () => {
    const turnos = [TURNO_1, TURNO_2]
    expect(turnoActivo(3, turnos).rotulo).toBe('2.ª fecha · 05/12/2026')
    expect(turnoActivo('sin', turnos).rotulo).toBe('Sin turno')
    expect(turnoActivo(null, turnos)).toBeNull()
    // El id 99 no está en la lista: ningún filtro activo.
    expect(turnoActivo(99, turnos)).toBeNull()
    expect(valorDelSelectorDeTurno(99, turnos)).toBe('')
    expect(valorDelSelectorDeTurno(3, turnos)).toBe('3')
    expect(valorDelSelectorDeTurno('sin', turnos)).toBe('sin')
  })
})

describe('las celdas del listado', () => {
  it('la última revisión', () => {
    expect(celdaUltimaRevision('2026-10-30')).toBe('30/10/2026')
    expect(celdaUltimaRevision(null)).toBe('Sin revisar')
  })

  it('los siete estados de la fila, y uno desconocido', () => {
    const f = (estado, extra = {}) => estadoDeLaFila({ estado, vencidos: 0, rechazados: 0, ...extra })
    expect(f('APTO').texto).toBe('Apto')
    expect(f('TO_REVIEW').texto).toBe('A revisar')
    expect(f('INCOMPLETE').texto).toBe('Incompleto')
    expect(f('EXPIRED', { vencidos: 1 }).texto).toBe('1 vencido')
    expect(f('EXPIRED', { vencidos: 2 }).texto).toBe('2 vencidos')
    expect(f('REJECTED', { rechazados: 1 }).texto).toBe('1 rechazado')
    expect(f('NO_WINDOW').texto).toBe('Sin turno')
    expect(f('UNKNOWN_AGE').texto).toBe('Sin fecha de nacimiento')
    expect(f('INVENTADO').texto).toBe('Estado desconocido')
  })
})

describe('conCambio', () => {
  const base = { buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 3 }
  it('cualquier cambio de filtro vuelve a la primera página', () => {
    expect(conCambio(base, { buscar: 'mol' }).pagina).toBe(1)
    expect(conCambio(base, { filtro: 'completa' }).pagina).toBe(1)
    expect(conCambio(base, { turno: 'sin' }).pagina).toBe(1)
  })
  it('cambiar de página la respeta', () => {
    expect(conCambio(base, { pagina: 2 }).pagina).toBe(2)
  })
})

describe('describirDictamen', () => {
  const base = {
    id: 1, en_calidad_de: 'DOCTOR', por: 'Elena Médica',
    fecha: '2026-11-04T15:00:00Z', motivo: '', motivo_texto: '', detalle: '',
  }

  it('una aprobación revertida —sin motivo ni detalle— tiene texto propio', () => {
    const d = describirDictamen({ ...base, estado: 'REVERTED' })
    expect(d.titulo).toBe('Aprobación revertida por Elena Médica (médico) el 04/11/2026')
    expect(d.titulo.trim()).not.toBe('')
  })

  it('cada estado tiene su texto', () => {
    expect(describirDictamen({ ...base, estado: 'APPROVED' }).titulo)
      .toBe('Aprobado por Elena Médica (médico) el 04/11/2026')
    expect(describirDictamen({ ...base, estado: 'PRE_APPROVED', en_calidad_de: 'NURSE', por: 'Vera' }).titulo)
      .toBe('Pre-revisado por Vera (enfermero auxiliar) el 04/11/2026')
  })

  it('el rechazo trae el motivo y el detalle textuales', () => {
    const d = describirDictamen({
      ...base, estado: 'REJECTED', motivo: 'ILLEGIBLE',
      motivo_texto: 'Documento ilegible', detalle: 'Salió cortada.',
    })
    expect(d.titulo).toBe('Rechazado por Elena Médica (médico) el 04/11/2026')
    expect(d.motivo).toBe('Documento ilegible')
    expect(d.cuerpo).toBe('Salió cortada.')
  })

  it('un estado que no se conoce no queda en blanco', () => {
    const d = describirDictamen({ ...base, estado: 'OTRO' })
    expect(d.titulo).toContain('OTRO')
  })
})

describe('el estado de un punto', () => {
  it('los nueve estados tienen rótulo y uno desconocido se nombra', () => {
    for (const e of ['NOT_REQUIRED', 'MISSING', 'BEFORE_WINDOW', 'IN_REVIEW',
      'PRE_REVIEWED', 'APPROVED', 'REJECTED', 'EXPIRED', 'DATE_INVALID']) {
      expect(estadoDelPunto(e).rotulo).toBeTruthy()
    }
    expect(estadoDelPunto('NUEVO').rotulo).toBe('NUEVO')
  })

  it('la línea de un punto que no corresponde dice por qué', () => {
    expect(lineaDelPunto({
      estado: 'NOT_REQUIRED',
      motivo_no_corresponde: 'Se exige a partir de los 40 años de edad',
    })).toBe('No corresponde: se exige a partir de los 40 años de edad')
  })

  it('la línea de un punto cargado lleva fechas en dd/mm/aaaa', () => {
    const linea = lineaDelPunto({
      estado: 'IN_REVIEW', vence_el: '2027-10-12', fecha_del_estudio: '2026-10-12',
      subido_el: '2026-10-13T15:00:00Z',
    })
    expect(linea).toBe('Estudio del 12/10/2026, subido el 13/10/2026 · vigente hasta el 12/10/2027')
    expect(linea).not.toMatch(/\d{4}-\d{2}-\d{2}/)
  })

  it('un punto vencido dice cuándo venció', () => {
    expect(lineaDelPunto({
      estado: 'EXPIRED', vence_el: '2026-10-15', fecha_del_estudio: '2026-09-15',
      subido_el: '2026-09-16T15:00:00Z',
    })).toContain('venció el 15/10/2026')
  })
})

describe('el encabezado y los contadores de la ficha', () => {
  const ficha = {
    dni: '12.345.675', edad: 31, unidad: 'Base Naval', exigidos: 7,
    presentados: 6, aprobados: 2, a_revisar: 2, vencidos: 1, rechazados: 1,
  }

  it('dice cuántos estudios corresponden y la edad de la regla', () => {
    expect(renglonDelEncabezado(ficha))
      .toBe('DNI 12.345.675 · 31 años · Base Naval · Corresponden 7 de 8 estudios')
  })

  it('sin exigidos no inventa un número', () => {
    const texto = renglonDelEncabezado({ ...ficha, exigidos: null, edad: null })
    expect(texto).not.toMatch(/años/)
    expect(texto).toContain('sin determinar')
  })

  it('los cuatro contadores', () => {
    const c = contadoresDeLaFicha(ficha)
    expect(c.map(x => x.clave)).toEqual(['presentados', 'aprobados', 'a_revisar', 'problema'])
    expect(c[0]).toMatchObject({ valor: 6, de: 7 })
    expect(c[1]).toMatchObject({ valor: 2, de: 7 })
    expect(c[3].valor).toBe(2)
  })

  it('sin exigidos los contadores no llevan denominador', () => {
    const c = contadoresDeLaFicha({ ...ficha, exigidos: null })
    expect(c[0].de).toBeNull()
    expect(c[1].de).toBeNull()
  })
})

describe('estadoAlAprobar', () => {
  it('el médico aprueba y el enfermero pre-aprueba', () => {
    expect(estadoAlAprobar('DOCTOR')).toBe('APPROVED')
    expect(estadoAlAprobar('NURSE')).toBe('PRE_APPROVED')
  })
})

describe('los errores del servidor', () => {
  it('cada mensaje va en el campo que lo causó', () => {
    const e = erroresDelDialogo({
      rejection_reason: ['Todo rechazo requiere un motivo.'],
      content: ['Todo rechazo requiere un detalle para el buzo.'],
    })
    expect(e.campos.rejection_reason).toBe('Todo rechazo requiere un motivo.')
    expect(e.campos.content).toBe('Todo rechazo requiere un detalle para el buzo.')
    expect(e.general).toBe('')
  })

  it('un solo campo con error no inventa el otro', () => {
    const e = erroresDelDialogo({ content: ['Falta el detalle.'] })
    expect(e.campos.rejection_reason).toBeUndefined()
    expect(e.campos.content).toBe('Falta el detalle.')
  })

  it('lo que no es de un campo va a general', () => {
    expect(erroresDelDialogo({ detail: 'Sin permiso.' }).general).toBe('Sin permiso.')
    expect(erroresDelDialogo({ block: ['No puede.'] }).general).toBe('No puede.')
    expect(erroresDelDialogo(['Sólo se puede revertir una aprobación.']).general)
      .toBe('Sólo se puede revertir una aprobación.')
  })

  it('un cuerpo que no es JSON (el HTML de un 500) no se muestra tal cual', () => {
    expect(mensajeDelFallo({ response: { data: '<html>…</html>' } }, 'No se pudo.'))
      .toBe('No se pudo.')
    expect(mensajeDelFallo({}, 'No se pudo.')).toBe('No se pudo.')
    expect(mensajeDelFallo({ response: { data: { detail: 'Listo.' } } }, 'No se pudo.'))
      .toBe('Listo.')
  })
})
