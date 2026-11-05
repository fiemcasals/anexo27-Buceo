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
  const { register, control, handleSubmit, setError, clearErrors, formState: { errors } } = useForm()
  const [enviando, setEnviando] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')

  const enviar = async valores => {
    setErrorGeneral('')
    setEnviando(true)
    try {
      const archivo = await comprimirEnElNavegador(valores.archivo[0])
      const datos = new FormData()
      datos.append('study_code', code)
      datos.append('study_date', valores.fecha)
      datos.append('pdf_attachment', archivo)
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

  const alCambiar = campo => () => clearErrors(campo)
  const estilo = { fontSize: '13px' }

  return (
    <form onSubmit={handleSubmit(enviar)} noValidate className="mt-3">
      <div className="mb-3">
        <label htmlFor="carga-fecha" className="form-label fw-bold mb-1" style={estilo}>
          Fecha que figura en el documento
        </label>
        <div className="mb-2" style={{ fontSize: '12px', color: '#7a8499', lineHeight: 1.5 }}>
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
          Archivo
        </label>
        <input id="carga-archivo" type="file" accept="image/*,.pdf,.heic" capture="environment"
               className={`form-control${errors.archivo ? ' is-invalid' : ''}`}
               aria-invalid={!!errors.archivo}
               {...register('archivo', {
                 validate: f => (f && f.length > 0) || 'Falta elegir el archivo del estudio.',
                 onChange: alCambiar('archivo'),
               })} />
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
