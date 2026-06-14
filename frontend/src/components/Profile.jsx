import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { QRCodeSVG } from 'qrcode.react';

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
    profile_data: {}
  });
  const [loading, setLoading] = useState(true);
  const [showQRModal, setShowQRModal] = useState(false);

  useEffect(() => {
    fetchProfile();
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
    ['age', 'weight', 'height'].forEach(field => {
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

  if (loading) return <div className="p-5 text-center">Cargando...</div>;

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
          <Link to="/dashboard" className="nav-link d-flex align-items-center">
            <i className="bi bi-grid me-3"></i>
            <span>Dashboard</span>
          </Link>
          <Link to="/profile" className="nav-link active d-flex align-items-center">
            <i className="bi bi-person-circle-fill me-3"></i>
            <span>Mi Perfil</span>
          </Link>
          <Link to="/permissions" className="nav-link d-flex align-items-center">
            <i className="bi bi-shield-lock me-3"></i>
            <span>Permisos</span>
          </Link>
          <Link to="/bitacora" className="nav-link d-flex align-items-center">
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
                <QRCodeSVG value={`USER_ID:${profile.user.id}`} size={80} />
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
                <QRCodeSVG value={`USER_ID:${profile.user.id}`} size={300} />
                <p className="text-muted mt-4 mb-4">Muestra este código al instructor para firmar digitalmente.</p>
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
