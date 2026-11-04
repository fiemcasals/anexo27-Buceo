import { describe, it, expect } from 'vitest'
import { enCastellano } from './fecha-castellano'

describe('enCastellano', () => {
  it('escribe el mes con palabras, como pide el §8.3', () => {
    expect(enCastellano('2027-10-12')).toBe('12 de octubre de 2027')
  })

  it('no mete el cero adelante en los dias de un digito', () => {
    expect(enCastellano('2027-01-05')).toBe('5 de enero de 2027')
  })

  it('no se corre un dia por la zona horaria', () => {
    // Una fecha ISO suelta en new Date() se interpreta como UTC y en
    // Argentina (UTC-3) retrocede un dia. Es el error clasico.
    expect(enCastellano('2027-03-01')).toBe('1 de marzo de 2027')
  })

  it('devuelve cadena vacia con null, para que la pantalla no imprima "undefined"', () => {
    expect(enCastellano(null)).toBe('')
  })

  it('escribe los doce meses, cada uno con su nombre (escritos a mano)', () => {
    const esperados = {
      '2027-01-15': '15 de enero de 2027',
      '2027-02-15': '15 de febrero de 2027',
      '2027-03-15': '15 de marzo de 2027',
      '2027-04-15': '15 de abril de 2027',
      '2027-05-15': '15 de mayo de 2027',
      '2027-06-15': '15 de junio de 2027',
      '2027-07-15': '15 de julio de 2027',
      '2027-08-15': '15 de agosto de 2027',
      '2027-09-15': '15 de septiembre de 2027',
      '2027-10-15': '15 de octubre de 2027',
      '2027-11-15': '15 de noviembre de 2027',
      '2027-12-15': '15 de diciembre de 2027',
    }
    for (const [iso, texto] of Object.entries(esperados)) {
      expect(enCastellano(iso)).toBe(texto)
    }
  })

  it('no se corre en los bordes del año, donde un desfase de zona cambiaria el año', () => {
    expect(enCastellano('2027-01-01')).toBe('1 de enero de 2027')
    expect(enCastellano('2027-12-31')).toBe('31 de diciembre de 2027')
  })

  it('devuelve cadena vacia con undefined y con cadena vacia', () => {
    expect(enCastellano(undefined)).toBe('')
    expect(enCastellano('')).toBe('')
  })
})
