import React, { useState } from 'react'
import api from '../api'

// Los pasos del circuito real de esta pantalla. Van en una lista y no en un
// campo libre porque lo primero que hay que saber es DONDE se trabo, y escrito
// a mano eso llega como "no funciona".
const PASOS = [
  'Ingresar o crear la cuenta',
  'Recuperar la contraseña',
  'Completar los datos del perfil',
  'Elegir la fecha de habilitación',
  'Cargar un estudio',
  'Ver qué estudios me faltan',
  'Otro / no está en la lista',
]

const BORDE = '1.5px solid var(--info-borde)'

/**
 * Boton Soporte: manda por correo lo que no funciono.
 *
 * Plegado por omision: es una salida de emergencia, no parte del circuito, y
 * desplegado le compite la atencion a los estudios que el buzo vino a cargar.
 */
export default function Soporte() {
  const [abierto, setAbierto] = useState(false)
  const [paso, setPaso] = useState(PASOS[0])
  const [mensaje, setMensaje] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const [error, setError] = useState('')

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setError('')
    try {
      await api.post('support/', { step: paso, message: mensaje })
      setEnviado(true)
      setMensaje('')
    } catch (err) {
      setError(err.response?.data?.error
        || 'No se pudo enviar el reporte. Probá de nuevo en un rato.')
    } finally {
      setEnviando(false)
    }
  }

  if (!abierto) {
    return (
      <div className="text-center mt-4 mb-2">
        <button type="button" className="btn btn-link btn-sm text-decoration-none"
                style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }}
                onClick={() => setAbierto(true)}>
          ¿Algo no funciona? Avisanos
        </button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-4 p-3 mb-3 mt-4" style={{ border: BORDE }}>
      <div className="d-flex justify-content-between align-items-start">
        <div className="fw-bold" style={{ fontSize: '15px', color: 'var(--texto-fuerte)' }}>
          Avisar un problema
        </div>
        <button type="button" className="btn-close btn-sm"
                aria-label="Cerrar" onClick={() => setAbierto(false)} />
      </div>

      {enviado ? (
        <div className="mt-2" style={{ fontSize: '12.5px', color: 'var(--info)', lineHeight: 1.5 }}>
          Listo, el reporte salió. Gracias por avisar.
          <div>
            <button type="button" className="btn btn-outline-secondary btn-sm mt-3"
                    onClick={() => setEnviado(false)}>
              Avisar otra cosa
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={enviar}>
          <div className="mt-2" style={{ fontSize: '12.5px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
            Contanos qué pasó. Llega directo a quienes mantienen el sistema, con tu
            correo para poder contestarte.
          </div>

          <label className="form-label mt-3 mb-1"
                 style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }} htmlFor="soporte-paso">
            ¿En qué paso te trabaste?
          </label>
          <select id="soporte-paso" className="form-select form-select-sm"
                  value={paso} onChange={e => setPaso(e.target.value)}>
            {PASOS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>

          <label className="form-label mt-3 mb-1"
                 style={{ fontSize: '12.5px', color: 'var(--texto-suave)' }} htmlFor="soporte-mensaje">
            ¿Qué pasó?
          </label>
          <textarea id="soporte-mensaje" className="form-control form-control-sm"
                    rows={4} value={mensaje} required
                    placeholder="Qué estabas haciendo y qué viste en la pantalla"
                    onChange={e => setMensaje(e.target.value)} />

          {error && (
            <div className="alert alert-warning mt-3 mb-0 py-2"
                 style={{ fontSize: '12.5px' }} role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary w-100 fw-bold mt-3 py-2"
                  disabled={enviando || !mensaje.trim()}>
            {enviando ? 'Enviando…' : 'Enviar el reporte'}
          </button>
        </form>
      )}
    </div>
  )
}
