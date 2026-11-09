import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api from '../api';
import { nombreConGrado } from '../lib/nombre-con-grado';
import BarraLateral from './BarraLateral';
import Pastilla from './Pastilla';
import { leerFiltros, escribirFiltros } from '../lib/plantel';
import {
  FILTROS, ORDENES, ordenVigente, celdaPresentados, celdaTurno, rotuloDelTurno,
  turnoActivo, valorDelSelectorDeTurno, celdaUltimaRevision, estadoDeLaFila,
  subtituloDelListado, conCambio, mensajeDelFallo,
} from '../lib/pantallas-del-revisor';

// El listado del plantel (§8.1): una fila por buzo, ya contada y paginada por
// el servidor. Es la pantalla de trabajo del médico y de los enfermeros
// auxiliares, la misma para los dos; sólo cambia el orden con el que entran.
//
// Los filtros viven en la dirección de la página (`?buscar=&filtro=&turno=...`)
// y no en el estado de React: el médico filtra, abre una ficha, dictamina y
// vuelve, y tiene que encontrar la lista como la dejó. Esta pantalla no guarda
// ningún filtro por su cuenta: los lee de `location.search` y, para cambiarlos,
// navega a otra dirección.
//
// Los tres contadores de arriba se recalculan con el buscador y el turno, a
// propósito: dicen cuántos buzos habría en cada solapa dentro de lo buscado.

const ESPERA_DEL_BUSCADOR_MS = 300;

const ENCABEZADO = {
  fontSize: '10.5px',
  textTransform: 'uppercase',
  letterSpacing: '.6px',
  color: 'var(--texto-suave)',
  fontWeight: 600,
  whiteSpace: 'nowrap',
};

const CONTADORES = [
  { clave: 'aptos', rotulo: 'Aptos', color: 'var(--ok)', fondo: 'var(--ok-fondo)', borde: 'var(--ok-borde)' },
  { clave: 'a_revisar', rotulo: 'A revisar', color: 'var(--aviso-texto)', fondo: 'var(--aviso-fondo)', borde: 'var(--aviso-borde)' },
  { clave: 'vencidos', rotulo: 'Vencidos', color: 'var(--peligro-texto)', fondo: 'var(--peligro-fondo)', borde: 'var(--peligro-borde)' },
];

function Contadores({ contadores }) {
  return (
    <div className="d-flex gap-2">
      {CONTADORES.map((c) => (
        <div key={c.clave}
             style={{
               background: c.fondo, border: `1px solid ${c.borde}`, borderRadius: '10px',
               padding: '9px 15px', textAlign: 'center', minWidth: '92px',
             }}>
          <div style={{ fontSize: '21px', fontWeight: 700, color: c.color, lineHeight: 1 }}>
            {contadores ? contadores[c.clave] : '–'}
          </div>
          <div style={{
            fontSize: '10px', color: c.color, textTransform: 'uppercase',
            letterSpacing: '.5px', marginTop: '3px',
          }}>
            {c.rotulo}
          </div>
        </div>
      ))}
    </div>
  );
}

function ARevisar({ fila }) {
  if (fila.a_revisar === 0) return <span style={{ color: 'var(--borde)' }}>—</span>;
  return (
    <div className="d-flex flex-column align-items-center gap-1">
      {fila.sin_tocar > 0 && (
        <Pastilla tono="aviso" titulo="Subidos que nadie tocó">
          {fila.sin_tocar} sin tocar
        </Pastilla>
      )}
      {fila.pre_revisados > 0 && (
        <Pastilla tono="neutro" titulo="Pre-revisados por un enfermero, a la espera de la firma del médico">
          {fila.pre_revisados} pre-revisados
        </Pastilla>
      )}
    </div>
  );
}

function Fila({ fila, desde, onAbrir }) {
  const presentados = celdaPresentados(fila);
  const turno = celdaTurno(fila.turno);
  const estado = estadoDeLaFila(fila);
  const nombre = nombreConGrado(fila) || 'Sin nombre';
  const subtitulo = fila.unidad || '';
  return (
    <tr style={{ cursor: 'pointer', borderBottom: '1px solid var(--superficie-2)' }}
        onClick={() => onAbrir(fila.id)}>
      <td style={{ padding: '13px 26px' }}>
        <Link to={`/plantel/${fila.id}`} state={{ desde }}
              onClick={(e) => e.stopPropagation()}
              className="fw-bold text-decoration-none" style={{ color: 'var(--texto-fuerte)' }}>
          {nombre}
        </Link>
        {subtitulo && (
          <div style={{ color: 'var(--texto-suave)', fontSize: '12px', marginTop: '2px' }}>{subtitulo}</div>
        )}
      </td>
      <td style={{ padding: '13px 10px', color: 'var(--texto-suave)', whiteSpace: 'nowrap' }}>{fila.dni || '—'}</td>
      <td style={{ padding: '13px 10px', textAlign: 'center', color: 'var(--texto-suave)' }}
          title="La edad que usó la regla: el año del turno menos el año de nacimiento">
        {fila.edad ?? '—'}
      </td>
      <td style={{ padding: '13px 10px', color: 'var(--texto-suave)' }}>
        <div className={fila.turno ? '' : 'fst-italic'} style={{ whiteSpace: 'nowrap' }}>{turno.principal}</div>
        {turno.fechas && <div style={{ fontSize: '12px', color: 'var(--texto-suave)' }}>{turno.fechas}</div>}
      </td>
      <td style={{ padding: '13px 10px', textAlign: 'center' }}>
        <strong style={{
          color: presentados.sinDeterminar || presentados.completo ? undefined : 'var(--peligro-texto)',
          fontSize: presentados.sinDeterminar ? '12.5px' : undefined,
          whiteSpace: presentados.sinDeterminar ? 'normal' : 'nowrap',
        }}>
          {presentados.texto}
        </strong>
      </td>
      <td style={{ padding: '13px 10px', textAlign: 'center' }}><ARevisar fila={fila} /></td>
      <td style={{ padding: '13px 10px', color: 'var(--texto-suave)', whiteSpace: 'nowrap' }}>
        {celdaUltimaRevision(fila.ultima_revision)}
      </td>
      <td style={{ padding: '13px 26px 13px 10px' }}>
        <Pastilla tono={estado.tono}>{estado.conTilde ? `✓ ${estado.texto}` : estado.texto}</Pastilla>
      </td>
    </tr>
  );
}

function Paginador({ pagina, paginas, onIr }) {
  if (paginas <= 1) return null;
  return (
    <nav className="d-flex align-items-center justify-content-center gap-3 py-3"
         aria-label="Páginas del listado">
      <button type="button" className="btn btn-outline-secondary btn-sm"
              disabled={pagina <= 1} onClick={() => onIr(pagina - 1)}>
        Anterior
      </button>
      <span style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>
        Página {pagina} de {paginas}
      </span>
      <button type="button" className="btn btn-outline-secondary btn-sm"
              disabled={pagina >= paginas} onClick={() => onIr(pagina + 1)}>
        Siguiente
      </button>
    </nav>
  );
}

const ListadoPlantel = ({ onLogout, perfil }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const role = perfil?.role;

  // `undefined`: la lista de turnos todavía no contestó. Un fallo la deja
  // vacía: sin lista no hay forma de nombrar un turno, y entonces ningún
  // filtro de turno puede estar activo.
  const [turnos, setTurnos] = useState(undefined);
  const [resultado, setResultado] = useState(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vigente = true;
    api.get('fechas/')
      .then((res) => { if (vigente) setTurnos(res.data); })
      .catch(() => { if (vigente) setTurnos([]); });
    return () => { vigente = false; };
  }, []);

  // Los filtros, tal como los dejó la dirección, salvo un turno que la lista no
  // conoce: ese no se muestra como activo **ni se manda al servidor**. Un id
  // viejo o inventado en la dirección dejaría la tabla vacía sin que el médico
  // pudiera ver qué la vació.
  const filtros = useMemo(() => {
    const crudos = leerFiltros(location.search);
    if (turnos === undefined || crudos.turno === null) return crudos;
    return turnoActivo(crudos.turno, turnos) ? crudos : { ...crudos, turno: null };
  }, [location.search, turnos]);

  const esperandoTurnos = turnos === undefined && typeof filtros.turno === 'number';
  const orden = ordenVigente(filtros, role);

  // Lo que se le pide al servidor. El orden va siempre explícito: sin él, el
  // servidor ordena por apellido y la pila con la que el rol entra no existiría.
  const peticion = useMemo(
    () => escribirFiltros({ ...filtros, orden }),
    [filtros, orden],
  );
  const clave = `${peticion}#${intento}`;

  useEffect(() => {
    if (esperandoTurnos) return undefined;
    let vigente = true;
    api.get(`plantel/${peticion}`)
      .then((res) => { if (vigente) setResultado({ clave, datos: res.data }); })
      .catch((error) => { if (vigente) setResultado({ clave, error }); });
    return () => { vigente = false; };
  }, [peticion, clave, esperandoTurnos]);

  const cargando = esperandoTurnos || resultado?.clave !== clave;
  const datos = resultado?.datos;
  const fallo = !cargando ? resultado?.error : null;

  // El buscador: el texto que se tipea es local, y pasa a la dirección cuando
  // la persona hace una pausa. Si la dirección cambia por otro lado (el botón
  // de atrás, un enlace), el texto la sigue. `emitido` es lo último que este
  // campo mandó a la dirección: cuando vuelve como eco no se pisa lo que ya se
  // siguió tipeando.
  const [texto, setTexto] = useState(
    { valor: filtros.buscar, deLaDireccion: filtros.buscar, emitido: null });
  if (filtros.buscar !== texto.deLaDireccion) {
    setTexto((t) => (t.emitido === filtros.buscar
      ? { ...t, deLaDireccion: filtros.buscar }
      : { valor: filtros.buscar, deLaDireccion: filtros.buscar, emitido: null }));
  }

  const ir = (cambio, { reemplazar = false } = {}) => {
    navigate({ pathname: '/plantel', search: escribirFiltros(conCambio(filtros, cambio)) },
             { replace: reemplazar });
  };

  useEffect(() => {
    if (texto.valor === filtros.buscar) return undefined;
    const espera = setTimeout(() => {
      setTexto((t) => ({ ...t, emitido: texto.valor }));
      navigate(
        { pathname: '/plantel', search: escribirFiltros(conCambio(filtros, { buscar: texto.valor })) },
        // Escribir no apila una entrada por letra en el historial.
        { replace: true },
      );
    }, ESPERA_DEL_BUSCADOR_MS);
    return () => clearTimeout(espera);
  }, [texto.valor, filtros, navigate]);

  const hayFiltros = escribirFiltros({ ...filtros, orden: null }) !== '';
  const ajustaLosNumeros = filtros.buscar !== '' || filtros.turno !== null;
  const nombre = nombreConGrado({
    grado: perfil?.rank, nombre: perfil?.first_name, apellido: perfil?.last_name,
  });
  const forbidden = fallo?.response?.status === 403;

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={role} onLogout={onLogout} />

      <div className="flex-grow-1 bg-white" style={{ minWidth: 0 }}>
        <div style={{ padding: '22px 26px 0' }}>
          <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
            <div>
              <h1 className="fw-bold m-0" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
                Personal a controlar
              </h1>
              <div style={{ fontSize: '13px', color: 'var(--texto-suave)', marginTop: '3px' }}>
                {datos ? subtituloDelListado(datos.total) : 'Cargando…'}
                {nombre && <> · {nombre}</>}
              </div>
            </div>
            <Contadores contadores={datos?.contadores} />
          </div>
          {ajustaLosNumeros && (
            <div style={{ fontSize: '12px', color: 'var(--texto-suave)', marginTop: '8px' }}>
              Los números de arriba y de las solapas cuentan sólo lo que se busca
              y el turno elegido.
            </div>
          )}

          <div className="d-flex gap-2 flex-wrap align-items-center" style={{ marginTop: '20px' }}>
            <div style={{ flex: 1, minWidth: '260px', position: 'relative' }}>
              <i className="bi bi-search"
                 style={{ position: 'absolute', left: '13px', top: '50%',
                          transform: 'translateY(-50%)', color: 'var(--texto-suave)' }}></i>
              <input
                type="search"
                className="form-control"
                aria-label="Buscar"
                placeholder="Buscar por nombre, apellido, DNI o grado…"
                value={texto.valor}
                onChange={(e) => setTexto({ ...texto, valor: e.target.value })}
                style={{ paddingLeft: '38px', borderRadius: '10px', padding: '11px 14px 11px 38px' }}
              />
            </div>
            <label className="d-flex align-items-center gap-2 m-0" style={{ fontSize: '13.5px' }}>
              Turno
              <select
                className="form-select"
                style={{ borderRadius: '10px', minWidth: '190px' }}
                value={valorDelSelectorDeTurno(filtros.turno, turnos || [])}
                onChange={(e) => {
                  const v = e.target.value;
                  ir({ turno: v === '' ? null : v === 'sin' ? 'sin' : Number(v) });
                }}
              >
                <option value="">Todos los turnos</option>
                {(turnos || []).map((t) => (
                  <option key={t.id} value={t.id}>{rotuloDelTurno(t)}</option>
                ))}
                <option value="sin">Sin turno</option>
              </select>
            </label>
            <label className="d-flex align-items-center gap-2 m-0" style={{ fontSize: '13.5px' }}>
              Ordenar
              <select
                className="form-select"
                style={{ borderRadius: '10px', minWidth: '210px' }}
                value={orden}
                onChange={(e) => ir({ orden: e.target.value })}
              >
                {ORDENES.map((o) => <option key={o.clave} value={o.clave}>{o.rotulo}</option>)}
              </select>
            </label>
          </div>

          <div className="d-flex gap-2 flex-wrap" style={{ marginTop: '14px' }} role="tablist">
            {FILTROS.map((f) => {
              const activo = filtros.filtro === f.clave;
              return (
                <button
                  key={f.clave}
                  type="button"
                  role="tab"
                  aria-selected={activo}
                  onClick={() => ir({ filtro: f.clave })}
                  className="border-0"
                  style={{
                    background: activo ? 'var(--borde)' : 'var(--superficie-2)',
                    color: activo ? '#fff' : 'var(--texto-fuerte)',
                    borderRadius: '999px', padding: '7px 15px', fontSize: '12.5px',
                    fontWeight: activo ? 600 : 400,
                  }}
                >
                  {f.rotulo}{' '}
                  <span style={{ opacity: 0.6 }}>
                    {datos ? datos.contadores.por_filtro[f.clave] : ''}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {fallo && (
          <div className="alert alert-warning d-flex align-items-center justify-content-between gap-3"
               role="alert" style={{ margin: '18px 26px 0' }}>
            <span>
              {forbidden
                ? 'Esta pantalla es sólo para el médico y los enfermeros auxiliares.'
                : mensajeDelFallo(fallo, 'No se pudo cargar el listado.')}
            </span>
            {!forbidden && (
              <button type="button" className="btn btn-sm btn-outline-dark"
                      onClick={() => setIntento((i) => i + 1)}>
                Reintentar
              </button>
            )}
          </div>
        )}

        {!fallo && cargando && !datos && (
          <div className="p-5 text-center text-muted">Cargando…</div>
        )}

        {datos && (
          <div style={{ opacity: cargando ? 0.5 : 1, transition: 'opacity .15s' }}>
            <div className="table-responsive" style={{ marginTop: '18px' }}>
              <table className="table align-middle mb-0" style={{ fontSize: '13.5px' }}>
                <thead>
                  <tr style={{ background: 'var(--superficie-2)' }}>
                    <th style={{ ...ENCABEZADO, padding: '11px 26px' }}>Grado y nombre</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px' }}>DNI</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px', textAlign: 'center' }}>Edad</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px' }}>Turno</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px', textAlign: 'center' }}>Presentados</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px', textAlign: 'center' }}>A revisar</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 10px' }}>Última vez revisado</th>
                    <th style={{ ...ENCABEZADO, padding: '11px 26px 11px 10px' }}>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.filas.map((fila) => (
                    <Fila key={fila.id} fila={fila} desde={location.search}
                          onAbrir={(id) => navigate(`/plantel/${id}`, { state: { desde: location.search } })} />
                  ))}
                </tbody>
              </table>
            </div>

            {datos.filas.length === 0 && (
              <div className="text-center text-muted py-5">
                {hayFiltros
                  ? <>
                      <div>Ningún buzo coincide con lo buscado.</div>
                      <button type="button" className="btn btn-link"
                              onClick={() => navigate('/plantel', { replace: true })}>
                        Quitar los filtros
                      </button>
                    </>
                  : 'Todavía no hay buzos registrados.'}
              </div>
            )}

            <Paginador pagina={datos.pagina} paginas={datos.paginas}
                       onIr={(p) => ir({ pagina: p })} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ListadoPlantel;
