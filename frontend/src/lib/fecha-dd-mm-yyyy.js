// La traducción entre lo que la persona escribe y lo que la API habla.
//
// Existe porque `<input type="date">` lo dibuja el navegador con **su** idioma
// y no con el de la página: con Chrome en inglés el campo muestra mm/dd/yyyy y
// no hay CSS ni atributo que lo cambie. Para que diga dd/mm/yyyy hay que poner
// un campo de texto propio, y entonces la conversión queda de este lado.
//
// Ninguna de las tres funciones construye un `Date` a partir de la cadena ISO.
// `new Date('2026-01-01')` es medianoche UTC, y en Argentina (UTC−3) retrocede
// al 31/12/2025: cambiaría hasta el año.

const DIAS_POR_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

function esBisiesto(anio) {
  // La regla completa, con la excepción del siglo: 2100 no es bisiesto aunque
  // sea divisible por 4. Un cálculo casero con sólo `% 4` acepta el 29/02/2100.
  return (anio % 4 === 0 && anio % 100 !== 0) || anio % 400 === 0
}

function diasDelMes(anio, mes) {
  if (mes === 2 && esBisiesto(anio)) return 29
  return DIAS_POR_MES[mes - 1]
}

/** ISO a lo que se muestra: '2026-11-18' → '18/11/2026'. Vacío si no hay fecha. */
export function aTexto(iso) {
  if (!iso) return ''
  const [anio, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${anio}`
}

/** Lo que se escribió a ISO, o `null` si no es una fecha que exista.
 *
 * Devolver `null` y no una cadena a medias es lo que hace que un 31 de febrero
 * no llegue al servidor: si pasara, se guardaría `2026-02-31`, volvería un 400
 * genérico, y la persona no entendería qué está mal en lo que escribió.
 *
 * Tolera un dígito en el día y en el mes, espacios alrededor, y una fecha ISO
 * pegada desde otro lado (pasa de verdad: se copia del admin de Django).
 */
export function aIso(texto) {
  if (!texto) return null
  const limpio = String(texto).trim()
  if (!limpio) return null

  // Se indexa en lugar de desestructurar: una asignación que empieza con `[`
  // se parsea como un índice de la expresión anterior y rompe el archivo.
  let anio, mes, dia
  const iso = limpio.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (iso) {
    anio = iso[1]
    mes = iso[2]
    dia = iso[3]
  } else {
    const partes = limpio.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
    if (!partes) return null
    dia = partes[1]
    mes = partes[2]
    anio = partes[3]
  }

  anio = Number(anio)
  mes = Number(mes)
  dia = Number(dia)
  if (mes < 1 || mes > 12) return null
  if (dia < 1 || dia > diasDelMes(anio, mes)) return null

  return `${String(anio).padStart(4, '0')}-${String(mes).padStart(2, '0')}-${String(dia).padStart(2, '0')}`
}

/** Lo que se ve en el campo mientras se tipea: las barras se ponen solas.
 *
 * Descarta todo lo que no sea un dígito, así que pegar `18-11-2026` o
 * `18.11.2026` también funciona, y corta en ocho dígitos para que no entre un
 * año de cinco cifras.
 *
 * La barra se agrega recién cuando hay un dígito después, no al completar dos:
 * si apareciera antes, el campo quedaría en `18/` y el backspace se comería la
 * barra en lugar del número.
 */
export function enmascarar(texto) {
  const digitos = String(texto || '').replace(/\D/g, '').slice(0, 8)
  if (digitos.length <= 2) return digitos
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`
}
