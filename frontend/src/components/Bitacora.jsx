import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { QRCodeSVG } from 'qrcode.react';
import { Scanner } from '@yudiel/react-qr-scanner';

const Bitacora = ({ onLogout }) => {
  const [activeTab, setActiveTab] = useState('mis-buceos');
  const [activities, setActivities] = useState([]);
  const [logs, setLogs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  // Form for instructor activity
  const [actData, setActData] = useState({
    date: new Date().toISOString().split('T')[0],
    location_coords: '',
    location_type: '',
    dive_type: '',
    time_in: '',
    time_out: '',
    max_depth_meters: '',
    duration_minutes: '',
    surface_temp_celsius: '',
    water_temp_celsius: '',
    visibility_meters: '',
    altitude_meters: '',
    atmospheric_conditions: '',
    water_course_conditions: '',
    wind_speed_knots: '',
    safety_diver: '',
    medic: '',
    supervisor: '',
    notes: ''
  });

  const [generatedToken, setGeneratedToken] = useState(null);
  const [scanningRole, setScanningRole] = useState(null); 
  
  // Diver Log Modal Form (Instructor Side)
  const [showLogModal, setShowLogModal] = useState(false);
  const [selectedActivityId, setSelectedActivityId] = useState(null);
  const [logData, setLogData] = useState({
    equipment_type: '', gas_type: 'Aire', suit_type: '', weight_kgs: '',
    tank_type: '', start_pressure_bar: '', end_pressure_bar: '',
    residual_nitrogen_pre: '', residual_nitrogen_post: '',
    decompression_stop: false, decompression_depth_meters: '', decompression_time_minutes: '',
    diver_notes: ''
  });
  const [diveGraphFile, setDiveGraphFile] = useState(null);

  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [newInstructorEmail, setNewInstructorEmail] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [profRes, actRes, logRes] = await Promise.all([
        api.get('profiles/me/'),
        api.get('dive-activities/'),
        api.get('dive-logs/')
      ]);
      setProfile(profRes.data);
      setActivities(actRes.data);
      setLogs(logRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChangeAct = (e) => {
    setActData({ ...actData, [e.target.name]: e.target.value });
  };

  const handleLogChange = (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setLogData({ ...logData, [e.target.name]: value });
  };

  const createActivity = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...actData };
      ['max_depth_meters', 'duration_minutes', 'surface_temp_celsius', 'water_temp_celsius', 'visibility_meters', 'altitude_meters', 'wind_speed_knots', 'safety_diver', 'medic', 'supervisor', 'time_in', 'time_out'].forEach(f => {
        if (payload[f] === '') payload[f] = null;
      });

      await api.post('dive-activities/', payload);
      alert('Actividad creada exitosamente');
      fetchData();
      setActData(prev => ({
        ...prev,
        time_in: '', time_out: '', safety_diver: '', medic: '', supervisor: ''
      }));
    } catch (err) {
      alert('Error creando actividad');
    }
  };

  const handleDeleteAct = async (id) => {
    if (!window.confirm('¿Eliminar esta inmersión?')) return;
    try {
      await api.delete(`/dive-activities/${id}/`);
      fetchData();
    } catch (error) {
      alert('Error eliminando inmersión');
    }
  };

  const closeMenu = () => {
    const toggle = document.getElementById('menu-toggle');
    if (toggle) toggle.checked = false;
  };

  const openLogModal = (activityId) => {
    setSelectedActivityId(activityId);
    setLogData({
      equipment_type: '', gas_type: 'Aire', suit_type: '', weight_kgs: '',
      tank_type: '', start_pressure_bar: '', end_pressure_bar: '',
      residual_nitrogen_pre: '', residual_nitrogen_post: '',
      decompression_stop: false, decompression_depth_meters: '', decompression_time_minutes: '',
      diver_notes: ''
    });
    setDiveGraphFile(null);
    setShowLogModal(true);
  };

  const submitLogAndGenerateQR = async (e) => {
    e.preventDefault();
    try {
      const formData = new FormData();
      formData.append('activity_id', selectedActivityId);
      
      // Append scalar fields
      Object.keys(logData).forEach(key => {
        if (logData[key] !== '' && logData[key] !== null) {
          formData.append(key, logData[key]);
        }
      });
      
      if (diveGraphFile) {
        formData.append('dive_graph', diveGraphFile);
      }

      const res = await api.post('dive-logs/generate/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setGeneratedToken(res.data.token);
      setShowLogModal(false);
    } catch (err) {
      alert('Error cargando los datos del buzo y generando QR');
    }
  };

  const promoteUser = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('superusers/promote/', { email: newAdminEmail });
      alert(res.data.message);
      setNewAdminEmail('');
    } catch (err) {
      alert(err.response?.data?.error || 'Error al promover usuario');
    }
  };

  const promoteInstructor = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('superusers/promote-instructor/', { email: newInstructorEmail });
      alert(res.data.message);
      setNewInstructorEmail('');
    } catch (err) {
      alert(err.response?.data?.error || 'Error al dar permisos de instructor');
    }
  };

  const handleScanSignature = (result) => {
    if (result && result.length > 0 && result[0].rawValue.startsWith('USER_ID:')) {
      const userId = result[0].rawValue.split(':')[1];
      setActData({ ...actData, [scanningRole]: userId });
      setScanningRole(null);
      alert('¡Firma digital capturada con éxito!');
    } else {
      alert('QR Inválido para firma. Asegúrate de escanear el QR Personal del buzo desde su perfil.');
    }
  };

  if (loading && !profile) return <div className="p-5 text-center">Cargando...</div>;

  const isSuperUser = profile?.user?.is_superuser;
  const isInstructor = profile?.is_instructor;
  const myDives = logs.filter(l => l.diver === profile?.user?.id);
  const qrUrl = generatedToken ? `${window.location.origin}/bitacora/scan/${generatedToken}` : '';

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <div className="sidebar p-4 d-flex flex-column">
        <div className="d-flex align-items-center mb-5 ps-2">
          <div className="bg-white rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '35px', height: '35px' }}>
            <i className="bi bi-water text-primary fs-5"></i>
          </div>
          <h4 className="m-0 fw-bold">Anexo Buceo</h4>
        </div>
        
        <nav className="nav flex-column gap-2 flex-grow-1">
          <Link to="/dashboard" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-grid me-3"></i><span>Dashboard</span>
          </Link>
          <Link to="/profile" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-person-circle me-3"></i><span>Mi Perfil</span>
          </Link>
          <Link to="/permissions" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-shield-lock me-3"></i><span>Permisos</span>
          </Link>
          <Link to="/bitacora" className="nav-link active d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-book-fill me-3"></i><span>Bitácora de Buceo</span>
          </Link>
        </nav>

        <div className="mt-auto">
          <button className="btn btn-outline-light w-100 d-flex align-items-center justify-content-center gap-2 py-2 opacity-75 border-0" onClick={onLogout}>
            <i className="bi bi-box-arrow-left"></i><span>Cerrar Sesión</span>
          </button>
        </div>
      </div>

      <div className="flex-grow-1 p-5 bg-light overflow-auto position-relative">
        <h2 className="fw-bold mb-4">Bitácora Digital</h2>
        
        <div className="nav nav-tabs border-0 mb-4 gap-2">
          <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'mis-buceos' ? 'bg-primary text-white' : 'text-muted'}`} onClick={() => setActiveTab('mis-buceos')}>
            Mis Buceos ({myDives.length})
          </button>
          {isInstructor && (
            <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'instructor' ? 'bg-primary text-white' : 'text-muted'}`} onClick={() => setActiveTab('instructor')}>
              Modo Instructor
            </button>
          )}
          {isSuperUser && (
            <button className={`nav-link rounded-pill border-0 px-4 ${activeTab === 'admin' ? 'bg-primary text-white' : 'text-muted'}`} onClick={() => setActiveTab('admin')}>
              Panel Superusuario
            </button>
          )}
        </div>

        {/* Modal QR Scanner */}
        {scanningRole && (
          <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
            <div className="modal-dialog modal-dialog-centered">
              <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
                <div className="bg-primary text-white p-3 d-flex justify-content-between align-items-center">
                  <h6 className="m-0 fw-bold">Escanear QR de Firma</h6>
                  <button type="button" className="btn-close btn-close-white" onClick={() => setScanningRole(null)}></button>
                </div>
                <div className="p-3 text-center">
                  <p className="small text-muted mb-3">Escanea el QR del perfil de la persona que actuó como: <strong>{scanningRole}</strong></p>
                  <Scanner 
                    onScan={handleScanSignature} 
                    onError={(error) => alert(`Error de cámara: Asegúrate de estar usando HTTPS o localhost, y tener permisos habilitados. Detalle: ${error.message || error}`)}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal Carga de Datos del Buzo */}
        {showLogModal && (
          <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1040, overflowY: 'auto' }}>
            <div className="modal-dialog modal-dialog-centered modal-lg">
              <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
                <div className="bg-primary text-white p-4 d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="m-0 fw-bold">Cargar Registro del Buzo</h5>
                    <small className="opacity-75">Completa los datos técnicos del buzo para generar su QR</small>
                  </div>
                  <button type="button" className="btn-close btn-close-white" onClick={() => setShowLogModal(false)}></button>
                </div>
                <div className="p-4 bg-light">
                  <form onSubmit={submitLogAndGenerateQR}>
                    <h6 className="fw-bold mb-3 border-bottom pb-2">Equipamiento y Consumo</h6>
                    <div className="row g-2 mb-4">
                      <div className="col-md-4"><label className="form-label small text-muted">Equipo</label><input type="text" name="equipment_type" className="form-control form-control-sm" value={logData.equipment_type} onChange={handleLogChange} /></div>
                      <div className="col-md-4"><label className="form-label small text-muted">Traje</label><input type="text" name="suit_type" className="form-control form-control-sm" value={logData.suit_type} onChange={handleLogChange} /></div>
                      <div className="col-md-4"><label className="form-label small text-muted">Lastre (Kgs)</label><input type="number" step="0.1" name="weight_kgs" className="form-control form-control-sm" value={logData.weight_kgs} onChange={handleLogChange} /></div>
                      <div className="col-md-4"><label className="form-label small text-muted">Botellón</label><input type="text" name="tank_type" className="form-control form-control-sm" value={logData.tank_type} onChange={handleLogChange} /></div>
                      <div className="col-md-4"><label className="form-label small text-muted">Gas</label><select name="gas_type" className="form-select form-select-sm" value={logData.gas_type} onChange={handleLogChange}><option>Aire</option><option>Nitrox</option><option>Trimix</option></select></div>
                      <div className="col-md-2"><label className="form-label small text-muted">Presión Inicial</label><input type="number" name="start_pressure_bar" className="form-control form-control-sm" value={logData.start_pressure_bar} onChange={handleLogChange} /></div>
                      <div className="col-md-2"><label className="form-label small text-muted">Presión Final</label><input type="number" name="end_pressure_bar" className="form-control form-control-sm" value={logData.end_pressure_bar} onChange={handleLogChange} /></div>
                    </div>

                    <h6 className="fw-bold mb-3 border-bottom pb-2">Descompresión y Nitrógeno</h6>
                    <div className="row g-2 mb-4 align-items-end">
                      <div className="col-md-3"><label className="form-label small text-muted">Nitrógeno PRE</label><input type="text" name="residual_nitrogen_pre" className="form-control form-control-sm" value={logData.residual_nitrogen_pre} onChange={handleLogChange} /></div>
                      <div className="col-md-3"><label className="form-label small text-muted">Nitrógeno POST</label><input type="text" name="residual_nitrogen_post" className="form-control form-control-sm" value={logData.residual_nitrogen_post} onChange={handleLogChange} /></div>
                      <div className="col-md-2"><div className="form-check form-switch mb-1"><input className="form-check-input" type="checkbox" name="decompression_stop" checked={logData.decompression_stop} onChange={handleLogChange} id="decompCheck"/><label className="form-check-label small" htmlFor="decompCheck">Parada Descomp.</label></div></div>
                      {logData.decompression_stop && (
                        <>
                          <div className="col-md-2"><label className="form-label small text-muted">Prof. (m)</label><input type="number" step="0.1" name="decompression_depth_meters" className="form-control form-control-sm" value={logData.decompression_depth_meters} onChange={handleLogChange} /></div>
                          <div className="col-md-2"><label className="form-label small text-muted">Tiempo (min)</label><input type="number" name="decompression_time_minutes" className="form-control form-control-sm" value={logData.decompression_time_minutes} onChange={handleLogChange} /></div>
                        </>
                      )}
                    </div>

                    <h6 className="fw-bold mb-3 border-bottom pb-2">Archivos y Observaciones</h6>
                    <div className="row g-3 mb-4">
                      <div className="col-md-6">
                        <label className="form-label small text-muted">Gráfica de Buceo (PDF o Imagen)</label>
                        <input type="file" className="form-control form-control-sm" accept="image/*,.pdf" onChange={e => setDiveGraphFile(e.target.files[0])} />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label small text-muted">Observaciones Adicionales</label>
                        <textarea name="diver_notes" className="form-control form-control-sm" rows="2" value={logData.diver_notes} onChange={handleLogChange}></textarea>
                      </div>
                    </div>

                    <div className="text-end">
                      <button type="button" className="btn btn-light rounded-pill px-4 me-2" onClick={() => setShowLogModal(false)}>Cancelar</button>
                      <button type="submit" className="btn btn-primary rounded-pill px-5 fw-bold shadow-sm"><i className="bi bi-qr-code me-2"></i>Guardar y Generar QR</button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'mis-buceos' && (
          <div className="card border-0 shadow-sm p-4">
            <h5 className="fw-bold mb-4">Mi Historial de Buceos</h5>
            <div className="row g-4">
              {myDives.filter(l => l.is_completed).map(log => (
                <div className="col-md-6" key={log.id}>
                  <div className="card shadow-sm border-0 p-3 h-100">
                    <div className="d-flex justify-content-between">
                      <h6 className="fw-bold text-primary"><i className="bi bi-geo-alt-fill me-2"></i>{log.activity_details.location_coords}</h6>
                      <span className="text-muted small">{log.activity_details.date}</span>
                    </div>
                    <div className="small text-muted mb-3 pb-2 border-bottom">Escribiente: {log.activity_details.instructor_name}</div>
                    <div className="row g-2 small mt-2">
                      <div className="col-6"><strong>Profundidad:</strong> {log.activity_details.max_depth_meters}m</div>
                      <div className="col-6"><strong>Tiempo:</strong> {log.activity_details.duration_minutes}m</div>
                      <div className="col-6"><strong>Gas:</strong> {log.gas_type}</div>
                      <div className="col-6"><strong>Consumo:</strong> {log.start_pressure_bar} - {log.end_pressure_bar} bar</div>
                    </div>
                  </div>
                </div>
              ))}
              {myDives.filter(l => l.is_completed).length === 0 && <div className="text-muted text-center py-5">No tienes buceos registrados.</div>}
            </div>
          </div>
        )}

        {activeTab === 'instructor' && isInstructor && (
          <div className="row g-4">
            <div className="col-md-7">
              <div className="card border-0 shadow-sm p-4">
                <h5 className="fw-bold mb-4">Crear Actividad de Buceo</h5>
                <form onSubmit={createActivity}>
                  <h6 className="fw-bold small text-primary mb-3">Lugar y Fecha</h6>
                  <div className="row g-2 mb-4">
                    <div className="col-md-4"><label className="form-label small text-muted">Fecha</label><input type="date" name="date" className="form-control form-control-sm" value={actData.date} onChange={handleChangeAct} required /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Lugar / Coord</label><input type="text" name="location_coords" className="form-control form-control-sm" value={actData.location_coords} onChange={handleChangeAct} required /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Tipo de Lugar</label><input type="text" name="location_type" className="form-control form-control-sm" value={actData.location_type} onChange={handleChangeAct} /></div>
                  </div>

                  <h6 className="fw-bold small text-primary mb-3">Parámetros del Buceo</h6>
                  <div className="row g-2 mb-4">
                    <div className="col-md-4"><label className="form-label small text-muted">Tipo Inmersión</label><input type="text" name="dive_type" className="form-control form-control-sm" value={actData.dive_type} onChange={handleChangeAct} /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Profundidad Máx (m)</label><input type="number" step="0.1" name="max_depth_meters" className="form-control form-control-sm" value={actData.max_depth_meters} onChange={handleChangeAct} /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">T. Fondo (min)</label><input type="number" name="duration_minutes" className="form-control form-control-sm" value={actData.duration_minutes} onChange={handleChangeAct} /></div>
                    <div className="col-md-3"><label className="form-label small text-muted">H. Entrada</label><input type="time" name="time_in" className="form-control form-control-sm" value={actData.time_in} onChange={handleChangeAct} /></div>
                    <div className="col-md-3"><label className="form-label small text-muted">H. Salida</label><input type="time" name="time_out" className="form-control form-control-sm" value={actData.time_out} onChange={handleChangeAct} /></div>
                  </div>

                  <h6 className="fw-bold small text-primary mb-3">Condiciones del Entorno</h6>
                  <div className="row g-2 mb-4">
                    <div className="col-md-3"><label className="form-label small text-muted">T° Sup. (°C)</label><input type="number" step="0.1" name="surface_temp_celsius" className="form-control form-control-sm" value={actData.surface_temp_celsius} onChange={handleChangeAct} /></div>
                    <div className="col-md-3"><label className="form-label small text-muted">T° Agua (°C)</label><input type="number" step="0.1" name="water_temp_celsius" className="form-control form-control-sm" value={actData.water_temp_celsius} onChange={handleChangeAct} /></div>
                    <div className="col-md-3"><label className="form-label small text-muted">Visibilidad (m)</label><input type="number" name="visibility_meters" className="form-control form-control-sm" value={actData.visibility_meters} onChange={handleChangeAct} /></div>
                    <div className="col-md-3"><label className="form-label small text-muted">Altura snm (m)</label><input type="number" name="altitude_meters" className="form-control form-control-sm" value={actData.altitude_meters} onChange={handleChangeAct} /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Cond. Atmosf.</label><input type="text" name="atmospheric_conditions" className="form-control form-control-sm" value={actData.atmospheric_conditions} onChange={handleChangeAct} /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Cond. Curso Agua</label><input type="text" name="water_course_conditions" className="form-control form-control-sm" value={actData.water_course_conditions} onChange={handleChangeAct} /></div>
                    <div className="col-md-4"><label className="form-label small text-muted">Viento (Nudos)</label><input type="number" step="0.1" name="wind_speed_knots" className="form-control form-control-sm" value={actData.wind_speed_knots} onChange={handleChangeAct} /></div>
                  </div>

                  <h6 className="fw-bold small text-primary mb-3">Firmas / Personal (Escanear QRs)</h6>
                  <div className="row g-2 mb-4">
                    <div className="col-md-4 text-center">
                      <div className={`p-2 border rounded ${actData.safety_diver ? 'bg-success-subtle border-success' : 'bg-light'}`}>
                        <div className="small fw-bold mb-1">Buzo Seguridad</div>
                        {actData.safety_diver ? <div className="text-success small"><i className="bi bi-check-circle-fill me-1"></i>Firmado</div> : <button type="button" className="btn btn-sm btn-outline-primary rounded-pill py-0 px-2 small" onClick={() => setScanningRole('safety_diver')}><i className="bi bi-qr-code-scan me-1"></i>Escanear</button>}
                      </div>
                    </div>
                    <div className="col-md-4 text-center">
                      <div className={`p-2 border rounded ${actData.medic ? 'bg-success-subtle border-success' : 'bg-light'}`}>
                        <div className="small fw-bold mb-1">Enf. Hiperbárico</div>
                        {actData.medic ? <div className="text-success small"><i className="bi bi-check-circle-fill me-1"></i>Firmado</div> : <button type="button" className="btn btn-sm btn-outline-primary rounded-pill py-0 px-2 small" onClick={() => setScanningRole('medic')}><i className="bi bi-qr-code-scan me-1"></i>Escanear</button>}
                      </div>
                    </div>
                    <div className="col-md-4 text-center">
                      <div className={`p-2 border rounded ${actData.supervisor ? 'bg-success-subtle border-success' : 'bg-light'}`}>
                        <div className="small fw-bold mb-1">Supervisor</div>
                        {actData.supervisor ? <div className="text-success small"><i className="bi bi-check-circle-fill me-1"></i>Firmado</div> : <button type="button" className="btn btn-sm btn-outline-primary rounded-pill py-0 px-2 small" onClick={() => setScanningRole('supervisor')}><i className="bi bi-qr-code-scan me-1"></i>Escanear</button>}
                      </div>
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary w-100 rounded-pill py-2 fw-bold shadow-sm">Crear Actividad Guardando Configuración</button>
                </form>
              </div>
            </div>

            <div className="col-md-5">
              <div className="card border-0 shadow-sm p-4 mb-4">
                <h5 className="fw-bold mb-4">Añadir Buzos y Generar QR</h5>
                {activities.length === 0 ? <p className="text-muted small">No has creado actividades aún.</p> : (
                  <div className="list-group list-group-flush">
                    {activities.map(act => (
                      <div key={act.id} className="list-group-item d-flex justify-content-between align-items-center py-3 px-0 border-bottom border-light">
                        <div>
                          <div className="fw-bold text-dark">{act.location_coords}</div>
                          <div className="small text-muted">{act.date} | {act.max_depth_meters}m</div>
                        </div>
                        <button className="btn btn-outline-primary btn-sm rounded-pill px-3 fw-bold" onClick={() => openLogModal(act.id)}>
                          <i className="bi bi-person-plus-fill me-2"></i>Agregar Buzo
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {generatedToken && (
                <div className="card border-0 shadow-sm p-4 bg-primary-subtle text-center">
                  <h5 className="fw-bold text-primary mb-3">QR de Firma Generado</h5>
                  <p className="small text-muted mb-4">Pídele al buzo que escanee este código para revisar sus datos y confirmar su identidad. Este QR es de único uso.</p>
                  <div className="bg-white p-3 d-inline-block rounded shadow-sm mx-auto mb-3">
                    <QRCodeSVG value={qrUrl} size={200} />
                  </div>
                  <button className="btn btn-primary btn-sm mt-2 rounded-pill px-5" onClick={() => setGeneratedToken(null)}>Ocultar</button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'admin' && isSuperUser && (
          <div className="row g-4">
            <div className="col-md-6">
              <div className="card border-0 shadow-sm p-4 mb-4">
                <h5 className="fw-bold mb-3">Dar Permisos de Instructor</h5>
                <form onSubmit={promoteInstructor} className="d-flex gap-2">
                  <input type="email" className="form-control rounded-pill" placeholder="Email del usuario" value={newInstructorEmail} onChange={e=>setNewInstructorEmail(e.target.value)} required />
                  <button type="submit" className="btn btn-primary rounded-pill px-4">Otorgar</button>
                </form>
              </div>
            </div>
            
            <div className="col-md-6">
              <div className="card border-0 shadow-sm p-4 mb-4">
                <h5 className="fw-bold mb-3 text-danger">Dar Permisos de Superusuario</h5>
                <form onSubmit={promoteUser} className="d-flex gap-2">
                  <input type="email" className="form-control rounded-pill" placeholder="Email del usuario" value={newAdminEmail} onChange={e=>setNewAdminEmail(e.target.value)} required />
                  <button type="submit" className="btn btn-danger rounded-pill px-4">Promover</button>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Bitacora;
