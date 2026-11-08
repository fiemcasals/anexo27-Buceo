import { useState, useEffect, useCallback } from 'react';
import api from '../api';
import BarraLateral from './BarraLateral';

// La lista de usuarios del administrador: ver quién está registrado, borrar una
// cuenta o ponerle una contraseña nueva a quien la olvidó. Las cuentas de
// administración se ven pero no se tocan desde acá (el servidor tampoco deja).

const ROL = {
  USER: 'Buzo', NURSE: 'Enfermero auxiliar', DOCTOR: 'Médico', ADMIN: 'Administrador',
};

// El tipo de usuario se lee de un vistazo: un color por rol.
const COLOR = {
  USER: 'text-bg-secondary', NURSE: 'text-bg-info', DOCTOR: 'text-bg-success',
  ADMIN: 'text-bg-dark',
};

function mensajeDe(err, porDefecto) {
  const d = err.response?.data;
  if (!d) return porDefecto;
  if (typeof d === 'string') return d;
  const primero = d.detail || d.password || Object.values(d)[0];
  return Array.isArray(primero) ? primero.join(' ') : String(primero || porDefecto);
}

const Usuarios = ({ onLogout, perfil }) => {
  const [usuarios, setUsuarios] = useState(null);
  const [fallo, setFallo] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  // Qué fila está en medio de una acción: { id, tipo: 'borrar' | 'clave' }.
  const [accion, setAccion] = useState(null);
  const [clave, setClave] = useState('');
  const [aviso, setAviso] = useState(null);
  const [error, setError] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const traer = useCallback(() => api.get('admin/usuarios/')
    .then((res) => { setUsuarios(res.data); setFallo(null); })
    .catch(() => setFallo('No se pudo cargar la lista de usuarios.')), []);

  useEffect(() => { traer(); }, [traer]);

  const abrir = (id, tipo) => {
    setAccion({ id, tipo }); setClave(''); setError(null); setAviso(null);
  };
  const cerrar = () => { setAccion(null); setClave(''); setError(null); };

  const borrar = (u) => {
    setTrabajando(true); setError(null);
    api.delete(`admin/usuarios/${u.id}/`)
      .then(() => { cerrar(); setAviso(`Se borró a ${u.nombre}.`); return traer(); })
      .catch((err) => setError(mensajeDe(err, 'No se pudo borrar.')))
      .finally(() => setTrabajando(false));
  };

  const cambiarClave = (u) => {
    setTrabajando(true); setError(null);
    api.post(`admin/usuarios/${u.id}/clave/`, { password: clave })
      .then(() => { cerrar(); setAviso(`Se cambió la contraseña de ${u.nombre}.`); })
      .catch((err) => setError(mensajeDe(err, 'No se pudo cambiar la contraseña.')))
      .finally(() => setTrabajando(false));
  };

  const q = busqueda.trim().toLowerCase();
  const visibles = (usuarios || []).filter((u) =>
    !q || `${u.nombre} ${u.email} ${u.dni}`.toLowerCase().includes(q));

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={perfil?.role} onLogout={onLogout} />
      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '900px' }}>
          <h1 className="fw-bold mb-3" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
            Usuarios
          </h1>

          {fallo && <div className="alert alert-warning" role="alert">{fallo}</div>}
          {aviso && <div className="alert alert-success py-2" role="status">{aviso}</div>}
          {!usuarios && !fallo && <div className="text-muted">Cargando…</div>}

          {usuarios && (
            <>
              <input type="search" className="form-control mb-3"
                     placeholder="Buscar por nombre, correo o DNI"
                     aria-label="Buscar usuario" value={busqueda}
                     onChange={(e) => setBusqueda(e.target.value)} />
              <div className="text-muted mb-2" style={{ fontSize: '13px' }}>
                {visibles.length} de {usuarios.length} usuarios
              </div>
              <div className="list-group">
                {visibles.map((u) => (
                  <div key={u.id} className="list-group-item">
                    <div className="d-flex flex-wrap align-items-center gap-2">
                      <div style={{ flex: '1 1 0', minWidth: 0 }}>
                        <div className="fw-semibold">{u.nombre}</div>
                        <div className="text-muted" style={{ fontSize: '13px' }}>
                          {u.email}{u.dni ? ` · DNI ${u.dni}` : ''}
                        </div>
                      </div>
                      <div style={{ minWidth: '150px' }}>
                        <span className={`badge ${COLOR[u.role] || 'text-bg-light border'}`}
                              aria-label={`Tipo de usuario: ${ROL[u.role] || 'Sin perfil'}`}>
                          {ROL[u.role] || 'Sin perfil'}
                        </span>
                      </div>
                      {u.protegido ? (
                        <span className="text-muted" style={{ fontSize: '12px' }}>
                          Cuenta de administración
                        </span>
                      ) : (
                        <div className="d-flex gap-2">
                          <button type="button" className="btn btn-sm btn-outline-secondary"
                                  onClick={() => abrir(u.id, 'clave')}>
                            Cambiar contraseña
                          </button>
                          <button type="button" className="btn btn-sm btn-outline-danger"
                                  onClick={() => abrir(u.id, 'borrar')}>
                            Eliminar
                          </button>
                        </div>
                      )}
                    </div>

                    {accion?.id === u.id && accion.tipo === 'clave' && (
                      <form className="mt-3 d-flex flex-wrap gap-2"
                            onSubmit={(e) => { e.preventDefault(); cambiarClave(u); }}>
                        <input type="password" className="form-control"
                               style={{ maxWidth: '280px' }} autoComplete="new-password"
                               aria-label={`Contraseña nueva de ${u.nombre}`}
                               placeholder="Contraseña nueva" value={clave}
                               onChange={(e) => setClave(e.target.value)} />
                        <button type="submit" className="btn btn-primary"
                                disabled={trabajando || !clave}>Guardar</button>
                        <button type="button" className="btn btn-link" onClick={cerrar}>
                          Cancelar
                        </button>
                        <div className="form-text w-100">
                          Se cierran las sesiones abiertas de esa persona.
                        </div>
                      </form>
                    )}

                    {accion?.id === u.id && accion.tipo === 'borrar' && (
                      <div className="mt-3 alert alert-danger mb-0">
                        Se borra a <strong>{u.nombre}</strong> con sus estudios y su
                        historial. No se puede deshacer.
                        <div className="d-flex gap-2 mt-2">
                          <button type="button" className="btn btn-danger btn-sm"
                                  disabled={trabajando} onClick={() => borrar(u)}>
                            Sí, eliminar
                          </button>
                          <button type="button" className="btn btn-link btn-sm" onClick={cerrar}>
                            Cancelar
                          </button>
                        </div>
                      </div>
                    )}

                    {accion?.id === u.id && error && (
                      <div className="text-danger mt-2" role="alert"
                           style={{ fontSize: '14px' }}>{error}</div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Usuarios;
