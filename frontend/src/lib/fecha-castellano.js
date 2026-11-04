const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

// '2027-10-12' -> '12 de octubre de 2027'. Se parte la cadena a mano y no con
// new Date(iso): una fecha ISO suelta se interpreta como UTC y en Argentina
// (UTC-3) retrocede un día, así que el resultado dependería de la zona horaria
// de la máquina.
export function enCastellano(iso) {
  if (!iso) return ''
  const [anio, mes, dia] = iso.split('-')
  return `${Number(dia)} de ${MESES[Number(mes) - 1]} de ${Number(anio)}`
}
