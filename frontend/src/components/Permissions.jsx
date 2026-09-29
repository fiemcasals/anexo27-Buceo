import React, { useState, useEffect } from 'react';
import api from '../api';
import Sidebar from './Sidebar';

const Permissions = ({ onLogout }) => {
    const [permissions, setPermissions] = useState([]);
    const [studies, setStudies] = useState([]);
    const [loading, setLoading] = useState(true);
    
    // Form state
    const [granteeEmail, setGranteeEmail] = useState('');
    const [accessLevel, setAccessLevel] = useState('VIEW');
    const [selectedItems, setSelectedItems] = useState(['ALL']);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [permsRes, studiesRes] = await Promise.all([
                api.get('permissions/'),
                api.get('blocks/')
            ]);
            setPermissions(permsRes.data);
            setStudies(studiesRes.data);
        } catch (err) {
            console.error("Error fetching data", err);
        } finally {
            setLoading(false);
        }
    };

    const handleShare = async (e) => {
        e.preventDefault();
        if (selectedItems.length === 0) {
            alert("Seleccione al menos un ítem para compartir");
            return;
        }
        try {
            await api.post('permissions/', {
                grantee_email: granteeEmail,
                access_level: accessLevel,
                shared_items: selectedItems
            });
            alert("Acceso compartido exitosamente");
            setGranteeEmail('');
            setSelectedItems(['ALL']);
            fetchData();
        } catch (err) {
            const msg = err.response?.data?.grantee_email || "Error al compartir";
            alert(msg);
        }
    };

    const handleRevoke = async (id) => {
        if (!window.confirm("¿Revocar este permiso?")) return;
        try {
            await api.delete(`permissions/${id}/`);
            fetchData();
        } catch (err) {
            alert("Error al revocar permiso");
        }
    };


    const toggleItem = (item) => {
        if (item === 'ALL') {
            setSelectedItems(selectedItems.includes('ALL') ? [] : ['ALL']);
            return;
        }

        let newSelected = selectedItems.filter(i => i !== 'ALL');
        if (newSelected.includes(item)) {
            newSelected = newSelected.filter(i => i !== item);
        } else {
            newSelected.push(item);
        }
        setSelectedItems(newSelected);
    };

    if (loading) return <div className="p-5 text-center">Cargando...</div>;

    return (
        <div className="d-flex" style={{ minHeight: '100vh' }}>
            {/* Sidebar */}
            <Sidebar active="/permissions" onLogout={onLogout} />

            {/* Main Content */}
            <div className="main-content flex-grow-1 p-5 bg-light overflow-auto">
                <div className="d-flex justify-content-between align-items-center mb-5">
                    <div>
                        <h2 className="fw-bold mb-1">Configuración de Privacidad</h2>
                        <p className="text-muted">Gestiona quién puede ver tu información y qué datos específicos compartes.</p>
                    </div>
                </div>

                <div className="row g-4">
                    <div className="col-lg-5">
                        <div className="card border-0 shadow-sm p-4 h-100 animate-hover">
                            <h5 className="fw-bold mb-4 d-flex align-items-center gap-2">
                                <i className="bi bi-plus-circle text-primary"></i> 
                                Nuevo Permiso
                            </h5>
                            <form onSubmit={handleShare}>
                                <div className="mb-4">
                                    <label className="form-label small fw-bold text-uppercase text-muted">Correo del destinatario</label>
                                    <input 
                                        type="email" 
                                        className="form-control form-control-lg border-0 bg-light" 
                                        placeholder="correo@ejercito.mil.ar" 
                                        value={granteeEmail}
                                        onChange={(e) => setGranteeEmail(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="mb-4">
                                    <label className="form-label small fw-bold text-uppercase text-muted">Nivel de Acceso</label>
                                    <select 
                                        className="form-select form-select-lg border-0 bg-light"
                                        value={accessLevel}
                                        onChange={(e) => setAccessLevel(e.target.value)}
                                    >
                                        <option value="VIEW">Visualización (Lectura)</option>
                                        <option value="MODIFY">Intervención (Médico Auditor)</option>
                                    </select>
                                </div>
                                <div className="mb-4">
                                    <label className="form-label small fw-bold text-uppercase text-muted">¿Qué deseas compartir?</label>
                                    <div className="bg-light p-3 rounded-3 border border-light-subtle" style={{ maxHeight: '250px', overflowY: 'auto' }}>
                                        <div className="form-check mb-3">
                                            <input 
                                                className="form-check-input" 
                                                type="checkbox" 
                                                id="check_all"
                                                checked={selectedItems.includes('ALL')}
                                                onChange={() => toggleItem('ALL')}
                                            />
                                            <label className="form-check-label fw-bold text-primary" htmlFor="check_all">
                                                Compartir Todo
                                            </label>
                                            <div className="small text-muted">Datos personales y todos los estudios</div>
                                        </div>
                                        
                                        <hr className="my-3 opacity-10" />
                                        
                                        <div className="form-check mb-2">
                                            <input 
                                                className="form-check-input" 
                                                type="checkbox" 
                                                id="check_personal"
                                                checked={selectedItems.includes('ALL') || selectedItems.includes('PERSONAL_DATA')}
                                                disabled={selectedItems.includes('ALL')}
                                                onChange={() => toggleItem('PERSONAL_DATA')}
                                            />
                                            <label className="form-check-label fw-medium" htmlFor="check_personal">
                                                Datos Personales
                                            </label>
                                            <div className="small text-muted" style={{fontSize: '0.75rem'}}>DNI, Edad, Grado, Peso, Altura, etc.</div>
                                        </div>

                                        <div className="mt-3 mb-2 small fw-bold text-muted text-uppercase" style={{fontSize: '0.7rem'}}>Estudios Médicos</div>
                                        {studies.length === 0 && <div className="small text-muted italic">No hay estudios cargados</div>}
                                        {studies.map(s => (
                                            <div key={s.id} className="form-check mb-2">
                                                <input 
                                                    className="form-check-input" 
                                                    type="checkbox" 
                                                    id={`study_${s.id}`}
                                                    checked={selectedItems.includes('ALL') || selectedItems.includes(s.id.toString())}
                                                    disabled={selectedItems.includes('ALL')}
                                                    onChange={() => toggleItem(s.id.toString())}
                                                />
                                                <label className="form-check-label small" htmlFor={`study_${s.id}`}>
                                                    {s.title}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <button type="submit" className="btn btn-primary w-100 rounded-pill py-3 fw-bold shadow-sm">
                                    Conceder Acceso
                                </button>
                            </form>
                        </div>
                    </div>

                    <div className="col-lg-7">
                        <div className="card border-0 shadow-sm p-4 h-100">
                            <h5 className="fw-bold mb-4">Usuarios con Acceso</h5>
                            <div className="d-none d-md-block table-responsive">
                                <table className="table table-hover align-middle">
                                    <thead className="table-light">
                                        <tr>
                                            <th className="border-0 bg-transparent text-muted small text-uppercase py-3">Usuario</th>
                                            <th className="border-0 bg-transparent text-muted small text-uppercase py-3">Acceso</th>
                                            <th className="border-0 bg-transparent text-muted small text-uppercase py-3">Contenido</th>
                                            <th className="border-0 bg-transparent text-muted small text-uppercase py-3 text-end">Acción</th>
                                        </tr>
                                    </thead>
                                    <tbody className="border-0">
                                        {permissions.length === 0 && (
                                            <tr>
                                                <td colSpan="4" className="text-center py-5 text-muted">
                                                    No has otorgado permisos aún.
                                                </td>
                                            </tr>
                                        )}
                                        {permissions.map((p) => (
                                            <tr key={p.id}>
                                                <td className="py-3 border-0">
                                                    <div className="d-flex align-items-center">
                                                        <div className="bg-primary-subtle text-primary rounded-circle d-flex align-items-center justify-content-center me-3" style={{width: '32px', height: '32px', fontSize: '0.8rem'}}>
                                                            {p.grantee_details?.username?.[0].toUpperCase()}
                                                        </div>
                                                        <div>
                                                            <div className="fw-medium">{p.grantee_details?.email}</div>
                                                            <div className="small text-muted">{p.grantee_details?.first_name} {p.grantee_details?.last_name}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="py-3 border-0">
                                                    <span className={`badge ${p.access_level === 'MODIFY' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'} rounded-pill px-3`}>
                                                        {p.access_level === 'MODIFY' ? 'Médico' : 'Lector'}
                                                    </span>
                                                </td>
                                                <td className="py-3 border-0">
                                                    <div className="small">
                                                        {p.shared_items.includes('ALL') ? (
                                                            <span className="text-primary fw-bold">Completo</span>
                                                        ) : (
                                                            <div className="d-flex flex-column gap-1">
                                                                {p.shared_items.includes('PERSONAL_DATA') && <span className="badge bg-info text-white text-start text-wrap" style={{width: 'fit-content'}}>Datos Personales</span>}
                                                                {p.shared_items.filter(i => i !== 'PERSONAL_DATA').map(idStr => {
                                                                    const study = studies.find(s => s.id === parseInt(idStr));
                                                                    return study ? (
                                                                        <span key={idStr} className="badge bg-secondary text-start text-wrap" style={{width: 'fit-content', maxWidth: '250px'}} title={study.title}>
                                                                            <i className="bi bi-file-earmark-medical me-1"></i>
                                                                            {study.title}
                                                                        </span>
                                                                    ) : (
                                                                        <span key={idStr} className="badge bg-light text-muted text-start text-wrap" style={{width: 'fit-content'}}>Estudio Eliminado (ID: {idStr})</span>
                                                                    );
                                                                })}
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="py-3 border-0 text-end">
                                                    <button onClick={() => handleRevoke(p.id)} className="btn btn-outline-danger btn-sm rounded-pill px-3">
                                                        Revocar
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Mobile Cards */}
                            <div className="d-block d-md-none">
                                {permissions.length === 0 && (
                                    <div className="text-center py-5 text-muted border rounded-4 bg-light">
                                        No has otorgado permisos aún.
                                    </div>
                                )}
                                {permissions.map((p) => (
                                    <div key={p.id} className="card border mb-3 rounded-4 shadow-sm">
                                        <div className="card-body">
                                            <div className="d-flex align-items-center mb-3">
                                                <div className="bg-primary-subtle text-primary rounded-circle d-flex align-items-center justify-content-center me-3" style={{width: '40px', height: '40px', fontSize: '1rem'}}>
                                                    {p.grantee_details?.username?.[0].toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="fw-bold text-primary">{p.grantee_details?.email}</div>
                                                    <div className="small text-muted">{p.grantee_details?.first_name} {p.grantee_details?.last_name}</div>
                                                </div>
                                            </div>
                                            <div className="mb-3">
                                                <span className="small text-muted d-block mb-1 text-uppercase fw-bold">Nivel de Acceso:</span>
                                                <span className={`badge ${p.access_level === 'MODIFY' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'} rounded-pill px-3 py-2`}>
                                                    {p.access_level === 'MODIFY' ? 'Médico' : 'Lector'}
                                                </span>
                                            </div>
                                            <div className="mb-3">
                                                <span className="small text-muted d-block mb-1 text-uppercase fw-bold">Contenido:</span>
                                                <div className="small">
                                                    {p.shared_items.includes('ALL') ? (
                                                        <span className="text-primary fw-bold">Acceso Completo</span>
                                                    ) : (
                                                        <div className="d-flex flex-column gap-1">
                                                            {p.shared_items.includes('PERSONAL_DATA') && <span className="badge bg-info text-white text-start text-wrap" style={{width: 'fit-content'}}>Datos Personales</span>}
                                                            {p.shared_items.filter(i => i !== 'PERSONAL_DATA').map(idStr => {
                                                                const study = studies.find(s => s.id === parseInt(idStr));
                                                                return study ? (
                                                                    <span key={idStr} className="badge bg-secondary text-start text-wrap" style={{width: 'fit-content', maxWidth: '250px'}} title={study.title}>
                                                                        <i className="bi bi-file-earmark-medical me-1"></i>
                                                                        {study.title}
                                                                    </span>
                                                                ) : (
                                                                    <span key={idStr} className="badge bg-light text-muted text-start text-wrap" style={{width: 'fit-content'}}>Estudio Eliminado (ID: {idStr})</span>
                                                                );
                                                            })}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="border-top pt-3 mt-2">
                                                <button onClick={() => handleRevoke(p.id)} className="btn btn-outline-danger w-100 rounded-pill">
                                                    <i className="bi bi-shield-slash me-2"></i>Revocar Acceso
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Permissions;
