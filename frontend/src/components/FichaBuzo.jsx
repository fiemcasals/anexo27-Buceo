import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import api from '../api';
import BarraLateral from './BarraLateral';
import Pastilla from './Pastilla';
import {
  MOTIVOS_DE_RECHAZO, celdaTurno, contadoresDeLaFicha, describirDictamen,
  erroresDelDialogo, estadoAlAprobar, estadoDelPunto, lineaDelPunto,
  mensajeDelFallo, renglonDelEncabezado,
} from '../lib/pantallas-del-revisor';

// La ficha de un buzo (§8.2): los ocho puntos de la directiva, siempre los
// ocho y en orden a–h, presentados o no, y los botones de dictamen sólo donde
// hay algo que dictaminar.
//
// Todo lo que se muestra viene del servidor ya calculado (`GET /api/plantel/<id>/`):
// la pantalla no deriva ningún estado. Después de cada dictamen se vuelve a
// pedir la ficha entera, porque el estado de un punto, el del buzo y los cuatro
// contadores cambian juntos y la única fuente es el servidor.

const TONO_DE_LA_FILA = {
  aviso: { background: '#fffaf0', borderLeft: '4px solid #f0c36d' },
  peligro: { background: '#fff', borderLeft: '4px solid #e8a5a5' },
  ok: { background: '#fff', borderLeft: '4px solid #9ad3ae' },
  neutro: { background: '#fff', borderLeft: '4px solid #dde2ec' },
  apagado: { background: '#f7f8fb', borderLeft: '4px solid #eceff5' },
};

const COLOR_DEL_TEXTO = {
  ok: '#1d7a3d', aviso: '#9a6508', peligro: '#a52a2a', neutro: '#5b6684',
};

function Contadores({ ficha }) {
  return (
    <div className="d-flex gap-2 flex-wrap">
      {contadoresDeLaFicha(ficha).map((c) => (
        <div key={c.clave}
             style={{
               background: '#f7f8fb', border: '1px solid #eceff5', borderRadius: '10px',
               padding: '9px 15px', textAlign: 'center', minWidth: '92px',
             }}>
          <div style={{ fontSize: '21px', fontWeight: 700, color: '#15213b', lineHeight: 1 }}>
            {c.valor}
            {c.de !== null && <span style={{ fontSize: '13px', color: '#8590a8' }}>/{c.de}</span>}
          </div>
          <div style={{
            fontSize: '10px', color: '#6b7694', textTransform: 'uppercase',
            letterSpacing: '.5px', marginTop: '3px',
          }}>
            {c.rotulo}
          </div>
        </div>
      ))}
    </div>
  );
}

// Un dictamen de la historia del punto, con quién y cuándo. Cada estado tiene
// su texto, y uno que el servidor mande sin contenido —una aprobación
// revertida— se lee igual: nunca queda una línea en blanco.
function Dictamen({ dictamen }) {
  const d = describirDictamen(dictamen);
  return (
    <li style={{ color: COLOR_DEL_TEXTO[d.tono] || COLOR_DEL_TEXTO.neutro }}>
      <span className="fw-semibold">{d.titulo}</span>
      {d.motivo && <div style={{ color: '#15213b' }}><strong>{d.motivo}.</strong> {d.cuerpo}</div>}
    </li>
  );
}

function Punto({ estudio, rol, ocupado, error, onAprobar, onRechazar, onRevertir }) {
  const [confirmando, setConfirmando] = useState(false);
  const estado = estadoDelPunto(estudio.estado);
  const noCorresponde = estudio.estado === 'NOT_REQUIRED';
  const enCurso = ocupado === estudio.code;
  const espera = estudio.espera_dictamen;

  return (
    <div className="d-flex gap-3 align-items-start flex-wrap"
         style={{ padding: '14px 18px', borderBottom: '1px solid #eceff5', ...TONO_DE_LA_FILA[estado.tono] }}>
      <div style={{ width: '22px', fontWeight: 700, color: '#8590a8' }}>{estudio.code}.</div>

      <div style={{ flex: 1, minWidth: '240px' }}>
        <div style={{
          fontWeight: 600, color: noCorresponde ? '#9aa3b8' : '#15213b',
          textDecoration: noCorresponde ? 'line-through' : 'none',
        }}>
          {estudio.texto}
        </div>
        <div style={{ fontSize: '12.5px', color: '#6b7694', marginTop: '2px' }}>
          {lineaDelPunto(estudio)}
        </div>
        {estudio.dictamenes.length > 0 && (
          <ul className="list-unstyled mb-0" style={{ fontSize: '12.5px', marginTop: '6px' }}>
            {estudio.dictamenes.map((d) => <Dictamen key={d.id} dictamen={d} />)}
          </ul>
        )}
        {estudio.estado === 'REJECTED' && (
          <div style={{ fontSize: '12.5px', color: '#6b7694', marginTop: '4px' }}>
            A la espera de que el buzo suba el reemplazo.
          </div>
        )}
        {error && (
          <div className="alert alert-danger py-1 px-2 mt-2 mb-0" role="alert" style={{ fontSize: '12.5px' }}>
            {error}
          </div>
        )}
      </div>

      <div className="d-flex align-items-center gap-2 flex-wrap justify-content-end">
        {!espera && !noCorresponde && <Pastilla tono={estado.tono}>{estado.rotulo}</Pastilla>}
        {noCorresponde && <Pastilla tono="apagado">{estado.rotulo}</Pastilla>}
        {espera && <Pastilla tono="aviso">{estado.rotulo}</Pastilla>}

        {estudio.archivo && (
          <a href={estudio.archivo} target="_blank" rel="noreferrer"
             className="btn btn-sm btn-outline-secondary">
            Ver
          </a>
        )}

        {espera && (
          <>
            <button type="button" className="btn btn-sm btn-success" disabled={enCurso}
                    onClick={() => onAprobar(estudio)}>
              {enCurso ? 'Guardando…' : '✓ Aprobar'}
            </button>
            <button type="button" className="btn btn-sm btn-outline-danger" disabled={enCurso}
                    onClick={() => onRechazar(estudio)}>
              Rechazar
            </button>
          </>
        )}

        {estudio.revertible_id && !confirmando && (
          <button type="button" className="btn btn-sm btn-outline-secondary" disabled={enCurso}
                  onClick={() => setConfirmando(true)}>
            Revertir
          </button>
        )}
        {estudio.revertible_id && confirmando && (
          <span className="d-flex align-items-center gap-2" style={{ fontSize: '12.5px' }}>
            El punto vuelve a revisión.
            <button type="button" className="btn btn-sm btn-warning" disabled={enCurso}
                    onClick={() => { setConfirmando(false); onRevertir(estudio); }}>
              Revertir la aprobación
            </button>
            <button type="button" className="btn btn-sm btn-link" onClick={() => setConfirmando(false)}>
              Cancelar
            </button>
          </span>
        )}
      </div>

      {espera && rol === 'NURSE' && (
        <div style={{ flexBasis: '100%', fontSize: '12px', color: '#8590a8', paddingLeft: '34px' }}>
          La aprobación del enfermero auxiliar deja el estudio como pre-revisado:
          la firma final es del médico.
        </div>
      )}
    </div>
  );
}

// El diálogo de rechazo. Pide los dos datos que el servidor exige (el motivo y
// el detalle) y dice, con la dirección a la vista, que al confirmar se le manda
// un correo al buzo: quien rechaza tiene que saber que eso sale.
//
// No valida de su lado: si falta algo, el servidor contesta 400 con el campo
// señalado y el mensaje se muestra junto a ese campo.
function DialogoDeRechazo({ estudio, correo, onCancelar, onConfirmar }) {
  const [motivo, setMotivo] = useState('');
  const [detalle, setDetalle] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [errores, setErrores] = useState({ campos: {}, general: '' });

  useEffect(() => {
    const alTeclear = (e) => { if (e.key === 'Escape') onCancelar(); };
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [onCancelar]);

  const confirmar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setErrores({ campos: {}, general: '' });
    try {
      await onConfirmar({ rejection_reason: motivo, content: detalle });
    } catch (error) {
      const dato = error?.response?.data;
      setErrores(dato && typeof dato === 'object'
        ? erroresDelDialogo(dato)
        : { campos: {}, general: 'No se pudo guardar el rechazo.' });
      setEnviando(false);
    }
  };

  return (
    <>
      <div className="modal-backdrop fade show"></div>
      <div className="modal fade show d-block" role="dialog" aria-modal="true"
           aria-labelledby="titulo-rechazo" tabIndex={-1}>
        <div className="modal-dialog modal-dialog-centered">
          <form className="modal-content" onSubmit={confirmar} noValidate>
            <div className="modal-header">
              <h2 className="modal-title fs-5" id="titulo-rechazo">Rechazar estudio</h2>
            </div>
            <div className="modal-body">
              <div className="text-uppercase" style={{ fontSize: '11px', color: '#8590a8', letterSpacing: '.5px' }}>
                Estudio
              </div>
              <div className="fw-semibold mb-3">{estudio.code}. {estudio.texto}</div>

              <fieldset className="mb-3">
                <legend className="form-label fw-semibold" style={{ fontSize: '14px' }}>
                  Motivo del rechazo
                </legend>
                {MOTIVOS_DE_RECHAZO.map((m) => (
                  <div className="form-check" key={m.codigo}>
                    <input className={`form-check-input${errores.campos.rejection_reason ? ' is-invalid' : ''}`}
                           type="radio" name="motivo" id={`motivo-${m.codigo}`}
                           value={m.codigo} checked={motivo === m.codigo}
                           onChange={() => setMotivo(m.codigo)} />
                    <label className="form-check-label" htmlFor={`motivo-${m.codigo}`}>{m.texto}</label>
                  </div>
                ))}
                {errores.campos.rejection_reason && (
                  <div className="text-danger mt-1" role="alert" style={{ fontSize: '13px' }}>
                    {errores.campos.rejection_reason}
                  </div>
                )}
              </fieldset>

              <div className="mb-3">
                <label className="form-label fw-semibold" htmlFor="detalle-rechazo" style={{ fontSize: '14px' }}>
                  Detalle para el buzo
                </label>
                <textarea id="detalle-rechazo" rows={3}
                          className={`form-control${errores.campos.content ? ' is-invalid' : ''}`}
                          placeholder="Qué está mal y qué hay que corregir…"
                          value={detalle} onChange={(e) => setDetalle(e.target.value)} />
                {errores.campos.content && (
                  <div className="invalid-feedback d-block" role="alert">{errores.campos.content}</div>
                )}
              </div>

              <div style={{
                background: '#f1f6ff', border: '1px solid #cfe0fb', borderRadius: '10px',
                padding: '10px 12px', fontSize: '13px', color: '#25406f',
              }}>
                <i className="bi bi-envelope me-2"></i>
                {correo
                  ? <>Al confirmar, se le manda un correo a <strong>{correo}</strong> con el motivo y el detalle.</>
                  : <>El buzo no tiene un correo cargado: el rechazo se guarda, pero no se envía ningún aviso.</>}
              </div>

              {errores.general && (
                <div className="alert alert-danger mt-3 mb-0 py-2" role="alert" style={{ fontSize: '13px' }}>
                  {errores.general}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onCancelar} disabled={enviando}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-danger" disabled={enviando}>
                {enviando ? 'Guardando…' : 'Rechazar y notificar'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

const FichaBuzo = ({ onLogout, perfil }) => {
  const { id } = useParams();
  const location = useLocation();
  const role = perfil?.role;

  // De dónde se vino: los filtros del listado, para devolverlos intactos. Si se
  // llegó directo a la ficha (un enlace, una recarga sin historia), vuelve al
  // listado sin filtros.
  const desde = location.state?.desde || '';

  const [resultado, setResultado] = useState(null);
  const [intento, setIntento] = useState(0);
  const [ocupado, setOcupado] = useState(null);
  const [errorDelPunto, setErrorDelPunto] = useState({});
  const [rechazando, setRechazando] = useState(null);

  const clave = `${id}#${intento}`;

  useEffect(() => {
    let vigente = true;
    api.get(`plantel/${id}/`)
      .then((res) => { if (vigente) setResultado({ clave, ficha: res.data }); })
      .catch((error) => { if (vigente) setResultado({ clave, error }); });
    return () => { vigente = false; };
  }, [id, clave]);

  const recargar = useCallback(() => setIntento((i) => i + 1), []);

  // La ficha anterior sigue en pantalla mientras llega la nueva, para que un
  // dictamen no haga parpadear toda la página; pero sólo si es del mismo buzo.
  const ficha = resultado?.ficha && String(resultado.ficha.id) === String(id) ? resultado.ficha : null;
  const cargando = resultado?.clave !== clave;
  const fallo = !cargando ? resultado?.error : null;

  const dictaminar = async (estudio, cuerpo) => {
    await api.post('comments/', { block: estudio.bloque, ...cuerpo });
    recargar();
  };

  const aprobar = async (estudio) => {
    setOcupado(estudio.code);
    setErrorDelPunto((e) => ({ ...e, [estudio.code]: null }));
    try {
      await dictaminar(estudio, { status: estadoAlAprobar(role) });
    } catch (error) {
      setErrorDelPunto((e) => ({
        ...e, [estudio.code]: mensajeDelFallo(error, 'No se pudo guardar el dictamen.'),
      }));
    } finally {
      setOcupado(null);
    }
  };

  const revertir = async (estudio) => {
    setOcupado(estudio.code);
    setErrorDelPunto((e) => ({ ...e, [estudio.code]: null }));
    try {
      await api.post(`comments/${estudio.revertible_id}/revertir/`);
      recargar();
    } catch (error) {
      setErrorDelPunto((e) => ({
        ...e, [estudio.code]: mensajeDelFallo(error, 'No se pudo revertir la aprobación.'),
      }));
    } finally {
      setOcupado(null);
    }
  };

  const confirmarRechazo = async (campos) => {
    await dictaminar(rechazando, { status: 'REJECTED', ...campos });
    setRechazando(null);
  };

  const cerrarElDialogo = useCallback(() => setRechazando(null), []);

  const turno = ficha ? celdaTurno(ficha.turno) : null;
  const nombre = ficha
    ? [ficha.apellido, ficha.nombre].filter(Boolean).join(', ') || 'Sin nombre'
    : '';

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={role} onLogout={onLogout} />

      <div className="flex-grow-1 bg-light" style={{ minWidth: 0 }}>
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '980px' }}>
          <Link to={`/plantel${desde}`} className="text-decoration-none d-inline-block mb-3"
                style={{ fontSize: '13.5px' }}>
            ← Volver al listado
          </Link>

          {fallo && !ficha && (
            <div className="alert alert-warning d-flex align-items-center justify-content-between gap-3" role="alert">
              <span>
                {fallo.response?.status === 404
                  ? 'No hay ningún buzo con ese número.'
                  : fallo.response?.status === 403
                    ? 'Esta pantalla es sólo para el médico y los enfermeros auxiliares.'
                    : mensajeDelFallo(fallo, 'No se pudo cargar la ficha.')}
              </span>
              {fallo.response?.status !== 404 && fallo.response?.status !== 403 && (
                <button type="button" className="btn btn-sm btn-outline-dark" onClick={recargar}>
                  Reintentar
                </button>
              )}
            </div>
          )}

          {!ficha && !fallo && <div className="text-muted">Cargando…</div>}

          {ficha && (
            <>
              <div className="bg-white" style={{ borderRadius: '12px', padding: '18px 20px', marginBottom: '16px' }}>
                <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
                  <div>
                    <h1 className="fw-bold m-0" style={{ fontSize: '20px', color: '#15213b' }}>
                      {[ficha.grado, nombre].filter(Boolean).join(' ')}
                    </h1>
                    <div style={{ fontSize: '13px', color: '#6b7694', marginTop: '4px' }}>
                      {renglonDelEncabezado(ficha)}
                    </div>
                    <div style={{ fontSize: '13px', color: '#6b7694', marginTop: '2px' }}>
                      Turno: <strong style={{ color: '#15213b' }}>{turno.principal}</strong>
                      {turno.fechas && <> · {turno.fechas}</>}
                    </div>
                  </div>
                  <Contadores ficha={ficha} />
                </div>
              </div>

              <div className="bg-white" style={{
                borderRadius: '12px', overflow: 'hidden',
                opacity: cargando ? 0.6 : 1, transition: 'opacity .15s',
              }}>
                {ficha.estudios.map((estudio) => (
                  <Punto
                    key={estudio.code}
                    estudio={estudio}
                    rol={role}
                    ocupado={ocupado}
                    error={errorDelPunto[estudio.code]}
                    onAprobar={aprobar}
                    onRechazar={setRechazando}
                    onRevertir={revertir}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {rechazando && (
        <DialogoDeRechazo
          estudio={rechazando}
          correo={ficha?.correo}
          onCancelar={cerrarElDialogo}
          onConfirmar={confirmarRechazo}
        />
      )}
    </div>
  );
};

export default FichaBuzo;
