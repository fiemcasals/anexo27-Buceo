const FALTA_SUBIR = 'Falta subir'
const EN_REVISION = 'En revisión'
const REVISADOS = 'Revisados'
const NO_CORRESPONDE = 'No corresponde'

// Orden de los grupos en pantalla (§8.3).
const GRUPOS = [FALTA_SUBIR, EN_REVISION, REVISADOS, NO_CORRESPONDE]

// Los nueve nombres de StudyState (api/fitness.py), explícitos y sin heurística
// sobre el nombre. BEFORE_WINDOW está en "Falta subir" pero NO cuenta en el
// "Faltan N" (§15.19): eso es presentación, y lo decide la pantalla.
const GRUPO_DE = {
  MISSING: FALTA_SUBIR,
  REJECTED: FALTA_SUBIR,
  EXPIRED: FALTA_SUBIR,
  DATE_INVALID: FALTA_SUBIR,
  BEFORE_WINDOW: FALTA_SUBIR,
  IN_REVIEW: EN_REVISION,
  PRE_REVIEWED: EN_REVISION,
  APPROVED: REVISADOS,
  NOT_REQUIRED: NO_CORRESPONDE,
}

// Devuelve siempre los cuatro grupos, en orden, aunque alguno quede vacío.
// Un estado que el mapa no conoce cae en "Falta subir" y se deja rastro: tirar
// un error le dejaría la pantalla en blanco al buzo. "Revisados" afirmaría una
// aprobación que no existe y "En revisión" lo dejaría esperando algo que no va
// a pasar; "Falta subir" lo mantiene visible y accionable. El guardia es el test
// de los nueve estados, que se pone rojo en desarrollo.
export function agrupar(estudios) {
  const grupos = GRUPOS.map(titulo => ({ titulo, estudios: [] }))
  for (const estudio of estudios) {
    let titulo = GRUPO_DE[estudio.estado]
    if (!titulo) {
      console.error(`Estado de estudio desconocido: ${estudio.estado}`)
      titulo = FALTA_SUBIR
    }
    grupos.find(g => g.titulo === titulo).estudios.push(estudio)
  }
  return grupos
}
