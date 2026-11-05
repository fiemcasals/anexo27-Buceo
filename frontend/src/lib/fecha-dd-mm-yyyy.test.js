import { describe, it, expect } from 'vitest'
import { aTexto, aIso, enmascarar } from './fecha-dd-mm-yyyy'

// La traduccion entre lo que la persona escribe (dd/mm/yyyy) y lo que la API
// habla (ISO). Va en funciones puras porque es donde un error no se ve: una
// fecha que se guarda corrida un dia, o un 31/02 que entra como valido, no
// produce ningun sintoma en la pantalla.

describe('aTexto', () => {
  const tabla = [
    ['2026-11-18', '18/11/2026'],
    ['2027-01-05', '05/01/2027'],
    ['2026-03-01', '01/03/2026'],
    ['2026-12-31', '31/12/2026'],
    [null, ''],
    [undefined, ''],
    ['', ''],
  ]

  for (const [iso, esperado] of tabla) {
    it(`${JSON.stringify(iso)} se escribe "${esperado}"`, () => {
      expect(aTexto(iso)).toBe(esperado)
    })
  }

  it('deja el cero adelante, porque dd/mm/yyyy son dos digitos', () => {
    // A diferencia del formato en palabras, aca el cero va: un campo de ancho
    // fijo que a veces tiene 8 caracteres y a veces 10 salta a la vista.
    expect(aTexto('2026-01-01')).toBe('01/01/2026')
  })

  it('no construye un Date, asi que no se corre por la zona horaria', () => {
    // `new Date('2026-01-01')` es medianoche UTC y en Argentina retrocede al
    // 31/12/2025. Es el error clasico y aca cambiaria hasta el año.
    expect(aTexto('2026-01-01')).toBe('01/01/2026')
    expect(aTexto('2026-12-31')).toBe('31/12/2026')
  })
})

describe('aIso', () => {
  it('traduce una fecha completa', () => {
    expect(aIso('18/11/2026')).toBe('2026-11-18')
  })

  it('tolera un digito en el dia y en el mes', () => {
    expect(aIso('1/1/2026')).toBe('2026-01-01')
    expect(aIso('5/11/2026')).toBe('2026-11-05')
  })

  it('tolera espacios alrededor', () => {
    expect(aIso('  18/11/2026 ')).toBe('2026-11-18')
  })

  it('acepta una fecha ISO pegada desde otro lado', () => {
    // Pasa de verdad: se copia de un correo o del admin de Django.
    expect(aIso('2026-11-18')).toBe('2026-11-18')
  })

  describe('lo que NO es una fecha devuelve null', () => {
    const invalidas = [
      ['', 'vacio'],
      ['   ', 'solo espacios'],
      [null, 'null'],
      [undefined, 'undefined'],
      ['18/11', 'sin año'],
      ['18/11/26', 'año de dos digitos'],
      ['18-11-2026', 'con guiones'],
      ['noviembre', 'palabras'],
      ['18/11/2026/01', 'de mas'],
      ['0/11/2026', 'dia cero'],
      ['18/0/2026', 'mes cero'],
      ['18/13/2026', 'mes trece'],
      ['32/01/2026', 'dia treinta y dos'],
    ]
    for (const [entrada, que] of invalidas) {
      it(`${que}: ${JSON.stringify(entrada)}`, () => {
        expect(aIso(entrada)).toBeNull()
      })
    }
  })

  describe('los dias que no existen en su mes devuelven null', () => {
    // Esta es la que de verdad importa. Un 31/02 que pasara se guardaria como
    // 2026-02-31, el servidor lo rechazaria con un 400 generico, y la persona
    // no entenderia por que.
    const imposibles = [
      ['31/02/2026', 'febrero no tiene 31'],
      ['30/02/2026', 'febrero no tiene 30'],
      ['29/02/2026', '2026 no es bisiesto'],
      ['31/04/2026', 'abril tiene 30'],
      ['31/06/2026', 'junio tiene 30'],
      ['31/09/2026', 'septiembre tiene 30'],
      ['31/11/2026', 'noviembre tiene 30'],
    ]
    for (const [entrada, que] of imposibles) {
      it(`${entrada} — ${que}`, () => {
        expect(aIso(entrada)).toBeNull()
      })
    }
  })

  it('el 29 de febrero de un año bisiesto SI existe', () => {
    expect(aIso('29/02/2028')).toBe('2028-02-29')
  })

  it('el 29 de febrero de 2100 no existe, porque 2100 no es bisiesto', () => {
    // La regla del siglo. Un calculo casero con `año % 4` lo daria por bueno.
    expect(aIso('29/02/2100')).toBeNull()
  })

  it('el 29 de febrero de 2000 existe, porque es divisible por 400', () => {
    expect(aIso('29/02/2000')).toBe('2000-02-29')
  })

  it('ida y vuelta: lo que sale de aTexto vuelve igual por aIso', () => {
    for (const iso of ['2026-11-18', '2027-01-05', '2028-02-29', '2026-12-31']) {
      expect(aIso(aTexto(iso))).toBe(iso)
    }
  })
})

describe('enmascarar', () => {
  // Las barras se ponen solas mientras se tipea, asi que nadie las escribe.
  const tabla = [
    ['', ''],
    ['1', '1'],
    ['18', '18'],
    ['181', '18/1'],
    ['1811', '18/11'],
    ['18112', '18/11/2'],
    ['18112026', '18/11/2026'],
    ['18/11/2026', '18/11/2026'],
  ]

  for (const [entrada, esperado] of tabla) {
    it(`"${entrada}" se muestra "${esperado}"`, () => {
      expect(enmascarar(entrada)).toBe(esperado)
    })
  }

  it('descarta lo que no es un digito, asi que pegar una fecha con guiones anda', () => {
    expect(enmascarar('18-11-2026')).toBe('18/11/2026')
    expect(enmascarar('18.11.2026')).toBe('18/11/2026')
  })

  it('corta en ocho digitos y no deja escribir un año de cinco cifras', () => {
    expect(enmascarar('181120267')).toBe('18/11/2026')
  })

  it('no agrega la barra antes de que haya que ponerla', () => {
    // Si la pusiera con dos digitos, borrar el ultimo dejaria "18/" y el
    // backspace se comeria la barra en lugar del numero.
    expect(enmascarar('18')).toBe('18')
    expect(enmascarar('1811')).toBe('18/11')
  })
})
