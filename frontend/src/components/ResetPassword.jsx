import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

const ResetPassword = () => {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await api.post('auth/password/reset/confirm/', {
        uid: uid,
        token: token,
        new_password1: formData.password,
        new_password2: formData.confirmPassword
      });
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      console.error("Reset error", err);
      let errorMsg = 'Error al restablecer la contraseña. El enlace podría ser inválido o haber expirado.';
      if (err.response?.data) {
        const data = err.response.data;
        if (typeof data === 'object') {
          errorMsg = Object.values(data).map(v => Array.isArray(v) ? v.join(' ') : v).join(' ');
        }
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container d-flex justify-content-center align-items-center" style={{minHeight: '100vh', backgroundColor: '#f8f9fa'}}>
      <div className="card shadow-lg p-5 glass" style={{ maxWidth: '400px', width: '100%', textAlign: 'center', backgroundColor: '#fff' }}>
        <h3 className="fw-bold mb-4">Nueva Contraseña</h3>
        
        {success ? (
          <div className="alert alert-success py-3">
            ¡Contraseña restablecida con éxito! Redirigiendo al login...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="text-start">
            {error && <div className="alert alert-danger py-2 small mb-3">{error}</div>}
            
            <div className="mb-3">
              <label className="form-label small fw-bold">Nueva Contraseña</label>
              <input 
                type="password" 
                name="password" 
                className="form-control" 
                placeholder="Ingresa la nueva contraseña"
                value={formData.password}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-4">
              <label className="form-label small fw-bold">Confirmar Contraseña</label>
              <input 
                type="password" 
                name="confirmPassword" 
                className="form-control" 
                placeholder="Repite la contraseña"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
              />
            </div>
            
            <button type="submit" className="btn btn-primary w-100 py-2 fw-bold" disabled={loading}>
              <span className={`spinner-border spinner-border-sm me-2 ${loading ? '' : 'd-none'}`} role="status" aria-hidden="true"></span>
              <span>Restablecer Contraseña</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPassword;
