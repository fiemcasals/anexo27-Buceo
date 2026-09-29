import React, { useState, useEffect } from 'react';
import api from '../api';
import Sidebar from './Sidebar';
import { QRCodeSVG } from 'qrcode.react';

const PROFESSION_LABELS = { MEDICO: 'Médico', ENFERMERO: 'Enfermero' };

const Profile = ({ onLogout }) => {
  const [profile, setProfile] = useState({
    first_name: '',
    last_name: '',
    dni: '',
    age: '',
    phone: '',
    rank: '',
    destination: '',
    weight: '',
    height: '',
    profession: '',
    specialty: '',
    profile_data: {}
  });
  const [specialties, setSpecialties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showQRModal, setShowQRModal] = useState(false);

  useEffect(() => {
    fetchProfile();
    api.get('specialties/')
      .then(res => setSpecialties(res.data))
      .catch(err => console.error("Error fetching specialties", err));
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('profiles/me/');
      // Ensure we don't have nulls where we expect strings for inputs
      setProfile({
        ...res.data,
        first_name: res.data.first_name || '',
        last_name: res.data.last_name || '',
        dni: res.data.dni || '',
        age: res.data.age || '',
        phone: res.data.phone || '',
        rank: res.data.rank || '',
        destination: res.data.destination || '',
        weight: res.data.weight || '',
        height: res.data.height || '',
        profession: res.data.profession || '',
        specialty: res.data.specialty || '',
      });
    } catch (err) {
      console.error("Error fetching profile", err);
    } finally {
      setLoading(false);
    }
  };


  const handleChange = (e) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  const handleSave = async (e) => {
    e.preventDefault();
    
    // Clean data: convert empty strings to null for numeric fields
    const cleanedProfile = { ...profile };
    ['age', 'weight', 'height', 'specialty'].forEach(field => {
      if (cleanedProfile[field] === '') {
        cleanedProfile[field] = null;
      }
    });

    try {
      await api.put(`profiles/${profile.id}/`, cleanedProfile);
      alert('Perfil guardado exitosamente');
      fetchProfile(); // Refresh to get clean data back
    } catch (err) {
      console.error("Error saving profile", err.response?.data);
      alert('Error al guardar el perfil. Revise los datos ingresados.');
    }
  };

  // El QR se lee con cualquier cámara: la primera línea la usa el sistema para
  // identificar a la persona, el resto es texto legible con sus datos de perfil.
  const qrValue = () => {
    const lines = [`USER_ID:${profile.user.id}`];
    const add = (label, value, unit = '') => {
      if (value !== '' && value !== null && value !== undefined) lines.push(`${label}: ${value}${unit}`);
    };

    const fullName = `${profile.first_name} ${profile.last_name}`.trim();
    if (fullName) lines.push(fullName);
    add('DNI', profile.dni);
    add('Edad', profile.age, ' años');
    add('Grado', profile.rank);
    add('Destino', profile.destination);
    add('Teléfono', profile.phone);
    add('Peso', profile.weight, ' kg');
    add('Altura', profile.height, ' cm');
    if (profile.profession) lines.push(PROFESSION_LABELS[profile.profession] || profile.profession);
    const specialty = specialties.find(x => String(x.id) === String(profile.specialty));
    if (specialty) add('Especialidad', specialty.name);

    return lines.join('\n');
  };

  if (loading) return <div className="p-5 text-center">Cargando...</div>;

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sidebar active="/profile" onLogout={onLogout} isSuperUser={profile?.user?.is_superuser} />

      <div className="flex-grow-1 p-5 bg-light overflow-auto">
        <div className="d-flex justify-content-between align-items-center mb-5">
          <div>
            <h2 className="fw-bold mb-1">Configuración del Perfil</h2>
            <p className="text-muted">Asegúrate de que tus datos personales estén actualizados.</p>
          </div>
          <div className="text-center" style={{ cursor: 'pointer' }} onClick={() => setShowQRModal(true)} title="Ampliar QR">
            <span className="small fw-bold text-muted d-block mb-2">Tu QR Personal</span>
            <div className="bg-white p-2 rounded shadow-sm d-inline-block animate-hover border">
              {profile.user?.id ? (
                <QRCodeSVG value={qrValue()} size={80} />
              ) : (
                <div style={{width: 80, height: 80}} className="bg-light d-flex align-items-center justify-content-center small text-muted">No disp.</div>
              )}
            </div>
          </div>
        </div>

        {/* Fullscreen QR Modal */}
        {showQRModal && profile.user?.id && (
          <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1050 }} onClick={() => setShowQRModal(false)}>
            <div className="modal-dialog modal-dialog-centered modal-lg d-flex justify-content-center">
              <div className="bg-white p-5 rounded-4 shadow-lg text-center" onClick={(e) => e.stopPropagation()}>
                <h4 className="fw-bold mb-4">Tu Firma Digital</h4>
                <QRCodeSVG value={qrValue()} size={300} level="M" />
                <p className="text-muted mt-4 mb-2">Muestra este código al instructor para firmar digitalmente.</p>
                <p className="small text-muted mb-4">Contiene tus datos de perfil: al escanearlo se leen tu nombre, DNI, grado, destino y medidas. Si algún dato falta, completalo en el formulario y guardá.</p>
                <button className="btn btn-outline-secondary rounded-pill px-5" onClick={() => setShowQRModal(false)}>Cerrar</button>
              </div>
            </div>
          </div>
        )}

        <div className="card shadow-sm border-0 p-4 profile-bg animate-hover">
          <form onSubmit={handleSave}>
            <div className="row g-4">
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Nombre</label>
                <input type="text" name="first_name" className="form-control form-control-lg border-0 bg-light" value={profile.first_name} onChange={handleChange} placeholder="Ingrese su nombre" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Apellido</label>
                <input type="text" name="last_name" className="form-control form-control-lg border-0 bg-light" value={profile.last_name} onChange={handleChange} placeholder="Ingrese su apellido" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">DNI</label>
                <input type="text" name="dni" className="form-control form-control-lg border-0 bg-light" value={profile.dni} onChange={handleChange} placeholder="Ingrese su DNI" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Edad</label>
                <input type="number" name="age" className="form-control form-control-lg border-0 bg-light" value={profile.age} onChange={handleChange} placeholder="25" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Teléfono</label>
                <input type="text" name="phone" className="form-control form-control-lg border-0 bg-light" value={profile.phone} onChange={handleChange} placeholder="+54 9..." />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Grado</label>
                <input type="text" name="rank" className="form-control form-control-lg border-0 bg-light" value={profile.rank} onChange={handleChange} placeholder="Grado militar/civil" />
              </div>
              <div className="col-md-12">
                <label className="form-label fw-medium text-muted small">Destino</label>
                <input type="text" name="destination" className="form-control form-control-lg border-0 bg-light" value={profile.destination} onChange={handleChange} placeholder="Base de operaciones / Destino actual" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">¿Sos médico o enfermero?</label>
                <select name="profession" className="form-select form-select-lg border-0 bg-light" value={profile.profession} onChange={handleChange}>
                  <option value="">No corresponde</option>
                  <option value="MEDICO">Médico</option>
                  <option value="ENFERMERO">Enfermero</option>
                </select>
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Especialidad</label>
                <select name="specialty" className="form-select form-select-lg border-0 bg-light" value={profile.specialty} onChange={handleChange}>
                  <option value="">Sin especialidad</option>
                  {specialties.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                <div className="form-text">Si cargás una especialidad, verás la pestaña "Compartidos conmigo" en el Dashboard.</div>
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Peso (kg)</label>
                <input type="number" name="weight" className="form-control form-control-lg border-0 bg-light" value={profile.weight} onChange={handleChange} placeholder="75" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Altura (cm)</label>
                <input type="number" name="height" className="form-control form-control-lg border-0 bg-light" value={profile.height} onChange={handleChange} placeholder="175" />
              </div>
            </div>

            <div className="mt-5 d-grid gap-2 d-md-flex justify-content-md-start">
              <button type="submit" className="btn btn-primary px-5 py-2 shadow-sm rounded-pill">
                Guardar Cambios
              </button>
              <button type="button" className="btn btn-outline-secondary px-5 py-2 rounded-pill border-0" onClick={fetchProfile}>
                Descartar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Profile;
