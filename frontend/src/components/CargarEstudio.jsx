import React, { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import api from '../api'
import { comprimirEnElNavegador } from '../lib/comprimir-imagen'
import { primerMensajeDelCuerpo } from '../lib/primer-mensaje-del-cuerpo'
import CampoFecha from './CampoFecha'

// Los dos campos de la carga: la fecha impresa en el documento y el archivo. El
// punto (`code`) ya viene determinado por la pantalla, que es quien muestra el
// nombre del estudio, su `upload_hint` y el aviso de la compresión.
//
// El navegador comprime pero no valida: tamaño, píxeles y formato los rechaza
// el servidor, y el mensaje que devuelve se muestra atado a su campo. Repetir
// esos límites acá los desincronizaría del servidor.
const CAMPOS = ['study_date', 'pdf_attachment']
const ERROR_GENERICO = 'No se pudo enviar el estudio. Intentar nuevamente.'

function mensajeDe(valor) {
  return Array.isArray(valor) ? valor.join(' ') : String(valor)
}

function CargarEstudio({ code, onSubido }) {
  const { control, handleSubmit, setError, clearErrors, formState: { errors } } = useForm()
  const [archivos, setArchivos] = useState([])
  const [claveInput, setClaveInput] = useState(0)
  const [enviando, setEnviando] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')

  const enviar = async valores => {
    setErrorGeneral('')
    if (archivos.length === 0) {
      setError('archivo', { type: 'manual', message: 'Falta elegir el archivo del estudio.' })
      return
    }
    setEnviando(true)
    try {
      // Varias fotos viajan como varios `pdf_attachment`: el servidor las junta
      // en un solo PDF, una por página, en el orden en que se eligieron.
      const comprimidos = await Promise.all(archivos.map(comprimirEnElNavegador))
      const datos = new FormData()
      datos.append('study_code', code)
      datos.append('study_date', valores.fecha)
      comprimidos.forEach(a => datos.append('pdf_attachment', a))
      await api.post('blocks/', datos)
      onSubido()
    } catch (e) {
      const cuerpo = e.response?.data
      if (cuerpo && typeof cuerpo === 'object') {
        let atado = false
        CAMPOS.forEach(campo => {
          if (cuerpo[campo]) {
            setError(campo === 'study_date' ? 'fecha' : 'archivo',
                     { type: 'server', message: mensajeDe(cuerpo[campo]) })
            atado = true
          }
        })
        if (!atado) {
          // El servidor ata el rechazo a su campo (p. ej. `study_code` cuando el
          // médico ya revisó el estudio). Si no es uno de los dos campos del
          // formulario, se muestra el mensaje que vino: el genérico invita a
          // reintentar algo que nunca va a andar.
          setErrorGeneral(primerMensajeDelCuerpo(cuerpo) || ERROR_GENERICO)
        }
      } else {
        setErrorGeneral(ERROR_GENERICO)
      }
      setEnviando(false)
    }
  }

  const estilo = { fontSize: '13px' }

  return (
    <form onSubmit={handleSubmit(enviar)} noValidate className="mt-3">
      <div className="mb-3">
        <label htmlFor="carga-fecha" className="form-label fw-bold mb-1" style={estilo}>
          Fecha que figura en el documento
        </label>
        <div className="mb-2" style={{ fontSize: '12px', color: 'var(--texto-suave)', lineHeight: 1.5 }}>
          Es la fecha impresa en el estudio, no la de hoy.
        </div>
        <Controller
          name="fecha"
          control={control}
          defaultValue=""
          rules={{ required: 'Falta la fecha que figura en el documento.' }}
          render={({ field }) => (
            <CampoFecha
              id="carga-fecha"
              value={field.value || ''}
              onChange={(iso) => { field.onChange(iso); clearErrors('fecha') }}
              error={errors.fecha?.message || null}
            />
          )}
        />
      </div>

      <div className="mb-3">
        <label htmlFor="carga-archivo" className="form-label fw-bold mb-1" style={estilo}>
          Archivo o fotos
        </label>
        {/* Sin `capture`: ese atributo le dice al celular "abrí la cámara" y se salta su menú,
            así que solo dejaba sacar foto. Sin él, el sistema ofrece sacar la foto, elegir de la
            galería o elegir un archivo (el PDF de un estudio ya hecho). */}
        {/* Cada vez que se elige o se saca algo se SUMA a la lista (y el input se vacía): en el
            celular la cámara devuelve una sola foto por vez y, si reemplazara, solo quedaría la última. */}
        <input id="carga-archivo" key={claveInput} type="file" accept="image/*,.pdf,.heic" multiple
               className={`form-control${errors.archivo ? ' is-invalid' : ''}`}
               aria-invalid={!!errors.archivo}
               onChange={e => {
                 const nuevos = Array.from(e.target.files || [])
                 if (nuevos.length) {
                   setArchivos(prev => [...prev, ...nuevos])
                   clearErrors('archivo')
                 }
                 setClaveInput(k => k + 1)
               }} />
        {archivos.length > 0 && (
          <ul className="list-unstyled mt-2 mb-0" style={estilo}>
            {archivos.map((a, i) => (
              <li key={`${a.name}-${a.lastModified}-${i}`}
                  className="d-flex align-items-center justify-content-between py-1">
                <span className="text-truncate me-2">{i + 1}. {a.name}</span>
                <button type="button" className="btn btn-sm btn-outline-danger"
                        onClick={() => setArchivos(prev => prev.filter((_, j) => j !== i))}>
                  Quitar
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-1" style={{ fontSize: '12px', color: 'var(--texto-suave)' }}>
          Se pueden sumar varias fotos (hasta 10), una por una o de a muchas: se juntan en un solo documento.
        </div>
        {errors.archivo && <div className="invalid-feedback d-block">{errors.archivo.message}</div>}
      </div>

      {errorGeneral && <div className="alert alert-danger py-2" role="alert" style={estilo}>{errorGeneral}</div>}

      <button type="submit" className="btn btn-primary w-100 py-2" style={{ borderRadius: '11px' }}
              disabled={enviando}>
        {enviando ? 'Enviando…' : 'Enviar estudio'}
      </button>
    </form>
  )
}

export default CargarEstudio
