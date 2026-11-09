// Los filtros del listado del plantel, guardados en la dirección de la página.
//
// Viven en la dirección y no en memoria porque el médico filtra, abre la ficha
// de un buzo, lo dictamina y vuelve: con el "volver" del navegador los filtros
// se restituyen solos, y además se puede compartir o guardar una vista.
//
// El backend normaliza por su cuenta lo que llegue mal; esto es la segunda red,
// y hace que los controles de la pantalla muestren el estado correcto.

const FILTROS = ['todos', 'completa', 'incompleta', 'pendientes']
const ORDENES = ['apellido', 'ultima_revision', 'pendientes', 'pila_rapida', 'pila_cruda',
  'grado_antiguo', 'grado_moderno']

const ARRANQUE = { buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 1 }

function leerTurno(valor) {
  // 'sin' (buzos sin turno) no es un número: un parseInt ciego lo volvería NaN.
  if (valor === 'sin') return 'sin'
  if (valor && /^\d+$/.test(valor) && Number.isSafeInteger(Number(valor))) return Number(valor)
  return ARRANQUE.turno
}

function leerPagina(valor) {
  if (valor && /^\d+$/.test(valor) && Number.isSafeInteger(Number(valor)) && Number(valor) >= 1) return Number(valor)
  return ARRANQUE.pagina
}

/** De la dirección (`location.search`) a los filtros; lo inválido cae en el arranque. */
export function leerFiltros(search) {
  const p = new URLSearchParams(search || '')
  const filtro = p.get('filtro')
  const orden = p.get('orden')
  return {
    buscar: p.get('buscar') || ARRANQUE.buscar,
    filtro: FILTROS.includes(filtro) ? filtro : ARRANQUE.filtro,
    turno: leerTurno(p.get('turno')),
    orden: ORDENES.includes(orden) ? orden : ARRANQUE.orden,
    pagina: leerPagina(p.get('pagina')),
  }
}

/** De los filtros a la cadena de la dirección, sin lo que está en su arranque.
 *  Devuelve '' si todo está por defecto, o '?...' en otro caso. */
export function escribirFiltros(filtros) {
  const p = new URLSearchParams()
  for (const clave of Object.keys(ARRANQUE)) {
    const valor = filtros[clave]
    if (valor === undefined || valor === null || valor === ARRANQUE[clave]) continue
    p.set(clave, String(valor))
  }
  const texto = p.toString()
  return texto ? `?${texto}` : ''
}
