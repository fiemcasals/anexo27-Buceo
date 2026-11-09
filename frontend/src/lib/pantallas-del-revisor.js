// Lo que dicen las dos pantallas del revisor (el listado y la ficha), como
// funciones puras: así se prueba lo que la pantalla *dice* sin montarla.
//
// Todos los textos son impersonales (§10) y toda fecha sale en dd/mm/aaaa.

import { aTexto } from './fecha-dd-mm-yyyy'

// ---------------------------------------------------------------------------
// Fechas
// ---------------------------------------------------------------------------

/** Un instante con zona (`2026-11-05T21:30:00Z`) a su día **local**, en
 *  dd/mm/aaaa. `subida_mas_vieja_sin_dictamen` y la fecha de un dictamen vienen
 *  en UTC: cortar el texto en la `T` mostraría el día de Greenwich, que de noche
 *  es el de mañana. */
export function diaLocal(instante) {
  if (!instante) return ''
  const fecha = new Date(instante)
  if (Number.isNaN(fecha.getTime())) return ''
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  return `${dia}/${mes}/${fecha.getFullYear()}`
}

// ---------------------------------------------------------------------------
// El listado
// ---------------------------------------------------------------------------

export const FILTROS = [
  { clave: 'todos', rotulo: 'Todos' },
  { clave: 'completa', rotulo: 'Documentación completa' },
  { clave: 'incompleta', rotulo: 'Documentación incompleta' },
  { clave: 'pendientes', rotulo: 'Pendientes de revisar' },
]

export const ORDENES = [
  { clave: 'apellido', rotulo: 'Apellido' },
  { clave: 'ultima_revision', rotulo: 'Última vez revisado' },
  { clave: 'pendientes', rotulo: 'Más pendientes' },
  { clave: 'pila_rapida', rotulo: 'Pre-revisado por enfermero' },
  { clave: 'pila_cruda', rotulo: 'Sin revisar por nadie' },
  { clave: 'grado_antiguo', rotulo: 'Grado (más antiguo)' },
  { clave: 'grado_moderno', rotulo: 'Grado (más moderno)' },
]

/** El orden con el que se entra: el médico a la pila rápida, lo pre-revisado
 *  que espera su firma; el enfermero a la cruda, lo que nadie tocó. */
export function ordenInicial(role) {
  return role === 'NURSE' ? 'pila_cruda' : 'pila_rapida'
}

/** El orden que rige: el de la dirección, o el inicial del rol. */
export function ordenVigente(filtros, role) {
  return filtros.orden || ordenInicial(role)
}

/** Lo que dice la celda "Presentados".
 *
 *  `exigidos` es `null` cuando no se puede determinar (sin turno, o sin fecha
 *  de nacimiento). Ahí NO se escribe "8/0" ni "0/0": un buzo que subió los ocho
 *  papeles sin inscribirse leería como alguien que no presentó nada. Se dice
 *  cuántos subió y qué falta para poder contar. */
export function celdaPresentados(fila) {
  if (fila.exigidos === null || fila.exigidos === undefined) {
    const n = fila.presentados
    const subidos = `${n} ${n === 1 ? 'subido' : 'subidos'}`
    // Sin turno es la causa casi siempre; con turno, lo que falta es la fecha
    // de nacimiento, y decir "sin turno" contradiría la columna de al lado.
    const falta = fila.turno ? 'sin fecha de nacimiento' : 'sin turno'
    return { texto: `${subidos} · ${falta}`, sinDeterminar: true, completo: false }
  }
  return {
    texto: `${fila.presentados}/${fila.exigidos}`,
    sinDeterminar: false,
    completo: fila.presentados >= fila.exigidos,
  }
}

/** La columna "Turno": el lugar en el ciclo y las fechas, o "Sin turno". */
export function celdaTurno(turno) {
  if (!turno) return { principal: 'Sin turno', fechas: '' }
  const inicio = aTexto(turno.start_date)
  const fin = aTexto(turno.end_date)
  return {
    principal: turno.slot_display,
    fechas: inicio === fin ? inicio : `${inicio} al ${fin}`,
  }
}

/** La opción que se muestra en el desplegable del filtro de turno. */
export function rotuloDelTurno(turno) {
  const { principal, fechas } = celdaTurno(turno)
  return fechas ? `${principal} · ${fechas}` : principal
}

/** El turno activo del filtro, por su nombre; `null` si el filtro no está
 *  puesto **o** si su id no está en la lista de turnos.
 *
 *  Que un id desconocido no cuente como filtro activo es lo que evita que el
 *  médico vea "no hay nadie" sin entender por qué: la pantalla no puede decir
 *  que filtra por algo que no sabe nombrar. */
export function turnoActivo(turnoDelFiltro, turnos) {
  if (turnoDelFiltro === null || turnoDelFiltro === undefined) return null
  if (turnoDelFiltro === 'sin') return { id: 'sin', rotulo: 'Sin turno' }
  const turno = turnos.find(t => t.id === turnoDelFiltro)
  return turno ? { id: turno.id, rotulo: rotuloDelTurno(turno) } : null
}

/** El valor del `<select>` de turno: lo que la pantalla puede nombrar. */
export function valorDelSelectorDeTurno(turnoDelFiltro, turnos) {
  const activo = turnoActivo(turnoDelFiltro, turnos)
  return activo ? String(activo.id) : ''
}

/** La columna "Última vez revisado": sólo dictámenes del médico. */
export function celdaUltimaRevision(iso) {
  return iso ? aTexto(iso) : 'Sin revisar'
}

const PLURAL = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

/** La etiqueta de estado de una fila: texto y tono. El estado lo deriva el
 *  servidor; acá sólo se nombra. Un estado desconocido no deja la celda en
 *  blanco. */
export function estadoDeLaFila(fila) {
  switch (fila.estado) {
    case 'APTO':
      return { texto: 'Apto', tono: 'ok', conTilde: true }
    case 'TO_REVIEW':
      return { texto: 'A revisar', tono: 'aviso' }
    case 'INCOMPLETE':
      return { texto: 'Incompleto', tono: 'neutro' }
    case 'EXPIRED':
      return { texto: PLURAL(fila.vencidos, 'vencido', 'vencidos'), tono: 'peligro' }
    case 'REJECTED':
      return { texto: PLURAL(fila.rechazados, 'rechazado', 'rechazados'), tono: 'peligro' }
    case 'NO_WINDOW':
      return { texto: 'Sin turno', tono: 'neutro' }
    case 'UNKNOWN_AGE':
      return { texto: 'Sin fecha de nacimiento', tono: 'neutro' }
    default:
      return { texto: 'Estado desconocido', tono: 'neutro' }
  }
}

/** Cuántos buzos hay en lo que se mira, para el subtítulo. */
export function subtituloDelListado(total) {
  if (total === 0) return 'Ningún buzo coincide con lo buscado'
  return PLURAL(total, 'buzo', 'buzos')
}

/** Los filtros a partir de lo que cambió: toda modificación que no sea la
 *  página vuelve a la primera. Cambiar el buscador estando en la página 3 y
 *  quedarse en la 3 muestra una página vacía o ajena. */
export function conCambio(filtros, cambio) {
  const nuevo = { ...filtros, ...cambio }
  if (!('pagina' in cambio)) nuevo.pagina = 1
  return nuevo
}

// ---------------------------------------------------------------------------
// La ficha
// ---------------------------------------------------------------------------

const ROL = { DOCTOR: 'médico', NURSE: 'enfermero auxiliar' }

function quienYCuando(dictamen) {
  const rol = ROL[dictamen.en_calidad_de]
  const por = rol ? `${dictamen.por} (${rol})` : dictamen.por
  const dia = diaLocal(dictamen.fecha)
  return `por ${por}${dia ? ` el ${dia}` : ''}`
}

/** Un dictamen como se lee en la fila: un título y, si lo hay, un detalle.
 *
 *  Un `REVERTED` no tiene motivo ni detalle —es un dictamen sin contenido—, y
 *  en una lista que sólo mostrara el contenido sería una fila en blanco: la
 *  ficha diría que no pasó nada, cuando lo que pasó es que el médico deshizo
 *  una aprobación. Por eso cada estado tiene su texto, y uno que no se conozca
 *  también: nunca se devuelve vacío. */
export function describirDictamen(dictamen) {
  const cuando = quienYCuando(dictamen)
  switch (dictamen.estado) {
    case 'APPROVED':
      return { titulo: `Aprobado ${cuando}`, detalle: '', tono: 'ok' }
    case 'PRE_APPROVED':
      return { titulo: `Pre-revisado ${cuando}`, detalle: '', tono: 'neutro' }
    case 'REJECTED': {
      const partes = [dictamen.motivo_texto, dictamen.detalle].filter(Boolean)
      return {
        titulo: `Rechazado ${cuando}`,
        detalle: partes.join('. '),
        // El motivo va aparte para que la pantalla lo resalte.
        motivo: dictamen.motivo_texto || '',
        cuerpo: dictamen.detalle || '',
        tono: 'peligro',
      }
    }
    case 'REVERTED':
      return { titulo: `Aprobación revertida ${cuando}`, detalle: '', tono: 'aviso' }
    default:
      return { titulo: `Dictamen "${dictamen.estado}" ${cuando}`, detalle: '', tono: 'neutro' }
  }
}

const NOMBRE_DE_ESTADO = {
  NOT_REQUIRED: { rotulo: 'No corresponde', tono: 'apagado' },
  MISSING: { rotulo: 'Falta', tono: 'neutro' },
  BEFORE_WINDOW: { rotulo: 'Todavía no se puede presentar', tono: 'neutro' },
  IN_REVIEW: { rotulo: 'En revisión', tono: 'aviso' },
  PRE_REVIEWED: { rotulo: 'Pre-revisado', tono: 'info' },
  APPROVED: { rotulo: 'Aprobado', tono: 'ok' },
  REJECTED: { rotulo: 'Rechazado', tono: 'peligro' },
  EXPIRED: { rotulo: 'Vencido', tono: 'peligro' },
  DATE_INVALID: { rotulo: 'Fecha inválida', tono: 'peligro' },
}

/** El rótulo y el tono del estado de un punto. Un estado desconocido se nombra
 *  tal cual en lugar de dejar el punto sin rótulo. */
export function estadoDelPunto(estado) {
  return NOMBRE_DE_ESTADO[estado] || { rotulo: String(estado), tono: 'neutro' }
}

/** La línea de debajo del título de un punto: qué se sabe de la carga. */
export function lineaDelPunto(estudio) {
  switch (estudio.estado) {
    case 'NOT_REQUIRED':
      return `No corresponde: ${minuscula(estudio.motivo_no_corresponde)}`
    case 'MISSING':
      return 'No presentado'
    case 'BEFORE_WINDOW':
      return estudio.desde_cuando
        ? `No presentado. Se puede presentar desde el ${aTexto(estudio.desde_cuando)}`
        : 'No presentado'
    case 'EXPIRED':
      return `${presentado(estudio)} · venció el ${aTexto(estudio.vence_el)}`
    case 'DATE_INVALID':
      return `${presentado(estudio)} · la fecha del estudio no es válida para el turno elegido`
    default:
      return estudio.vence_el
        ? `${presentado(estudio)} · vigente hasta el ${aTexto(estudio.vence_el)}`
        : presentado(estudio)
  }
}

function presentado(estudio) {
  const subido = diaLocal(estudio.subido_el)
  const hecho = aTexto(estudio.fecha_del_estudio)
  if (subido && hecho) return `Estudio del ${hecho}, subido el ${subido}`
  return subido ? `Subido el ${subido}` : 'Presentado'
}

function minuscula(texto) {
  if (!texto) return 'no se exige para este buzo'
  return texto.charAt(0).toLowerCase() + texto.slice(1)
}

/** Los cuatro contadores de la ficha. */
export function contadoresDeLaFicha(ficha) {
  const exigidos = ficha.exigidos
  const conDenominador = (n) => (exigidos === null ? { valor: n, de: null } : { valor: n, de: exigidos })
  return [
    { clave: 'presentados', rotulo: 'Presentados', ...conDenominador(ficha.presentados) },
    { clave: 'aprobados', rotulo: 'Aprobados', ...conDenominador(ficha.aprobados) },
    { clave: 'a_revisar', rotulo: 'A revisar', valor: ficha.a_revisar, de: null },
    { clave: 'problema', rotulo: 'Con problema', valor: ficha.vencidos + ficha.rechazados, de: null },
  ]
}

/** El renglón de datos del encabezado. La edad es la que usó la regla. */
export function renglonDelEncabezado(ficha) {
  const partes = []
  if (ficha.dni) partes.push(`DNI ${ficha.dni}`)
  if (ficha.edad !== null && ficha.edad !== undefined) partes.push(`${ficha.edad} años`)
  if (ficha.unidad) partes.push(ficha.unidad)
  partes.push(ficha.exigidos === null
    ? 'Estudios exigidos sin determinar'
    : `Corresponden ${ficha.exigidos} de 8 estudios`)
  return partes.join(' · ')
}

// Los cuatro motivos de `Comment.REJECTION_REASONS` (api/models.py), con los
// mismos códigos y los mismos textos. El servidor rechaza cualquier otro código.
export const MOTIVOS_DE_RECHAZO = [
  { codigo: 'OUT_OF_TERM', texto: 'Estudio fuera del plazo de la directiva' },
  { codigo: 'UNFIT_VALUES', texto: 'Valores no aptos para realizar la actividad' },
  { codigo: 'ILLEGIBLE', texto: 'Documento ilegible' },
  { codigo: 'OTHER', texto: 'Otros' },
]

/** Qué estado manda al aprobar: el médico aprueba; el enfermero auxiliar
 *  pre-aprueba y su aprobación deja el estudio pre-revisado. El backend rechaza
 *  la combinación contraria con un 400, y la pantalla no debe ofrecerla. */
export function estadoAlAprobar(role) {
  return role === 'DOCTOR' ? 'APPROVED' : 'PRE_APPROVED'
}

// ---------------------------------------------------------------------------
// Los errores del servidor
// ---------------------------------------------------------------------------

function unTexto(valor) {
  if (Array.isArray(valor)) return valor.map(unTexto).filter(Boolean).join(' ')
  if (valor && typeof valor === 'object') return Object.values(valor).map(unTexto).join(' ')
  return valor ? String(valor) : ''
}

/** Un 400 de DRF a mensajes por campo.
 *
 *  El rechazo sin motivo o sin detalle vuelve como `{rejection_reason: [...]}`
 *  o `{content: [...]}`: cada mensaje va junto al campo que lo causó y no en un
 *  cartel genérico. Lo que no es de ninguno de los campos del diálogo (un
 *  `detail`, un `non_field_errors`, un error de otro campo, un cuerpo que no es
 *  un objeto) va a `general`. */
export function erroresDelDialogo(datos, campos = ['rejection_reason', 'content']) {
  const salida = { campos: {}, general: '' }
  if (datos && typeof datos === 'object' && !Array.isArray(datos)) {
    const generales = []
    for (const [clave, valor] of Object.entries(datos)) {
      const texto = unTexto(valor)
      if (!texto) continue
      if (campos.includes(clave)) salida.campos[clave] = texto
      else generales.push(texto)
    }
    salida.general = generales.join(' ')
  } else {
    salida.general = unTexto(datos)
  }
  return salida
}

/** El mensaje de un fallo cualquiera: el del servidor si lo trae legible, y si
 *  no, el de reserva. Un 500 trae HTML (con DEBUG) y no se muestra tal cual. */
export function mensajeDelFallo(error, reserva) {
  const datos = error?.response?.data
  if (datos && typeof datos === 'object') {
    const texto = erroresDelDialogo(datos, []).general
    if (texto) return texto
  }
  return reserva
}
