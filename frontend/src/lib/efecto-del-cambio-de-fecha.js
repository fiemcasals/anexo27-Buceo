import { agrupar } from './agrupar-estudios'

// El grupo al que cae un estudio, derivado de `agrupar` para no repetir acá el
// mapa de los nueve estados. `agrupar` devuelve siempre los cuatro grupos, así
// que con un solo estudio exactamente uno queda lleno.
function grupoDe(estudio) {
  return agrupar([estudio]).find(grupo => grupo.estudios.length > 0).titulo
}

// §15.18: cambiar la fecha de habilitación recalcula todos los vencimientos,
// así que la pantalla tiene que mostrar el efecto y no cambiarlo en silencio.
// Compara dos respuestas de `GET /api/mi-estado/` —la de antes del cambio y la
// de después— y devuelve qué se movió. Las palabras con que se lee cada estado
// son de la pantalla: acá sólo se dice qué cambió.
//
// Compara por `estado` y no por grupo porque hay cambios que importan dentro de
// un mismo grupo: el Anexo 27 que pasa de MISSING a BEFORE_WINDOW sigue en
// "Falta subir" y, sin embargo, deja de pedir una carga.
export function efectoDelCambioDeFecha(antes, despues) {
  const anteriores = new Map((antes?.estudios ?? []).map(e => [e.code, e]))
  const cambios = []
  for (const estudio of despues?.estudios ?? []) {
    const anterior = anteriores.get(estudio.code)
    if (!anterior || anterior.estado === estudio.estado) continue
    cambios.push({
      code: estudio.code,
      texto: estudio.texto,
      estadoAntes: anterior.estado,
      estadoDespues: estudio.estado,
      grupoAntes: grupoDe(anterior),
      grupoDespues: grupoDe(estudio),
    })
  }
  return {
    faltanAntes: antes?.faltan ?? 0,
    faltanDespues: despues?.faltan ?? 0,
    cambios,
  }
}
