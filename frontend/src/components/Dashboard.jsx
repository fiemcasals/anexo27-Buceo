import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const STUDY_OPTIONS = [
  "Electrocardiograma de esfuerzo. (solo para mayores de 40 años).",
  "Ecocardiograma con informe (Sin Excepción).",
  "Electroencefalograma.",
  "Radiografía de tórax, frente y perfil.",
  "Radiografía de senos frontales y paranasales.",
  "Hemograma, eritrosedimentación, urea, glucosa, orina, CHAGAS (máx 30 días).",
  "Ficha de control odontológico (actualizada).",
  "Anexo 27 ORIGINAL firmado por médico militar y Jefe de Elemento (máx 30 días)."
];

const Dashboard = ({ onLogout }) => {
  const [profile, setProfile] = useState(null);
  const [studies, setStudies] = useState([]);
  const [sharedProfiles, setSharedProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('mine'); // 'mine' or 'shared'
  const [expandedOwners, setExpandedOwners] = useState({});
  
  // Review Modal State
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [selectedStudy, setSelectedStudy] = useState(null);
  const [reviewComment, setReviewComment] = useState('');
  const [reviewStatus, setReviewStatus] = useState('APPROVED');

  // Upload Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDate, setUploadDate] = useState(new Date().toISOString().split('T')[0]);

  // View Comment Modal State
  const [showViewCommentModal, setShowViewCommentModal] = useState(false);
  const [viewedComment, setViewedComment] = useState(null);

  const openViewCommentModal = (comment) => {
    setViewedComment(comment);
    setShowViewCommentModal(true);
  };

  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [profileRes, studiesRes, allProfilesRes] = await Promise.all([
        api.get('profiles/me/'),
        api.get('blocks/'),
        api.get('profiles/')
      ]);
      setProfile(profileRes.data);
      setStudies(studiesRes.data);
      setSharedProfiles(allProfilesRes.data.filter(p => p.user.id !== profileRes.data.user.id));
    } catch (err) {
      console.error("Error fetching data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStudy = async (id) => {
    if (!window.confirm("¿Seguro que desea eliminar este estudio?")) return;
    try {
      await api.delete(`blocks/${id}/`);
      setStudies(studies.filter(s => s.id !== id));
    } catch (err) {
      alert("Error al eliminar el estudio");
    }
  };

  const submitUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile || !uploadTitle || !uploadDate) {
      alert("Por favor completa todos los campos y selecciona un archivo.");
      return;
    }

    const formData = new FormData();
    formData.append('pdf_attachment', uploadFile);
    formData.append('title', uploadTitle);
    formData.append('study_date', uploadDate);

    try {
      setLoading(true);
      await api.post('blocks/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadTitle('');
      fetchData();
    } catch (err) {
      alert("Error al subir archivo");
      setLoading(false);
    }
  };

  const handleGenerateAnexo = async () => {
    try {
      const response = await api.get(`anexo27/${profile.user.id}/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `anexo_27_${profile.user.username}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Error al generar PDF");
    }
  };

  const openReviewModal = (study) => {
    setSelectedStudy(study);
    setReviewComment('');
    setReviewStatus('APPROVED');
    setShowReviewModal(true);
  };

  const handleSaveReview = async () => {
    try {
      await api.post('comments/', {
        block: selectedStudy.id,
        content: reviewComment,
        status: reviewStatus
      });
      alert("Comentario guardado");
      setShowReviewModal(false);
      fetchData();
    } catch (err) {
      alert("Error al guardar revisión");
    }
  };

  if (loading && !profile) return <div className="p-5 text-center">Cargando...</div>;

  const myStudies = studies.filter(s => s.user === profile?.user?.id);
  const sharedWithMe = studies.filter(s => s.user !== profile?.user?.id);

  // Group shared studies by owner
  const groupedShared = {};
  
  // First, initialize groups from shared profiles
  sharedProfiles.forEach(p => {
    groupedShared[p.user.id] = {
      ownerName: p.first_name ? `${p.first_name} ${p.last_name}`.trim() : p.user.username,
      profileData: p,
      studies: []
    };
  });

  // Then add studies
  sharedWithMe.forEach(study => {
    const ownerId = study.user;
    if (!groupedShared[ownerId]) {
      groupedShared[ownerId] = {
        ownerName: study.user_details ? (study.user_details.first_name ? `${study.user_details.first_name} ${study.user_details.last_name}`.trim() : study.user_details.username) : `Usuario ${ownerId}`,
        profileData: null,
        studies: []
      };
    }
    groupedShared[ownerId].studies.push(study);
  });

  const toggleOwner = (ownerId) => {
    setExpandedOwners(prev => ({ ...prev, [ownerId]: !prev[ownerId] }));
  };

  const getMediaUrl = (url) => {
    if (!url) return '#';
    if (url.startsWith('http')) {
      try {
        return new URL(url).pathname;
      } catch (e) {
        return url;
      }
    }
    return url;
  };

  const closeMenu = () => {
    const toggle = document.getElementById('menu-toggle');
    if (toggle) toggle.checked = false;
  };

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <div className="sidebar p-4 d-flex flex-column">
        <div className="d-flex align-items-center mb-5 ps-2">
          <div className="bg-white rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '35px', height: '35px' }}>
            <i className="bi bi-water text-primary fs-5"></i>
          </div>
          <h4 className="m-0 fw-bold">Anexo Buceo</h4>
        </div>
        
        <nav className="nav flex-column gap-2 flex-grow-1">
          <Link to="/dashboard" className="nav-link active d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-grid-fill me-3"></i>
            <span>Dashboard</span>
          </Link>
          <Link to="/profile" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-person-circle me-3"></i>
            <span>Mi Perfil</span>
          </Link>
          <Link to="/permissions" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-shield-lock me-3"></i>
            <span>Permisos</span>
          </Link>
          <Link to="/bitacora" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-book me-3"></i>
            <span>Bitácora de Buceo</span>
          </Link>
        </nav>

        <div className="mt-auto">
          <button className="btn btn-outline-light w-100 d-flex align-items-center justify-content-center gap-2 py-2 opacity-75 border-0" 
                  onClick={onLogout}>
            <i className="bi bi-box-arrow-left"></i>
            <span>Cerrar Sesión</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow-1 p-5 bg-light overflow-auto">
        <div className="d-flex justify-content-between align-items-center mb-5">
          <div>
            <h2 className="fw-bold mb-1">¡Hola, {profile?.user?.first_name || profile?.user?.username}!</h2>
            <p className="text-muted">Bienvenido al panel central de estudios médicos.</p>
          </div>
          <span title="No disponible, implementación futura" style={{ cursor: 'not-allowed' }}>
            <button className="btn btn-secondary d-flex align-items-center gap-2" style={{ pointerEvents: 'none', opacity: 0.6 }} disabled>
              <i className="bi bi-file-pdf"></i>
              Generar Anexo 27
            </button>
          </span>
        </div>

        {/* Tab Navigation */}
        <div className="nav nav-tabs border-0 mb-4 gap-2">
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'mine' ? 'bg-primary text-white' : 'text-muted'}`} 
                  onClick={() => setActiveTab('mine')}>
            Mis Estudios ({myStudies.length})
          </button>
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'shared' ? 'bg-primary text-white' : 'text-muted'}`} 
                  onClick={() => setActiveTab('shared')}>
            Compartidos conmigo ({sharedWithMe.length})
          </button>
        </div>

        {activeTab === 'mine' ? (
          <div className="row g-4">
            <div className="col-md-8">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-4">Mis Últimos Estudios</h5>
                {/* Desktop Table */}
                <div className="d-none d-md-block table-responsive">
                  <table className="table table-hover align-middle">
                    <thead>
                      <tr>
                        <th className="border-0 text-muted small text-uppercase py-3">Estudio</th>
                        <th className="border-0 text-muted small text-uppercase py-3">Fecha</th>
                        <th className="border-0 text-muted small text-uppercase py-3">Estado</th>
                        <th className="border-0 text-muted small text-uppercase py-3 text-end">Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {myStudies.map((s) => (
                        <tr key={s.id}>
                          <td className="py-3 border-0 fw-medium">{s.title}</td>
                          <td className="py-3 border-0 text-muted">{s.study_date}</td>
                          <td className="py-3 border-0">
                            {s.comments.length > 0 ? (
                              <div>
                                <span className={`badge ${s.comments[s.comments.length-1].status === 'REJECTED' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'} rounded-pill mb-1`}>
                                  {s.comments[s.comments.length-1].status === 'REJECTED' ? 'Rechazado' : 'Visto Bueno'}
                                </span>
                                {s.comments[s.comments.length-1].content && (
                                  <div className="mt-2">
                                    <button 
                                      className="btn btn-sm btn-outline-secondary rounded-pill" 
                                      style={{ fontSize: '0.75rem' }}
                                      onClick={() => openViewCommentModal(s.comments[s.comments.length-1])}
                                    >
                                      <i className="bi bi-chat-text me-1"></i>
                                      Ver dictamen
                                    </button>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="badge bg-light text-secondary rounded-pill">Pendiente</span>
                            )}
                          </td>
                          <td className="py-3 border-0 text-end d-flex gap-2 justify-content-end">
                            <a href={getMediaUrl(s.pdf_attachment)} target="_blank" rel="noreferrer" className="btn btn-sm btn-outline-primary border-0">
                              <i className="bi bi-eye"></i>
                            </a>
                            <button className="btn btn-sm btn-outline-danger border-0" onClick={() => handleDeleteStudy(s.id)}>
                              <i className="bi bi-trash"></i>
                            </button>
                          </td>
                        </tr>
                      ))}
                      {myStudies.length === 0 && <tr><td colSpan="4" className="text-center py-4 text-muted">No has cargado estudios aún.</td></tr>}
                    </tbody>
                  </table>
                </div>

                {/* Mobile Cards */}
                <div className="d-block d-md-none">
                  {myStudies.map((s) => (
                    <div key={s.id} className="card border mb-3 rounded-4 shadow-sm">
                      <div className="card-body">
                        <div className="d-flex justify-content-between align-items-center mb-3">
                          <h6 className="fw-bold mb-0 text-primary">{s.title}</h6>
                          <span className="text-muted small"><i className="bi bi-calendar3 me-1"></i>{s.study_date}</span>
                        </div>
                        <div className="mb-3">
                            <span className="small text-muted d-block mb-1 text-uppercase fw-bold">Estado del Dictamen:</span>
                            {s.comments.length > 0 ? (
                              <div>
                                <span className={`badge ${s.comments[s.comments.length-1].status === 'REJECTED' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'} rounded-pill mb-2 px-3 py-2`}>
                                  {s.comments[s.comments.length-1].status === 'REJECTED' ? 'Rechazado' : 'Visto Bueno'}
                                </span>
                                {s.comments[s.comments.length-1].content && (
                                  <div>
                                    <button 
                                      className="btn btn-sm btn-outline-secondary rounded-pill w-100" 
                                      style={{ fontSize: '0.8rem' }}
                                      onClick={() => openViewCommentModal(s.comments[s.comments.length-1])}
                                    >
                                      <i className="bi bi-chat-text me-2"></i>
                                      Ver Mensaje del Auditor
                                    </button>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="badge bg-light text-secondary border rounded-pill px-3 py-2">Pendiente de Revisión</span>
                            )}
                        </div>
                        <div className="d-flex gap-2 border-top pt-3 mt-2">
                          <a href={getMediaUrl(s.pdf_attachment)} target="_blank" rel="noreferrer" className="btn btn-sm btn-outline-primary w-50 rounded-pill">
                            <i className="bi bi-eye me-2"></i>Ver
                          </a>
                          <button className="btn btn-sm btn-outline-danger w-50 rounded-pill" onClick={() => handleDeleteStudy(s.id)}>
                            <i className="bi bi-trash me-2"></i>Eliminar
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {myStudies.length === 0 && <div className="text-center py-4 text-muted border rounded-4 bg-light">No has cargado estudios aún.</div>}
                </div>
              </div>
            </div>

            <div className="col-md-4">
              <div className="card border-0 shadow-sm p-4 h-100 bg-primary text-white animate-hover">
                <h5 className="fw-bold mb-3">Subir Nuevo Estudio</h5>
                <p className="small opacity-75 mb-4">Carga tus resultados médicos en formato PDF o imagen para centralizar tu historial.</p>
                <button 
                  className="btn btn-light w-100 rounded-pill py-2 fw-bold text-primary"
                  onClick={() => setShowUploadModal(true)}
                >
                  <i className="bi bi-cloud-arrow-up me-2"></i>
                  Seleccionar Archivo
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card border-0 shadow-sm p-4">
            <h5 className="fw-bold mb-4 text-primary">Estudios Compartidos por Colegas</h5>
            
            {Object.keys(groupedShared).length === 0 ? (
              <div className="text-center py-5 text-muted">No hay estudios compartidos contigo.</div>
            ) : (
              <div className="d-flex flex-column gap-3">
                {Object.entries(groupedShared).map(([ownerId, group]) => (
                  <div key={ownerId} className="border rounded-3 overflow-hidden shadow-sm">
                    <div 
                      className="bg-light p-3 d-flex justify-content-between align-items-center"
                      onClick={() => toggleOwner(ownerId)}
                      style={{ cursor: 'pointer' }}
                    >
                      <h6 className="m-0 fw-bold d-flex align-items-center text-primary">
                        <i className={`bi bi-chevron-${expandedOwners[ownerId] ? 'down' : 'right'} me-2`}></i>
                        <i className="bi bi-person-circle me-2 fs-5"></i>
                        {group.ownerName} 
                        {group.profileData && <span className="badge bg-info rounded-pill ms-3 text-white">Datos Personales</span>}
                        {group.studies.length === 1 ? (
                          <span className="badge bg-secondary rounded-pill ms-2 text-truncate" style={{ maxWidth: '250px' }} title={group.studies[0].title}>
                            {group.studies[0].title}
                          </span>
                        ) : (
                          <span className="badge bg-secondary rounded-pill ms-2">{group.studies.length} estudio{group.studies.length !== 1 ? 's' : ''}</span>
                        )}
                        <small className="ms-2 text-muted fw-normal" style={{ fontSize: '0.75rem' }}>(Clic para ver)</small>
                      </h6>
                    </div>
                    
                    {expandedOwners[ownerId] && (
                      <div className="p-4 bg-white border-top">
                        {group.profileData && (
                          <div className="card shadow-sm border-0 mb-4 bg-light">
                            <div className="card-body">
                              <h6 className="fw-bold mb-3"><i className="bi bi-person-vcard me-2 text-primary"></i>Datos Personales</h6>
                              <div className="row g-3">
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">DNI</span>
                                  <span className="fw-medium">{group.profileData.dni || '-'}</span>
                                </div>
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">Edad</span>
                                  <span className="fw-medium">{group.profileData.age ? group.profileData.age + ' años' : '-'}</span>
                                </div>
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">Teléfono</span>
                                  <span className="fw-medium">{group.profileData.phone || '-'}</span>
                                </div>
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">Grado</span>
                                  <span className="fw-medium">{group.profileData.rank || '-'}</span>
                                </div>
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">Destino</span>
                                  <span className="fw-medium">{group.profileData.destination || '-'}</span>
                                </div>
                                <div className="col-md-4">
                                  <span className="small text-muted d-block">Físico</span>
                                  <span className="fw-medium">{group.profileData.weight ? group.profileData.weight + ' kg' : '-'} / {group.profileData.height ? group.profileData.height + ' cm' : '-'}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                        <div className="row g-4">
                          {group.studies.length > 0 ? group.studies.map(s => (
                            <div className="col-md-6" key={s.id}>
                              <div className="card shadow-sm border-0 p-3 animate-hover h-100">
                                <div className="d-flex justify-content-between align-items-start mb-3">
                                  <div>
                                    <h6 className="fw-bold mb-1">{s.title}</h6>
                                    <span className="small text-muted">{s.study_date}</span>
                                  </div>
                                  <a href={getMediaUrl(s.pdf_attachment)} target="_blank" rel="noreferrer" className="btn btn-sm btn-light">
                                    Ver Documento
                                  </a>
                                </div>
                                <div className="bg-light p-2 rounded mb-3 small">
                                  {s.description || "Sin descripción"}
                                </div>
                                {s.comments.map(c => (
                                  <div key={c.id} className="small mb-2 p-2 rounded bg-white border-start border-4 border-primary shadow-xs">
                                    <div className="d-flex justify-content-between">
                                      <span className="fw-bold">{c.doctor_name}</span>
                                      <span className={`badge ${c.status === 'REJECTED' ? 'bg-danger-subtle text-danger' : 'bg-success-subtle text-success'}`}>
                                        {c.status === 'REJECTED' ? 'Rechazado' : 'Aprobado'}
                                      </span>
                                    </div>
                                    <p className="mb-0 text-muted">{c.content}</p>
                                  </div>
                                ))}
                                <div className="mt-auto pt-2">
                                  {s.access_level === 'MODIFY' ? (
                                    <button className="btn btn-primary btn-sm rounded-pill mt-2 w-100 text-start" onClick={() => openReviewModal(s)}>
                                      <i className="bi bi-chat-left-dots me-2"></i>
                                      Revisar Auditoria
                                    </button>
                                  ) : (
                                    <div className="text-center mt-2 small text-muted border rounded-pill py-1 bg-light">
                                      <i className="bi bi-eye me-2"></i>Solo Lectura
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )) : (
                            <div className="col-12 text-center text-muted py-3">Este usuario no ha compartido estudios médicos.</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Review Modal */}
      {showReviewModal && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-4 p-4">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">Auditando: {selectedStudy?.title}</h5>
                <button type="button" className="btn-close" onClick={() => setShowReviewModal(false)}></button>
              </div>
              <div className="modal-body py-4">
                <div className="mb-4">
                  <label className="form-label small text-muted text-uppercase fw-bold">Dictamen del Auditor</label>
                  <div className="d-flex gap-2">
                    <button 
                      className={`btn flex-grow-1 rounded-pill py-2 ${reviewStatus === 'APPROVED' ? 'btn-success shadow-sm' : 'btn-outline-success border-0'}`}
                      onClick={() => setReviewStatus('APPROVED')}
                    >
                      <i className="bi bi-check-circle me-2"></i>
                      Visto Bueno
                    </button>
                    <button 
                      className={`btn flex-grow-1 rounded-pill py-2 ${reviewStatus === 'REJECTED' ? 'btn-danger shadow-sm' : 'btn-outline-danger border-0'}`}
                      onClick={() => setReviewStatus('REJECTED')}
                    >
                      <i className="bi bi-exclamation-triangle me-2"></i>
                      Rechazado
                    </button>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted text-uppercase fw-bold">Observaciones / Comentarios</label>
                  <textarea 
                    className="form-control border-0 bg-light" 
                    rows="4" 
                    placeholder="Escriba su observación técnica aquí..."
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0 pt-0">
                <button type="button" className="btn btn-light rounded-pill px-4" onClick={() => setShowReviewModal(false)}>Cancelar</button>
                <button type="button" className="btn btn-primary rounded-pill px-5" onClick={handleSaveReview}>Guardar Dictamen</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-4 p-4">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">Subir Nuevo Estudio</h5>
                <button type="button" className="btn-close" onClick={() => {setShowUploadModal(false); setUploadFile(null); setUploadTitle('');}}></button>
              </div>
              <form onSubmit={submitUpload}>
                <div className="modal-body py-4">
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-muted text-uppercase">Tipo de Estudio</label>
                    <select 
                      className="form-select border-0 bg-light" 
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      required
                    >
                      <option value="" disabled>Seleccione una opción...</option>
                      {STUDY_OPTIONS.map((opt, idx) => (
                        <option key={idx} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-muted text-uppercase">Fecha del Estudio</label>
                    <input 
                      type="date" 
                      className="form-control border-0 bg-light" 
                      value={uploadDate}
                      onChange={(e) => setUploadDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-muted text-uppercase">Archivo (PDF o Imagen)</label>
                    <input 
                      type="file" 
                      className="form-control border-0 bg-light" 
                      onChange={(e) => setUploadFile(e.target.files[0])}
                      accept="image/*,application/pdf"
                      capture="environment"
                      required
                    />
                  </div>
                </div>
                <div className="modal-footer border-0 pt-0">
                  <button type="button" className="btn btn-light rounded-pill px-4" onClick={() => {setShowUploadModal(false); setUploadFile(null); setUploadTitle('');}}>Cancelar</button>
                  <button type="submit" className="btn btn-primary rounded-pill px-5">Subir Estudio</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* View Comment Modal */}
      {showViewCommentModal && viewedComment && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-4 p-4">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">Detalle del Dictamen</h5>
                <button type="button" className="btn-close" onClick={() => setShowViewCommentModal(false)}></button>
              </div>
              <div className="modal-body py-4">
                <div className="mb-4 d-flex justify-content-between align-items-center bg-light p-3 rounded-3">
                  <span className="small text-muted text-uppercase fw-bold">Estado de Auditoría</span>
                  <span className={`badge ${viewedComment.status === 'REJECTED' ? 'bg-danger' : 'bg-success'} rounded-pill px-3 py-2`}>
                    {viewedComment.status === 'REJECTED' ? 'Rechazado' : 'Visto Bueno'}
                  </span>
                </div>
                <div className="mb-4">
                  <span className="small text-muted text-uppercase fw-bold d-block mb-2">Auditor Médico</span>
                  <div className="fw-medium d-flex align-items-center">
                    <i className="bi bi-person-badge text-primary me-2 fs-5"></i>
                    Dr/a. {viewedComment.doctor_name}
                  </div>
                </div>
                <div className="mb-2">
                  <span className="small text-muted text-uppercase fw-bold d-block mb-2">Observaciones</span>
                  <div className="bg-light p-4 rounded-3 text-dark border-start border-4 border-primary" style={{ whiteSpace: 'pre-wrap' }}>
                    {viewedComment.content}
                  </div>
                </div>
              </div>
              <div className="modal-footer border-0 pt-0">
                <button type="button" className="btn btn-primary rounded-pill px-5 w-100" onClick={() => setShowViewCommentModal(false)}>Cerrar</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Simple Link component for Navbar substitute if needed
const Link = ({ to, children, className }) => {
  const navigate = useNavigate();
  return (
    <a 
      href={to} 
      className={className} 
      onClick={(e) => {
        e.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
};

export default Dashboard;
