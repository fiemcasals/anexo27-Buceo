import { enCastellano } from './fecha-castellano'

// '18 de noviembre de 2026' -> '18 de noviembre'. Se recorta el año en lugar de
// repetir acá la tabla de meses de `fecha-castellano`.
function sinAnio(texto) {
  return texto.slice(0, texto.lastIndexOf(' de '))
}

// Una fecha de habilitación es un rango de días (§4.1), y en la pantalla del
// buzo se lee en castellano, nunca como '18/11/2026 al 20/11/2026'. Se evita
// repetir el mes y el año cuando son los mismos, porque el rango es de tres
// días y escribirlo entero dos veces lo vuelve ilegible.
//
//   mismo día            -> 'El 18 de noviembre de 2026'
//   mismo mes y año      -> 'Del 18 al 20 de noviembre de 2026'
//   mismo año            -> 'Del 28 de noviembre al 2 de diciembre de 2026'
//   años distintos       -> 'Del 28 de diciembre de 2026 al 2 de enero de 2027'
export function rangoEnCastellano(inicio, fin) {
  if (!inicio || !fin) return ''
  const [anioInicio, mesInicio, diaInicio] = inicio.split('-')
  const [anioFin, mesFin] = fin.split('-')
  if (inicio === fin) return `El ${enCastellano(fin)}`
  if (anioInicio === anioFin && mesInicio === mesFin) {
    return `Del ${Number(diaInicio)} al ${enCastellano(fin)}`
  }
  if (anioInicio === anioFin) {
    return `Del ${sinAnio(enCastellano(inicio))} al ${enCastellano(fin)}`
  }
  return `Del ${enCastellano(inicio)} al ${enCastellano(fin)}`
}
