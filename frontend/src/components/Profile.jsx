import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import BarraLateral from './BarraLateral';
import CampoFecha from './CampoFecha';

// Los nombres que se leen en la pantalla, para que un error diga QUE campo falla
// y no solo "este campo no puede estar en blanco".
const ETIQUETAS = {
  first_name: 'Nombre', last_name: 'Apellido', dni: 'DNI', birth_date: 'Fecha de nacimiento',
  phone: 'Teléfono', rank: 'Grado', destination: 'Destino', weight: 'Peso', height: 'Altura',
};

const Profile = ({ onLogout, perfil }) => {
  const [profile, setProfile] = useState({
    first_name: '',
    last_name: '',
    dni: '',
    birth_date: '',
    phone: '',
    rank: '',
    destination: '',
    weight: '',
    height: '',
    profile_data: {}
  });
  const [loading, setLoading] = useState(true);
const [grupos, setGrupos] = useState(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  // La lista de grados la define el backend: no se redefine acá.
  useEffect(() => {
    let vigente = true;
    api.get('grados/')
      .then(res => { if (vigente) setGrupos(res.data); })
      .catch(() => { if (vigente) setGrupos([]); });
    return () => { vigente = false; };
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
        birth_date: res.data.birth_date || '',
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
    
    // Clean data: convert empty strings to null for numeric and date fields
    const cleanedProfile = { ...profile };
    ['weight', 'height', 'birth_date'].forEach(field => {
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
      const datos = err.response?.data;
      const detalle = datos && typeof datos === 'object'
        ? Object.entries(datos).map(([campo, msgs]) => `${ETIQUETAS[campo] || campo}: ${[].concat(msgs).join(' ')}`).join(' ')
        : '';
      alert(detalle ? `No se pudo guardar el perfil. ${detalle}` : 'Error al guardar el perfil. Revise los datos ingresados.');
    }
  };

  if (loading) return <div className="p-5 text-center">Cargando...</div>;

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <BarraLateral role={perfil?.role} onLogout={onLogout} />

      <div className="flex-grow-1 p-5 bg-light overflow-auto">
        <div className="d-flex justify-content-between align-items-center mb-5">
          <div>
            <h2 className="fw-bold mb-1">Configuración del Perfil</h2>
            <p className="text-muted">Los datos personales tienen que estar actualizados.</p>
          </div>
        </div>

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
                <label className="form-label fw-medium text-muted small">Fecha de nacimiento</label>
                <CampoFecha id="birth_date" value={profile.birth_date} onChange={(v) => setProfile({ ...profile, birth_date: v })} className="form-control form-control-lg border-0 bg-light" />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Teléfono</label>
                <input type="text" name="phone" className="form-control form-control-lg border-0 bg-light" value={profile.phone} onChange={handleChange} placeholder="+54 9..." />
              </div>
              <div className="col-md-6">
                <label className="form-label fw-medium text-muted small">Grado</label>
                <select name="rank" disabled={!grupos} className="form-select form-select-lg border-0 bg-light" value={profile.rank} onChange={handleChange}>
                    <option value="">{grupos ? 'Elegir el grado' : 'Cargando…'}</option>
                    {(grupos || []).map(g => (
                      <optgroup key={g.grupo} label={g.grupo}>
                        {g.grados.map(gr => <option key={gr.valor} value={gr.valor}>{gr.etiqueta}</option>)}
                      </optgroup>
                    ))}
                  </select>
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
