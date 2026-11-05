import React, { useState, useEffect } from 'react';
import api from '../api';
import Sidebar from './Sidebar';

const Admin = ({ onLogout }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('especialidades');

  const [specialties, setSpecialties] = useState([]);
  const [newSpecialty, setNewSpecialty] = useState('');
  const [editing, setEditing] = useState(null); // { id, name }

  const [privilegedUsers, setPrivilegedUsers] = useState([]);
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [newInstructorEmail, setNewInstructorEmail] = useState('');

  const EMPTY_SCOPE = { grantee_email: '', access_level: 'VIEW', age_min: '', age_max: '' };
  const [scopes, setScopes] = useState([]);
  const [scopeForm, setScopeForm] = useState(EMPTY_SCOPE);

  useEffect(() => {
    (async () => {
      try {
        const [pRes, sRes] = await Promise.all([api.get('profiles/me/'), api.get('specialties/')]);
        setProfile(pRes.data);
        setSpecialties(sRes.data);
        if (pRes.data?.user?.is_superuser) {
          fetchPrivileged();
          fetchScopes();
        }
      } catch (err) {
        console.error('Error cargando panel de administración', err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const fetchSpecialties = async () => setSpecialties((await api.get('specialties/')).data);
  const fetchScopes = async () => {
    try {
      setScopes((await api.get('auditor-scopes/')).data);
    } catch { /* sin permisos */ }
  };

  const addScope = async (e) => {
    e.preventDefault();
    try {
      await api.post('auditor-scopes/', {
        ...scopeForm,
        age_min: scopeForm.age_min === '' ? null : Number(scopeForm.age_min),
        age_max: scopeForm.age_max === '' ? null : Number(scopeForm.age_max),
      });
      setScopeForm(EMPTY_SCOPE);
      fetchScopes();
    } catch (err) {
      const d = err.response?.data || {};
      alert(d.grantee_email || d.age_max || d.age_min || 'Error al otorgar el acceso');
    }
  };

  const deleteScope = async (s) => {
    if (!window.confirm(`¿Quitar el acceso de ${s.grantee_details?.email} a los buzos de ${s.age_label}?`)) return;
    try {
      await api.delete(`auditor-scopes/${s.id}/`);
      fetchScopes();
    } catch {
      alert('Error al quitar el acceso');
    }
  };

  const fetchPrivileged = async () => {
    try {
      setPrivilegedUsers((await api.get('superusers/privileged/')).data);
    } catch { /* no superuser */ }
  };

  const addSpecialty = async (e) => {
    e.preventDefault();
    try {
      await api.post('specialties/', { name: newSpecialty });
      setNewSpecialty('');
      fetchSpecialties();
    } catch (err) {
      alert(err.response?.data?.name || 'Error al crear la especialidad');
    }
  };

  const saveSpecialty = async (e) => {
    e.preventDefault();
    try {
      await api.put(`specialties/${editing.id}/`, { name: editing.name });
      setEditing(null);
      fetchSpecialties();
    } catch (err) {
      alert(err.response?.data?.name || 'Error al guardar la especialidad');
    }
  };

  const deleteSpecialty = async (s) => {
    if (!window.confirm(`¿Eliminar la especialidad "${s.name}"? Los usuarios que la tengan asignada quedarán sin especialidad.`)) return;
    try {
      await api.delete(`specialties/${s.id}/`);
      fetchSpecialties();
    } catch {
      alert('Error al eliminar la especialidad');
    }
  };

  const promote = async (e, endpoint, email, reset) => {
    e.preventDefault();
    try {
      const res = await api.post(endpoint, { email });
      alert(res.data.message);
      reset('');
      fetchPrivileged();
    } catch (err) {
      alert(err.response?.data?.error || 'Error al otorgar permisos');
    }
  };

  const revokePrivilege = async (email, role) => {
    const label = role === 'superuser' ? 'superusuario' : 'instructor';
    if (!window.confirm(`¿Revocar permisos de ${label} a ${email}?`)) return;
    try {
      const endpoint = role === 'superuser' ? 'superusers/revoke/' : 'superusers/revoke-instructor/';
      const res = await api.post(endpoint, { email });
      alert(res.data.message);
      fetchPrivileged();
    } catch (err) {
      alert(err.response?.data?.error || 'Error al revocar permisos');
    }
  };

  if (loading) return <div className="p-5 text-center">Cargando...</div>;

  const isSuperUser = profile?.user?.is_superuser;

  if (!isSuperUser) {
    return (
      <div className="d-flex" style={{ minHeight: '100vh' }}>
        <Sidebar active="/admin" onLogout={onLogout} isSuperUser={false} />
        <div className="main-content flex-grow-1 p-5 bg-light">
          <div className="alert alert-warning">No tienes permisos para acceder al panel de administración.</div>
        </div>
      </div>
    );
  }

  const privilegedOf = (role) => privilegedUsers.filter(u => u.role === role);

  const PrivilegeList = ({ role, empty }) => (
    privilegedOf(role).length === 0
      ? <p className="text-muted small">{empty}</p>
      : privilegedOf(role).map(u => (
        <div key={`${role}-${u.id}`} className="d-flex justify-content-between align-items-center py-2 border-bottom">
          <div>
            <div className="fw-medium small">{u.name || u.email}</div>
            <div className="text-muted" style={{ fontSize: '0.75rem' }}>{u.email}</div>
          </div>
          <button className="btn btn-outline-danger btn-sm rounded-pill px-3" onClick={() => revokePrivilege(u.email, role)}>
            Revocar
          </button>
        </div>
      ))
  );

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <Sidebar active="/admin" onLogout={onLogout} isSuperUser={isSuperUser} />

      <div className="main-content flex-grow-1 p-5 bg-light overflow-auto">
        <div className="mb-5">
          <h2 className="fw-bold mb-1">Panel de Administración</h2>
          <p className="text-muted">Especialidades del sistema, permisos de usuarios y accesos de lectura por rango de edad.</p>
        </div>

        <div className="nav nav-tabs border-0 mb-4 gap-2">
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'especialidades' ? 'bg-primary text-white' : 'text-muted'}`}
                  onClick={() => setActiveTab('especialidades')}>
            Especialidades ({specialties.length})
          </button>
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'usuarios' ? 'bg-primary text-white' : 'text-muted'}`}
                  onClick={() => setActiveTab('usuarios')}>
            Permisos de Usuarios
          </button>
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'auditores' ? 'bg-primary text-white' : 'text-muted'}`}
                  onClick={() => setActiveTab('auditores')}>
            Lectores y Auditores ({scopes.length})
          </button>
        </div>

        {activeTab === 'auditores' && (
          <div className="row g-4">
            <div className="col-lg-5">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-3">Habilitar por Rango de Edad</h5>
                <form onSubmit={addScope}>
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-uppercase text-muted">Correo del profesional</label>
                    <input type="email" className="form-control rounded-pill" placeholder="medico@ejercito.mil.ar"
                           value={scopeForm.grantee_email}
                           onChange={e => setScopeForm({ ...scopeForm, grantee_email: e.target.value })} required />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-uppercase text-muted">Nivel de acceso</label>
                    <select className="form-select rounded-pill" value={scopeForm.access_level}
                            onChange={e => setScopeForm({ ...scopeForm, access_level: e.target.value })}>
                      <option value="VIEW">Lector (solo ver los estudios)</option>
                      <option value="MODIFY">Auditor (ver y dictaminar)</option>
                    </select>
                  </div>
                  <div className="row g-2 mb-3">
                    <div className="col-6">
                      <label className="form-label small fw-bold text-uppercase text-muted">Edad desde</label>
                      <input type="number" min="0" className="form-control rounded-pill" placeholder="22"
                             value={scopeForm.age_min}
                             onChange={e => setScopeForm({ ...scopeForm, age_min: e.target.value })} />
                    </div>
                    <div className="col-6">
                      <label className="form-label small fw-bold text-uppercase text-muted">Edad hasta</label>
                      <input type="number" min="0" className="form-control rounded-pill" placeholder="25"
                             value={scopeForm.age_max}
                             onChange={e => setScopeForm({ ...scopeForm, age_max: e.target.value })} />
                    </div>
                  </div>
                  <button type="submit" className="btn btn-primary w-100 rounded-pill py-2 fw-bold">Otorgar Acceso</button>
                </form>
                <p className="text-muted small mt-3 mb-0">
                  El profesional ve los estudios de todos los buzos dentro del rango sin que cada uno
                  se lo comparta. Dejá una edad vacía para no poner tope por ese lado; las dos vacías
                  habilitan todos los buzos. Un buzo que no cargó su edad no entra en ningún rango con tope.
                </p>
              </div>
            </div>

            <div className="col-lg-7">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-4">Accesos Otorgados</h5>
                {scopes.length === 0 && <p className="text-muted small">No hay lectores ni auditores habilitados.</p>}
                {scopes.map(s => (
                  <div key={s.id} className="d-flex justify-content-between align-items-center py-3 border-bottom gap-2">
                    <div>
                      <div className="fw-medium small">
                        {s.grantee_details?.first_name || s.grantee_details?.last_name
                          ? `${s.grantee_details.first_name} ${s.grantee_details.last_name}`.trim()
                          : s.grantee_details?.email}
                      </div>
                      <div className="text-muted" style={{ fontSize: '0.75rem' }}>{s.grantee_details?.email}</div>
                      <div className="mt-2 d-flex align-items-center gap-2 flex-wrap">
                        <span className={`badge rounded-pill px-3 ${s.access_level === 'MODIFY' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'}`}>
                          {s.access_level === 'MODIFY' ? 'Auditor' : 'Lector'}
                        </span>
                        <span className="badge bg-light text-dark rounded-pill px-3">{s.age_label}</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>{s.divers_count} buzos alcanzados</span>
                      </div>
                    </div>
                    <button className="btn btn-outline-danger btn-sm rounded-pill px-3" onClick={() => deleteScope(s)}>
                      Quitar
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'especialidades' && (
          <div className="row g-4">
            <div className="col-lg-5">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-3">Nueva Especialidad</h5>
                <form onSubmit={addSpecialty} className="d-flex gap-2">
                  <input type="text" className="form-control rounded-pill" placeholder="Ej: Medicina Hiperbárica"
                         value={newSpecialty} onChange={e => setNewSpecialty(e.target.value)} required />
                  <button type="submit" className="btn btn-primary rounded-pill px-4">Agregar</button>
                </form>
                <p className="text-muted small mt-3 mb-0">
                  Las especialidades cargadas aquí son las que los usuarios podrán elegir en su perfil.
                </p>
              </div>
            </div>

            <div className="col-lg-7">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-4">Especialidades Cargadas</h5>
                {specialties.length === 0 && <p className="text-muted small">No hay especialidades cargadas.</p>}
                {specialties.map(s => (
                  <div key={s.id} className="d-flex justify-content-between align-items-center py-2 border-bottom gap-2">
                    {editing?.id === s.id ? (
                      <form onSubmit={saveSpecialty} className="d-flex gap-2 flex-grow-1">
                        <input type="text" className="form-control form-control-sm rounded-pill" value={editing.name}
                               onChange={e => setEditing({ ...editing, name: e.target.value })} required autoFocus />
                        <button type="submit" className="btn btn-primary btn-sm rounded-pill px-3">Guardar</button>
                        <button type="button" className="btn btn-light btn-sm rounded-pill px-3" onClick={() => setEditing(null)}>Cancelar</button>
                      </form>
                    ) : (
                      <>
                        <span className="fw-medium small">{s.name}</span>
                        <div className="d-flex gap-2">
                          <button className="btn btn-outline-secondary btn-sm rounded-pill px-3" onClick={() => setEditing({ id: s.id, name: s.name })}>
                            Editar
                          </button>
                          <button className="btn btn-outline-danger btn-sm rounded-pill px-3" onClick={() => deleteSpecialty(s)}>
                            Eliminar
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'usuarios' && (
          <div className="row g-4">
            <div className="col-md-6">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-3">Dar Permisos de Instructor</h5>
                <form onSubmit={(e) => promote(e, 'superusers/promote-instructor/', newInstructorEmail, setNewInstructorEmail)} className="d-flex gap-2 mb-4">
                  <input type="email" className="form-control rounded-pill" placeholder="Email del usuario"
                         value={newInstructorEmail} onChange={e => setNewInstructorEmail(e.target.value)} required />
                  <button type="submit" className="btn btn-primary rounded-pill px-4">Otorgar</button>
                </form>
                <h6 className="fw-bold small text-muted text-uppercase mb-3">Instructores activos</h6>
                <PrivilegeList role="instructor" empty="No hay instructores asignados." />
              </div>
            </div>

            <div className="col-md-6">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-3 text-danger">Dar Permisos de Superusuario</h5>
                <form onSubmit={(e) => promote(e, 'superusers/promote/', newAdminEmail, setNewAdminEmail)} className="d-flex gap-2 mb-4">
                  <input type="email" className="form-control rounded-pill" placeholder="Email del usuario"
                         value={newAdminEmail} onChange={e => setNewAdminEmail(e.target.value)} required />
                  <button type="submit" className="btn btn-danger rounded-pill px-4">Promover</button>
                </form>
                <h6 className="fw-bold small text-muted text-uppercase mb-3">Superusuarios activos</h6>
                <PrivilegeList role="superuser" empty="No hay otros superusuarios asignados." />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Admin;
