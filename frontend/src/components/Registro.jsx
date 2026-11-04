import React, { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

// Los campos del POST /api/auth/registration/. `username` no se pide: el
// backend lo deriva. El nombre de cada campo del formulario es el mismo que usa
// el backend, de modo que un error del servidor se ata a su campo sin tabla de
// equivalencias.
const CAMPOS = [
  'email', 'email2', 'password1', 'password2',
  'first_name', 'last_name', 'dni', 'rank', 'destination', 'birth_date',
]
const ERROR_GENERICO = 'No se pudo completar el registro. Intentar nuevamente.'
const ESTILO = { fontSize: '13px' }

function mensajeDe(valor) {
  return Array.isArray(valor) ? valor.join(' ') : String(valor)
}

const noVacio = mensaje => v => v.trim() !== '' || mensaje

// Fuera de `Registro` a propósito: un componente definido adentro se recrea en
// cada render y los campos perderían el foco con cada tecla.
function Campo({ id, etiqueta, ayuda, error, children }) {
  return (
    <div className="mb-3">
      <label htmlFor={`reg-${id}`} className="form-label fw-bold mb-1" style={ESTILO}>{etiqueta}</label>
      {ayuda && <div className="mb-2" style={{ fontSize: '12px', color: '#7a8499', lineHeight: 1.5 }}>{ayuda}</div>}
      {children}
      {error && <div className="invalid-feedback d-block">{error.message}</div>}
    </div>
  )
}

function Registro({ onLogin }) {
  const navigate = useNavigate()
  const { register, handleSubmit, setError, clearErrors, getValues, formState: { errors } } = useForm()
  const [grupos, setGrupos] = useState(null)
  const [errorGrados, setErrorGrados] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')
  const [verClave, setVerClave] = useState(false)

  // La lista de grados la define el backend: no se redefine acá.
  useEffect(() => {
    let vigente = true
    api.get('grados/')
      .then(res => { if (vigente) setGrupos(res.data) })
      .catch(() => { if (vigente) setErrorGrados(true) })
    return () => { vigente = false }
  }, [])

  const enviar = async valores => {
    setErrorGeneral('')
    setEnviando(true)
    try {
      const res = await api.post('auth/registration/', {
        email: valores.email.trim(),
        email2: valores.email2.trim(),
        password1: valores.password1,
        password2: valores.password2,
        first_name: valores.first_name.trim(),
        last_name: valores.last_name.trim(),
        dni: valores.dni.trim(),
        rank: valores.rank,
        destination: valores.destination.trim(),
        birth_date: valores.birth_date,
      })
      // Con ACCOUNT_EMAIL_VERIFICATION = 'mandatory' el servidor no devuelve
      // `key`; guardar `undefined` dejaría la cadena "undefined" como token.
      if (!res.data?.key) {
        setErrorGeneral('Se creó la cuenta, pero no se pudo iniciar la sesión. Debe ingresarse desde la pantalla de acceso.')
        setEnviando(false)
        return
      }
      localStorage.setItem('token', res.data.key)
      onLogin()
      navigate('/dashboard')
    } catch (e) {
      const cuerpo = e.response?.data
      if (cuerpo && typeof cuerpo === 'object') {
        let atado = false
        CAMPOS.forEach(campo => {
          if (cuerpo[campo]) {
            setError(campo, { type: 'server', message: mensajeDe(cuerpo[campo]) })
            atado = true
          }
        })
        if (!atado) {
          const resto = cuerpo.non_field_errors || cuerpo.detail
          setErrorGeneral(resto ? mensajeDe(resto) : ERROR_GENERICO)
        }
      } else {
        setErrorGeneral(ERROR_GENERICO)
      }
      setEnviando(false)
    }
  }

  const entrada = (nombre, reglas, tipo = 'text', autoComplete) => (
    <input id={`reg-${nombre}`} type={tipo} autoComplete={autoComplete}
           className={`form-control${errors[nombre] ? ' is-invalid' : ''}`}
           aria-invalid={!!errors[nombre]}
           {...register(nombre, { ...reglas, onChange: () => clearErrors(nombre) })} />
  )
  const tipoClave = verClave ? 'text' : 'password'

  return (
    <div className="d-flex justify-content-center" style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      <div className="w-100 p-3 py-4" style={{ maxWidth: '460px' }}>
        <h1 className="fw-bold h3 mb-1">Registro</h1>
        <p className="text-secondary mb-3" style={ESTILO}>
          Datos del buzo. Todos los campos son obligatorios.
        </p>

        <form onSubmit={handleSubmit(enviar)} noValidate className="card shadow-sm p-3">
          <Campo id="rank" etiqueta="Grado" error={errors.rank}>
            <select id="reg-rank" disabled={!grupos} defaultValue=""
                    className={`form-select${errors.rank ? ' is-invalid' : ''}`}
                    aria-invalid={!!errors.rank}
                    {...register('rank', { required: 'Falta elegir el grado.', onChange: () => clearErrors('rank') })}>
              <option value="">
                {errorGrados ? 'No se pudo cargar la lista de grados' : grupos ? 'Elegir el grado' : 'Cargando…'}
              </option>
              {(grupos || []).map(g => (
                <optgroup key={g.grupo} label={g.grupo}>
                  {g.grados.map(gr => <option key={gr.valor} value={gr.valor}>{gr.etiqueta}</option>)}
                </optgroup>
              ))}
            </select>
          </Campo>

          <Campo id="first_name" etiqueta="Nombre" error={errors.first_name}>
            {entrada('first_name', { validate: noVacio('Falta el nombre.') }, 'text', 'given-name')}
          </Campo>
          <Campo id="last_name" etiqueta="Apellido" error={errors.last_name}>
            {entrada('last_name', { validate: noVacio('Falta el apellido.') }, 'text', 'family-name')}
          </Campo>
          <Campo id="dni" etiqueta="DNI" error={errors.dni}>
            {entrada('dni', { validate: noVacio('Falta el DNI.') })}
          </Campo>
          <Campo id="destination" etiqueta="Unidad" error={errors.destination}>
            {entrada('destination', { validate: noVacio('Falta la unidad.') })}
          </Campo>
          <Campo id="birth_date" etiqueta="Fecha de nacimiento" error={errors.birth_date}>
            {entrada('birth_date', { required: 'Falta la fecha de nacimiento.' }, 'date')}
          </Campo>
          <Campo id="email" etiqueta="Correo electrónico" error={errors.email}
                 ayuda="No se envía ninguna verificación: el correo debe escribirse sin errores.">
            {entrada('email', { validate: noVacio('Falta el correo electrónico.') }, 'email', 'email')}
          </Campo>
          <Campo id="email2" etiqueta="Repetir el correo electrónico" error={errors.email2}>
            {entrada('email2', {
              validate: v => v.trim() === ''
                ? 'Falta repetir el correo electrónico.'
                : v.trim() === getValues('email').trim() || 'Los dos correos no coinciden.',
            }, 'email')}
          </Campo>
          <Campo id="password1" etiqueta="Contraseña" error={errors.password1}>
            {entrada('password1', { required: 'Falta la contraseña.' }, tipoClave, 'new-password')}
          </Campo>
          <Campo id="password2" etiqueta="Repetir la contraseña" error={errors.password2}>
            {entrada('password2', {
              validate: v => v === ''
                ? 'Falta repetir la contraseña.'
                : v === getValues('password1') || 'Las dos contraseñas no coinciden.',
            }, tipoClave, 'new-password')}
          </Campo>
          <div className="form-check mb-3" style={ESTILO}>
            <input id="reg-ver" type="checkbox" className="form-check-input"
                   checked={verClave} onChange={e => setVerClave(e.target.checked)} />
            <label htmlFor="reg-ver" className="form-check-label">Mostrar las contraseñas</label>
          </div>

          {errorGeneral && <div className="alert alert-danger py-2" role="alert" style={ESTILO}>{errorGeneral}</div>}

          <button type="submit" className="btn btn-primary w-100 py-2" style={{ borderRadius: '11px' }}
                  disabled={enviando}>
            {enviando ? 'Registrando…' : 'Registrarse'}
          </button>
        </form>

        <div className="text-center text-muted mt-3" style={ESTILO}>
          ¿Ya existe una cuenta? <Link to="/login" className="fw-bold text-decoration-none">Iniciar sesión</Link>
        </div>
      </div>
    </div>
  )
}

export default Registro
