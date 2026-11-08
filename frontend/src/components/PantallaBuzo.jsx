import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import Soporte from './Soporte'
import { agrupar } from '../lib/agrupar-estudios'
import {
  llevaBoton, estaCompleto, oracionDelContador, cuantosFaltan,
} from '../lib/decisiones-de-la-pantalla'
import { enCastellano } from '../lib/fecha-castellano'
import { rangoEnCastellano } from '../lib/rango-de-fechas'
import { efectoDelCambioDeFecha } from '../lib/efecto-del-cambio-de-fecha'
import CargarEstudio from './CargarEstudio'
import BarraLateral from './BarraLateral'

// Los que piden una corrección se enmarcan en rojo. "Sin presentar" no: es una
// tarea pendiente, no un problema, y pintar todo de rojo entrena a ignorarlo.
const ESTADOS_CON_PROBLEMA = ['REJECTED', 'EXPIRED', 'DATE_INVALID']

// Cómo se lee cada estado en una línea, para el panel del efecto del cambio de
// fecha. IN_REVIEW y PRE_REVIEWED dicen lo mismo a propósito (§15.12): el buzo
// no tiene que ver la diferencia entre el enfermero y el médico.
const ESTADO_EN_PALABRAS = {
  MISSING: 'Sin presentar',
  BEFORE_WINDOW: 'Todavía no se puede presentar',
  IN_REVIEW: 'En revisión',
  PRE_REVIEWED: 'En revisión',
  APPROVED: 'Revisado',
  REJECTED: 'No aprobado',
  EXPIRED: 'Vencido',
  DATE_INVALID: 'Con la fecha fuera del período',
  NOT_REQUIRED: 'No corresponde',
}

const ERROR_AL_TRAER = 'No se pudo traer el estado de los estudios.'

const ROJO = 'var(--peligro-texto)'
const BORDE_PROBLEMA = 'var(--peligro-borde)'
const BORDE_NEUTRO = 'var(--borde)'
const BORDE_REVISADO = 'var(--ok-borde)'
const VERDE = 'var(--ok)'

function enPalabras(estado) {
  return ESTADO_EN_PALABRAS[estado] || estado
}

function Titulo({ children }) {
  return (
    <div className="text-uppercase fw-bold ps-1 mb-2"
         style={{ fontSize: '11px', color: 'var(--texto-suave)', letterSpacing: '.7px' }}>
      {children}
    </div>
  )
}

function BotonDeSubir({ onClick, children }) {
  return (
    <button type="button" className="btn w-100 fw-bold mt-3 py-3"
            style={{ borderRadius: '11px', background: '#E5AA19', borderColor: '#E5AA19', color: '#1B2024' }}
            onClick={onClick}>
      {children}
    </button>
  )
}

// --- La fecha de habilitación, primero (§8.3, §4.1) -------------------------

function BloqueDeFecha({ estado, onElegir }) {
  const elegida = estado.fecha_elegida

  if (elegida) {
    return (
      <div className="bg-white rounded-3 px-3 py-2 mb-2 d-flex align-items-center gap-2 flex-wrap"
           style={{ border: `1px solid ${BORDE_NEUTRO}` }}
           title="La vigencia de cada estudio se evalúa contra esta fecha.">
        <div className="flex-grow-1" style={{ minWidth: '200px' }}>
          <div className="text-uppercase fw-bold"
               style={{ fontSize: '10.5px', color: 'var(--texto-suave)', letterSpacing: '.7px' }}>
            Fecha de habilitación
          </div>
          <div style={{ fontSize: '13.5px', color: 'var(--texto-fuerte)' }}>
            <strong>{elegida.slot_display}</strong>
            <span style={{ color: 'var(--texto-suave)' }}>
              {' · '}{rangoEnCastellano(elegida.start_date, elegida.end_date)}
            </span>
          </div>
        </div>
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onElegir}>
          Cambiar
        </button>
      </div>
    )
  }

  // Sin fecha elegida y con fechas publicadas: elegir es la acción principal de
  // la pantalla, por encima de los estudios, porque sin fecha no hay contra qué
  // calcular nada.
  if (estado.hay_fechas_para_elegir) {
    return (
      <div className="rounded-3 px-3 py-2 mb-2 d-flex align-items-center gap-2 flex-wrap"
           style={{ background: 'var(--info-fondo)', border: '1px solid var(--info-borde)' }}>
        <div className="flex-grow-1" style={{ minWidth: '200px' }}>
          <div className="fw-bold" style={{ fontSize: '14px', color: 'var(--texto-fuerte)' }}>
            Falta elegir la fecha de habilitación
          </div>
          <div style={{ fontSize: '12px', lineHeight: 1.4, color: 'var(--info)' }}>
            Sin ella no se pueden calcular los estudios exigidos ni sus vencimientos.
          </div>
        </div>
        <button type="button" className="btn btn-sm fw-bold" onClick={onElegir}
                style={{ background: '#E5AA19', borderColor: '#E5AA19', color: '#1B2024' }}>
          Elegir la fecha
        </button>
      </div>
    )
  }

  // §15.21: no eligió porque no hay nada que elegir. No se le reprocha.
  return (
    <div className="rounded-3 px-3 py-2 mb-2"
         style={{ background: 'var(--borde)', border: `1px solid ${BORDE_NEUTRO}` }}>
      <div className="fw-bold" style={{ fontSize: '14px', color: 'var(--texto-fuerte)' }}>
        Todavía no se publicó ninguna fecha
      </div>
      <div style={{ fontSize: '12px', lineHeight: 1.4, color: 'var(--texto-suave)' }}>
        Las fechas de habilitación se cargan a medida que se definen.
      </div>
    </div>
  )
}

function SelectorDeFecha({ elegida, onConfirmar, onCancelar }) {
  const [fechas, setFechas] = useState(null)
  const [seleccionada, setSeleccionada] = useState(elegida ? String(elegida.id) : '')
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    let vigente = true
    api.get('fechas/')
      .then(res => { if (vigente) setFechas(res.data) })
      .catch(() => { if (vigente) setError('No se pudieron traer las fechas de habilitación.') })
    return () => { vigente = false }
  }, [])

  const confirmar = async () => {
    setGuardando(true)
    setError('')
    try {
      await onConfirmar(Number(seleccionada))
    } catch (err) {
      const datos = err.response?.data
      setError(datos?.window?.[0] || datos?.detail || 'No se pudo guardar la fecha elegida.')
      setGuardando(false)
    }
  }

  // Una fecha que ya pasó no se puede elegir, así que no se ofrece.
  const elegibles = (fechas || []).filter(f => !f.ya_paso)

  return (
    <div className="bg-white rounded-4 p-3 mb-3" style={{ border: '1.5px solid var(--info-borde)' }}>
      <Titulo>{elegida ? 'Cambiar la fecha de habilitación' : 'Elegir la fecha de habilitación'}</Titulo>

      <div className="rounded-3 p-3 mb-3"
           style={{ background: 'var(--aviso-fondo)', fontSize: '12.5px', color: 'var(--aviso-texto)', lineHeight: 1.5 }}>
        {elegida
          ? 'Al cambiar la fecha se recalculan todos los vencimientos. Un estudio que sirve '
            + 'para una fecha puede no servir para otra. El detalle de lo que cambie se '
            + 'muestra al confirmar.'
          : 'Al elegir la fecha se determinan los estudios exigidos y se calculan todos los '
            + 'vencimientos. El detalle se muestra al confirmar.'}
      </div>

      {fechas === null && !error && (
        <div style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>Trayendo las fechas…</div>
      )}

      {fechas !== null && elegibles.length === 0 && (
        <div style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>
          No hay ninguna fecha publicada para elegir.
        </div>
      )}

      {elegibles.map(fecha => (
        <label key={fecha.id} className="d-flex align-items-start gap-2 p-3 mb-2 rounded-3"
               style={{
                 border: `1.5px solid ${String(fecha.id) === seleccionada ? 'var(--info)' : BORDE_NEUTRO}`,
                 cursor: 'pointer',
               }}>
          <input type="radio" name="fecha-de-habilitacion" className="form-check-input mt-1"
                 value={fecha.id} checked={String(fecha.id) === seleccionada}
                 onChange={e => setSeleccionada(e.target.value)} />
          <span>
            <span className="fw-bold d-block" style={{ fontSize: '14px', color: 'var(--texto-fuerte)' }}>
              {fecha.slot_display}
            </span>
            <span style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }}>
              {rangoEnCastellano(fecha.start_date, fecha.end_date)}
            </span>
          </span>
        </label>
      ))}

      {error && <div className="text-danger mt-2" style={{ fontSize: '12.5px' }}>{error}</div>}

      <div className="d-flex gap-2 mt-3">
        <button type="button" className="btn btn-primary flex-grow-1 fw-bold py-2"
                style={{ borderRadius: '11px' }}
                disabled={!seleccionada || guardando
                  || (elegida && String(elegida.id) === seleccionada)}
                onClick={confirmar}>
          {guardando ? 'Guardando…' : 'Confirmar la fecha'}
        </button>
        <button type="button" className="btn btn-outline-secondary py-2"
                style={{ borderRadius: '11px' }} disabled={guardando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  )
}

// §15.18: el cambio de fecha no se hace en silencio. Esto es lo que cambió.
function EfectoDelCambio({ efecto, onCerrar }) {
  return (
    <div className="bg-white rounded-4 p-3 mb-3" style={{ border: '1.5px solid var(--info-borde)' }}>
      <Titulo>Efecto del cambio de fecha</Titulo>
      <div style={{ fontSize: '13px', color: 'var(--texto-fuerte)' }}>
        {cuantosFaltan(efecto.faltanAntes)} antes del cambio; {cuantosFaltan(efecto.faltanDespues)} ahora.
      </div>
      {efecto.cambios.length === 0 ? (
        <div className="mt-2" style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }}>
          Ningún estudio cambió de estado.
        </div>
      ) : (
        <ul className="mt-2 mb-0 ps-3" style={{ fontSize: '12.5px', color: 'var(--texto-fuerte)', lineHeight: 1.6 }}>
          {efecto.cambios.map(cambio => (
            <li key={cambio.code}>
              {cambio.texto}: {enPalabras(cambio.estadoAntes)} → <strong>{enPalabras(cambio.estadoDespues)}</strong>
            </li>
          ))}
        </ul>
      )}
      <button type="button" className="btn btn-outline-secondary btn-sm mt-3" onClick={onCerrar}>
        Entendido
      </button>
    </div>
  )
}

// --- "Faltan N estudios" y la barra de progreso -----------------------------

function Contador({ estado }) {
  const { faltan, revisados, total_exigidos: total } = estado
  const completo = estaCompleto(estado)
  const porcentaje = total > 0 ? Math.round((revisados / total) * 100) : 0
  const color = completo ? 'var(--ok)' : 'var(--aviso-texto)'

  return (
    <div className="px-3 py-2 mb-3 rounded-3"
         style={completo
           ? { background: 'var(--ok-fondo)', border: '1px solid var(--ok-borde)' }
           : { background: 'var(--aviso-fondo)', border: '1px solid var(--aviso-borde)' }}>
      <div className="d-flex justify-content-between align-items-baseline gap-2">
        <div className="fw-bold" style={{ fontSize: '15px', lineHeight: 1.3, color }}>
          {cuantosFaltan(faltan)}
        </div>
        <div className="fw-semibold text-nowrap" style={{ fontSize: '11.5px', color }}>
          {revisados} de {total} revisados
        </div>
      </div>
      <div style={{ fontSize: '12px', lineHeight: 1.4, color }}>
        {oracionDelContador(estado)}
      </div>
      <div className="rounded-pill mt-2 overflow-hidden"
           style={{ height: '5px', background: 'var(--borde)' }}>
        <div style={{ background: VERDE, height: '100%', width: `${porcentaje}%` }} />
      </div>
    </div>
  )
}

// --- Las tarjetas de cada estudio -------------------------------------------

function Rechazo({ rechazo }) {
  // §15.12: el motivo y el detalle, textuales. Quién rechazó no viene en la
  // respuesta y no se muestra.
  return (
    <div className="rounded-3 mt-2 px-3 py-2"
         style={{ background: 'var(--peligro-fondo)', fontSize: '12.5px', color: 'var(--peligro-texto)', lineHeight: 1.5 }}>
      <strong>No aprobado — {rechazo.motivo}.</strong>
      {rechazo.detalle && <><br />{rechazo.detalle}</>}
    </div>
  )
}

const ESTADOS_CONOCIDOS_EN_FALTA_SUBIR = [
  'MISSING', 'REJECTED', 'EXPIRED', 'DATE_INVALID', 'BEFORE_WINDOW',
]

function TarjetaPorSubir({ estudio, onSubir }) {
  const conProblema = ESTADOS_CON_PROBLEMA.includes(estudio.estado)
  const conBoton = llevaBoton(estudio)
  const fueraDeVentana = estudio.estado === 'BEFORE_WINDOW'

  return (
    <div className="rounded-4 p-3 mb-2"
         style={{
           background: fueraDeVentana ? 'var(--borde)' : 'var(--superficie)',
           border: `1.5px solid ${conProblema ? BORDE_PROBLEMA : BORDE_NEUTRO}`,
         }}>
      <div className="fw-semibold" style={{ fontSize: '14px', color: 'var(--texto-fuerte)', lineHeight: 1.35 }}>
        {estudio.texto}
      </div>

      {estudio.estado === 'MISSING' && (
        <div className="mt-1" style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }}>Sin presentar</div>
      )}

      {/* §15.19: sin rojo y sin botón. Dice desde cuándo se puede presentar. */}
      {fueraDeVentana && (
        <div className="mt-1" style={{ fontSize: '12.5px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
          Se puede presentar a partir del {enCastellano(estudio.desde_cuando)}.
          Antes de esa fecha, el documento no cubriría todo el período de la habilitación.
        </div>
      )}

      {estudio.estado === 'EXPIRED' && (
        <div className="mt-1 fw-semibold" style={{ fontSize: '12.5px', color: ROJO }}>
          Vencido el {enCastellano(estudio.vence_el)}
        </div>
      )}

      {estudio.estado === 'DATE_INVALID' && (
        <div className="mt-1" style={{ fontSize: '12.5px', color: ROJO, lineHeight: 1.5 }}>
          La fecha cargada no corresponde al período de la habilitación. Debe volver a
          subirse el estudio con la fecha que figura impresa en el documento.
        </div>
      )}

      {/* Un estado que la pantalla no conoce cae acá (agrupar-estudios.js): sin
          este renglón la tarjeta saldría con el nombre y nada más. */}
      {!ESTADOS_CONOCIDOS_EN_FALTA_SUBIR.includes(estudio.estado) && (
        <div className="mt-1" style={{ fontSize: '12.5px', color: ROJO, lineHeight: 1.5 }}>
          No se pudo determinar el estado de este estudio. Debe consultarse con la unidad.
        </div>
      )}

      {estudio.estado === 'REJECTED' && estudio.rechazo && <Rechazo rechazo={estudio.rechazo} />}

      {estudio.upload_hint && conBoton && (
        <div className="mt-2" style={{ fontSize: '12px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
          {estudio.upload_hint}
        </div>
      )}

      {conBoton && <BotonDeSubir onClick={() => onSubir(estudio)}>Subir estudio</BotonDeSubir>}
    </div>
  )
}

function TarjetaEnRevision({ estudio, onSubir }) {
  return (
    <div className="bg-white rounded-4 p-3 mb-2" style={{ border: `1.5px solid ${BORDE_NEUTRO}` }}>
      <div className="fw-semibold" style={{ fontSize: '13.5px', color: 'var(--texto-fuerte)', lineHeight: 1.35 }}>
        {estudio.texto}
      </div>
      {/* Mismo texto para IN_REVIEW y PRE_REVIEWED: el buzo no tiene que ver la
          diferencia entre el enfermero y el médico (§2, §15.12). */}
      <div className="mt-1" style={{ fontSize: '12px', color: 'var(--texto-suave)' }}>
        Presentado. Pendiente de revisión.
      </div>
      {/* Acá sí manda `puede_reemplazarse`, que es la pregunta que ese campo
          responde: si el servidor dejaría pisar la carga que ya existe (§15.10). */}
      {estudio.puede_reemplazarse && (
        <button type="button" className="btn btn-outline-primary btn-sm mt-2"
                style={{ "--bs-btn-border-color": "#356B8C", "--bs-btn-hover-border-color": "#356B8C", "--bs-btn-active-border-color": "#356B8C", borderColor: "#356B8C" }}
                onClick={() => onSubir(estudio)}>
          Reemplazar el estudio
        </button>
      )}
    </div>
  )
}

function TarjetaRevisada({ estudio }) {
  return (
    <div className="bg-white rounded-4 p-3 mb-2 d-flex align-items-center gap-3"
         style={{ border: `1.5px solid ${BORDE_REVISADO}` }}>
      <span className="fw-bold" style={{ color: VERDE, fontSize: '19px' }}>&#10003;</span>
      <div>
        <div className="fw-semibold" style={{ fontSize: '13.5px', color: 'var(--texto-fuerte)' }}>
          {estudio.texto}
        </div>
        {estudio.vence_el && (
          <div style={{ fontSize: '12px', color: 'var(--texto-suave)' }}>
            Vence el {enCastellano(estudio.vence_el)}
          </div>
        )}
      </div>
    </div>
  )
}

function TarjetaNoCorresponde({ estudio }) {
  // Se muestra igual, apagado y explicado: si se escondiera, el que cumple 40
  // se encontraría de golpe con un estudio nuevo sin entender de dónde salió.
  return (
    <div className="rounded-4 p-3 mb-2" style={{ background: 'var(--borde)', opacity: 0.8 }}>
      <div className="fw-semibold" style={{ fontSize: '13.5px', color: 'var(--texto-suave)' }}>
        {estudio.texto}
      </div>
      {estudio.motivo_no_corresponde && (
        <div className="mt-1" style={{ fontSize: '12px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
          {estudio.motivo_no_corresponde}.
        </div>
      )}
    </div>
  )
}

function Grupo({ grupo, onSubir }) {
  if (grupo.estudios.length === 0) return null
  const destacado = grupo.clave === 'falta-subir'
  return (
    <div className={destacado ? 'mb-4 mt-4 px-3 pt-3 pb-1 rounded-3' : 'mb-3'}
         style={destacado ? {
           background: 'var(--barra)',
           borderTop: '3px solid var(--oro-suave)',
           borderBottom: '3px solid var(--oro-suave)',
         } : undefined}>
      <Titulo>{grupo.titulo}</Titulo>
      {grupo.estudios.map(estudio => {
        if (grupo.clave === 'falta-subir') {
          return <TarjetaPorSubir key={estudio.code} estudio={estudio} onSubir={onSubir} />
        }
        if (grupo.clave === 'en-revision') {
          return <TarjetaEnRevision key={estudio.code} estudio={estudio} onSubir={onSubir} />
        }
        if (grupo.clave === 'revisados') {
          return <TarjetaRevisada key={estudio.code} estudio={estudio} />
        }
        // Sólo 'no-corresponde' llega acá. Se despacha por clave y no por el
        // título visible: un desajuste de una tilde mandaría un estudio a la
        // tarjeta más tranquilizadora de la pantalla.
        return <TarjetaNoCorresponde key={estudio.code} estudio={estudio} />
      })}
    </div>
  )
}

// --- El correo al que van los avisos (§15.11) -------------------------------

function BloqueDeCorreo({ correo, onGuardado }) {
  const [editando, setEditando] = useState(false)
  const [valor, setValor] = useState(correo)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  const abrir = () => {
    setValor(correo)
    setError('')
    setEditando(true)
  }

  const guardar = async e => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    try {
      const res = await api.put('mi-correo/', { email: valor })
      setEditando(false)
      onGuardado(res.data.email)
    } catch (err) {
      const datos = err.response?.data
      setError(datos?.email?.[0] || datos?.detail || 'No se pudo guardar el correo.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="bg-white rounded-4 p-3 mb-3" style={{ border: `1.5px solid ${BORDE_NEUTRO}` }}>
      <Titulo>Avisos por correo</Titulo>
      {editando ? (
        <form onSubmit={guardar}>
          <label className="form-label" style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }}>
            Dirección a la que se envían los avisos
          </label>
          <input type="email" required className="form-control" value={valor}
                 autoComplete="email" onChange={e => setValor(e.target.value)} />
          {error && <div className="text-danger mt-2" style={{ fontSize: '12.5px' }}>{error}</div>}
          <div className="d-flex gap-2 mt-3">
            <button type="submit" className="btn btn-primary btn-sm" disabled={guardando}>
              {guardando ? 'Guardando…' : 'Guardar el correo'}
            </button>
            <button type="button" className="btn btn-outline-secondary btn-sm"
                    disabled={guardando} onClick={() => setEditando(false)}>
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <>
          <div style={{ fontSize: '13px', color: 'var(--texto-fuerte)', wordBreak: 'break-all' }}>{correo}</div>
          <div className="mt-1" style={{ fontSize: '12px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
            Los avisos de esta aplicación se envían a esa dirección. Si está mal escrita,
            puede corregirse acá.
          </div>
          <button type="button" className="btn btn-outline-secondary btn-sm mt-2" onClick={abrir}>
            Corregir el correo
          </button>
        </>
      )}
    </div>
  )
}

// --- La hoja de carga -------------------------------------------------------

// El punto ya está determinado: se entra apretando el botón de ese estudio, así
// que no hay desplegable de tipo de estudio (§8.3). Los dos campos —la fecha
// impresa en el documento y el archivo— son de `CargarEstudio` (Tarea 8), que
// se monta acá adentro; esta hoja aporta el marco y el punto elegido.
function HojaDeCarga({ estudio, onCerrar, onSubido }) {
  return (
    <>
      <div className="position-fixed top-0 start-0 w-100 h-100"
           style={{ background: 'rgba(21,33,59,.45)', zIndex: 1070 }} onClick={onCerrar} />
      <div className="position-fixed bottom-0 start-0 w-100 bg-white px-3 pt-3 pb-4"
           style={{ borderRadius: '20px 20px 0 0', zIndex: 1071, maxHeight: '85vh', overflowY: 'auto' }}>
        <div className="rounded-pill mx-auto mb-3"
             style={{ width: '40px', height: '4px', background: 'var(--borde)' }} />
        <Titulo>Estudio</Titulo>
        <div className="fw-bold" style={{ fontSize: '15px', color: 'var(--texto-fuerte)', lineHeight: 1.35 }}>
          {estudio.texto}
        </div>
        {estudio.upload_hint && (
          <div className="mt-2" style={{ fontSize: '12.5px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
            {estudio.upload_hint}
          </div>
        )}
        <div className="rounded-3 px-3 py-2 mt-3"
             style={{ background: 'var(--info-fondo)', fontSize: '12px', color: 'var(--info)', lineHeight: 1.5 }}>
          La imagen se reduce automáticamente antes de enviarse. No se requiere ninguna acción.
        </div>
        <CargarEstudio code={estudio.code} onSubido={onSubido} />
        <button type="button" className="btn btn-outline-secondary w-100 mt-2 py-2"
                style={{ borderRadius: '11px' }} onClick={onCerrar}>
          Cerrar
        </button>
      </div>
    </>
  )
}

// --- La pantalla ------------------------------------------------------------

const PantallaBuzo = ({ onLogout, perfil, onSubir }) => {
  const [estado, setEstado] = useState(null)
  const [error, setError] = useState('')
  const [eligiendoFecha, setEligiendoFecha] = useState(false)
  const [efecto, setEfecto] = useState(null)
  const [estudioACargar, setEstudioACargar] = useState(null)

  const traer = useCallback(async () => {
    const res = await api.get('mi-estado/')
    setEstado(res.data)
    return res.data
  }, [])

  useEffect(() => {
    let vigente = true
    // Se arma la promesa acá en lugar de llamar a `traer()` derecho: la regla
    // `react-hooks/set-state-in-effect` cuenta la llamada sincrónica a una
    // función que escribe estado como un setState en el cuerpo del efecto.
    api.get('mi-estado/').then(
      res => { if (vigente) setEstado(res.data) },
      () => { if (vigente) setError(ERROR_AL_TRAER) },
    )
    return () => { vigente = false }
  }, [])

  const confirmarFecha = async idDeLaFecha => {
    const antes = estado
    // Dos pasos, dos errores: si el PUT sale bien y falla el GET, la fecha SÍ se
    // guardó, y el selector no debe decir lo contrario.
    await api.put('mi-fecha/', { window: idDeLaFecha })
    let despues
    try {
      despues = await traer()
    } catch {
      setEligiendoFecha(false)
      setEfecto(null)
      setError('La fecha se guardó, pero no se pudo traer el estado actualizado de los estudios.')
      return
    }
    setEligiendoFecha(false)
    setEfecto(efectoDelCambioDeFecha(antes, despues))
  }

  const abrirCarga = estudio => {
    if (onSubir) onSubir(estudio)
    else setEstudioACargar(estudio)
  }


  const nombre = [perfil?.last_name, perfil?.first_name].filter(Boolean).join(', ')
  // Con fecha elegida y sin estudios exigidos, lo que falta es la fecha de
  // nacimiento: el motor no puede saber qué puntos corresponden sin la edad.
  const faltaElNacimiento = !!estado?.fecha_elegida && estado.total_exigidos === 0

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={perfil?.role} onLogout={onLogout} />

      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '560px' }}>
          <h1 className="fw-bold mb-0" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
            Estudios médicos
          </h1>
          {nombre && (
            <div style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>
              {nombre}{perfil?.destination ? ` — ${perfil.destination}` : ''}
            </div>
          )}

          <div className="mt-4">
            {error && (
              <div className="alert alert-warning" role="alert">
                {error}
                <button type="button" className="btn btn-sm btn-outline-dark ms-2"
                        onClick={() => { setError(''); traer().catch(() => setError('No se pudo traer el estado de los estudios.')) }}>
                  Volver a intentar
                </button>
              </div>
            )}

            {!estado && !error && (
              <div style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>Trayendo los estudios…</div>
            )}

            {estado && (
              <>
                {eligiendoFecha ? (
                  <SelectorDeFecha elegida={estado.fecha_elegida}
                                   onConfirmar={confirmarFecha}
                                   onCancelar={() => setEligiendoFecha(false)} />
                ) : (
                  <BloqueDeFecha estado={estado} onElegir={() => {
                    setEfecto(null)
                    setEligiendoFecha(true)
                  }} />
                )}

                {efecto && <EfectoDelCambio efecto={efecto} onCerrar={() => setEfecto(null)} />}

                {faltaElNacimiento && (
                  <div className="rounded-4 p-3 mb-3"
                       style={{ background: 'var(--aviso-fondo)', border: '1px solid var(--aviso-borde)' }}>
                    <div className="fw-bold" style={{ fontSize: '15px', color: 'var(--aviso-texto)' }}>
                      Falta la fecha de nacimiento
                    </div>
                    <div className="mt-2" style={{ fontSize: '12.5px', color: 'var(--aviso-texto)', lineHeight: 1.5 }}>
                      Sin la fecha de nacimiento no se puede determinar qué estudios
                      corresponden, porque uno de ellos se exige a partir de los 40 años.
                      Se completa en el perfil.
                    </div>
                    <Link to="/profile" className="btn btn-outline-dark btn-sm mt-3">
                      Ir al perfil
                    </Link>
                  </div>
                )}

                {/* Sin estudios exigidos no hay nada que contar, y un "Faltan 0
                    estudios" en verde le diría a quien todavía no eligió fecha
                    que está todo en orden. */}
                {estado.total_exigidos > 0 && <Contador estado={estado} />}

                {agrupar(estado.estudios).map(grupo => (
                  <Grupo key={grupo.titulo} grupo={grupo} onSubir={abrirCarga} />
                ))}

                <BloqueDeCorreo correo={estado.correo}
                                onGuardado={correo => setEstado({ ...estado, correo })} />

                <Soporte />
              </>
            )}
          </div>
        </div>
      </div>

      {estudioACargar && (
        <HojaDeCarga estudio={estudioACargar} onCerrar={() => setEstudioACargar(null)}
                     onSubido={() => { setEstudioACargar(null); traer().catch(() => setError(ERROR_AL_TRAER)) }} />
      )}
    </div>
  )
}

export default PantallaBuzo
