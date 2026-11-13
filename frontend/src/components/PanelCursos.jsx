import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import BarraLateral from './BarraLateral';

// Panel del administrador: cuántos buzos tienen cada curso, en barras. Tocar una
// barra muestra quiénes son, con el enlace a su perfil.

const PanelCursos = ({ onLogout, perfil }) => {
  const [datos, setDatos] = useState(null);
  const [fallo, setFallo] = useState('');
  const [abierto, setAbierto] = useState(null);

  useEffect(() => {
    api.get('admin/cursos/resumen/')
      .then((res) => setDatos(res.data))
      .catch(() => setFallo('No se pudo traer el resumen de cursos.'));
  }, []);

  const total = datos?.total_buzos || 0;
  const cursos = datos ? [...datos.cursos].sort((a, b) => b.cantidad - a.cantidad) : [];
  const maximo = Math.max(1, ...cursos.map((c) => c.cantidad));

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={perfil?.role} onLogout={onLogout} />
      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '900px' }}>
          <h1 className="fw-bold mb-1" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
            Cursos
          </h1>
          <div className="mb-3" style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>
            Buzos con cada curso de buceo. Tocá una barra para ver quiénes son.
          </div>

          {fallo && <div className="alert alert-warning" role="alert">{fallo}</div>}
          {!datos && !fallo && <div className="text-muted">Cargando…</div>}

          {datos && (
            <>
              <div className="d-flex flex-wrap gap-2 mb-3">
                <span className="badge text-bg-secondary">{total} buzos</span>
                <span className="badge text-bg-secondary">{datos.sin_cursos} sin ningún curso marcado</span>
              </div>

              <div className="card p-3">
                {total === 0 && <div className="text-muted">Todavía no hay buzos registrados.</div>}
                {cursos.map((c) => {
                  const activo = c.valor === abierto;
                  return (
                    <div key={c.valor} className="mb-1">
                    <button type="button"
                            className="btn text-start p-2 border-0 w-100 barra-curso"
                            style={{ background: activo ? 'var(--superficie-2)' : 'transparent' }}
                            aria-expanded={activo}
                            aria-label={`${c.etiqueta}: ${c.cantidad} de ${total} buzos`}
                            onClick={() => setAbierto(activo ? null : c.valor)}>
                      <div className="d-flex justify-content-between gap-2" style={{ fontSize: '14px' }}>
                        <span style={{ minWidth: 0, overflowWrap: 'anywhere' }}>{c.etiqueta}</span>
                        <span className="fw-semibold">{c.cantidad}</span>
                      </div>
                      <div style={{ height: '10px', background: 'var(--borde)', borderRadius: '5px' }}
                           aria-hidden="true">
                        <div style={{
                          height: '100%', borderRadius: '5px', background: 'var(--oro)',
                          width: `${(c.cantidad / maximo) * 100}%`,
                          minWidth: c.cantidad ? '4px' : 0,
                        }} />
                      </div>
                    </button>
                    {activo && (
                      <div className="mx-2 mb-2 px-3 py-2 rounded-3"
                           style={{ border: '1px solid var(--borde)', borderLeft: '3px solid var(--oro)' }}>
                        {c.buzos.length === 0
                          ? <div className="text-muted" style={{ fontSize: '14px' }}>
                              Ningún buzo marcó este curso.
                            </div>
                          : (
                            <ul className="mb-0 ps-3" style={{ fontSize: '14px' }}>
                              {c.buzos.map((b) => (
                                <li key={b.id}><Link to={`/usuarios?abrir=${b.id}`}>{b.nombre}</Link></li>
                              ))}
                            </ul>
                          )}
                      </div>
                    )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default PanelCursos;
