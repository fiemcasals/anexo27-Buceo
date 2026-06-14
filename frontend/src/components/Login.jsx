import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const Login = ({ onLogin }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isForgotMode, setIsForgotMode] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    passwordConfirm: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isForgotMode) {
        await api.post('auth/password/reset/', { email: formData.email });
        setSuccessMsg('Si el correo existe, te enviaremos un enlace para restablecer tu contraseña.');
        setIsForgotMode(false);
      } else if (isRegistering) {
        if (formData.password !== formData.passwordConfirm) {
          setError('Las contraseñas no coinciden.');
          setLoading(false);
          return;
        }
        // Register using dj-rest-auth registration endpoint
        const response = await api.post('auth/registration/', {
          username: formData.email.split('@')[0],
          email: formData.email,
          password: formData.password,
          password1: formData.password,
          password2: formData.passwordConfirm,
        });
        const token = response.data.key;
        localStorage.setItem('token', token);
        onLogin();
        navigate('/dashboard');
      } else {
        // Login
        const response = await api.post('auth/login/', {
          email: formData.email,
          password: formData.password
        });
        const token = response.data.key;
        localStorage.setItem('token', token);
        onLogin();
        navigate('/dashboard');
      }
    } catch (err) {
      console.error("Auth error", err);
      let errorMsg = 'Error al procesar la solicitud.';
      if (err.response?.data) {
        // format errors if they exist
        const data = err.response.data;
        if (typeof data === 'object') {
          errorMsg = Object.values(data).map(v => Array.isArray(v) ? v.join(' ') : v).join(' ');
        }
      }
      if (!isForgotMode) setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container d-flex justify-content-center align-items-center" style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      <div className="card shadow-lg p-5 glass" style={{ maxWidth: '400px', width: '100%', textAlign: 'center', backgroundColor: '#fff' }}>
        <div className="mb-4">
          <div className="bg-primary d-inline-block p-3 rounded-circle mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="white" viewBox="0 0 16 16">
              <path d="M8 1a2 2 0 0 0-2 2v2H5V3a3 3 0 1 1 6 0v2h-1V3a2 2 0 0 0-2-2zM5 5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5z" />
            </svg>
          </div>
          <h2 className="fw-bold mb-1">Anexo Buceo</h2>
          <p className="text-secondary small">Centraliza y comparte tus estudios medicos</p>
        </div>


        {error && <div className="alert alert-danger py-2 small mb-3">{error}</div>}
        {successMsg && <div className="alert alert-success py-2 small mb-3">{successMsg}</div>}

        {isForgotMode ? (
          <form onSubmit={handleSubmit} className="text-start">
            <p className="small text-muted mb-3">Ingresa tu correo para recibir un enlace de recuperación.</p>
            <div className="mb-4">
              <label className="form-label small fw-bold">Correo Electrónico</label>
              <input
                type="email"
                name="email"
                className="form-control"
                placeholder="Tu correo"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary w-100 py-2 fw-bold mb-3" disabled={loading}>
              <span className={`spinner-border spinner-border-sm me-2 ${loading ? '' : 'd-none'}`} role="status" aria-hidden="true"></span>
              <span>Enviar enlace</span>
            </button>
            <div className="text-center text-muted small mt-2">
              <a href="#" onClick={(e) => { e.preventDefault(); setIsForgotMode(false); setError(''); setSuccessMsg(''); }} className="text-primary text-decoration-none fw-bold">
                Volver al inicio de sesión
              </a>
            </div>
          </form>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="text-start">
              <div className="mb-3">
                <label className="form-label small fw-bold">Correo Electrónico</label>
                <input
                  type="email"
                  name="email"
                  className="form-control"
                  placeholder="correo@ejemplo.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="form-label small fw-bold">Contraseña</label>
                <div className="input-group">
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    className="form-control"
                    placeholder="Tu contraseña"
                    value={formData.password}
                    onChange={handleChange}
                    required
                  />
                  <button className="btn btn-outline-secondary" type="button" onClick={() => setShowPassword(!showPassword)}>
                    <i className={`bi bi-eye${showPassword ? '-slash' : ''}`}></i>
                  </button>
                </div>
              </div>

              {isRegistering && (
                <div className="mb-4">
                  <label className="form-label small fw-bold">Confirmar Contraseña</label>
                  <div className="input-group">
                    <input
                      type={showPassword ? "text" : "password"}
                      name="passwordConfirm"
                      className="form-control"
                      placeholder="Repite tu contraseña"
                      value={formData.passwordConfirm}
                      onChange={handleChange}
                      required
                    />
                    <button className="btn btn-outline-secondary" type="button" onClick={() => setShowPassword(!showPassword)}>
                      <i className={`bi bi-eye${showPassword ? '-slash' : ''}`}></i>
                    </button>
                  </div>
                </div>
              )}

              <button type="submit" className="btn btn-primary w-100 py-2 fw-bold mb-2" disabled={loading}>
                <span className={`spinner-border spinner-border-sm me-2 ${loading ? '' : 'd-none'}`} role="status" aria-hidden="true"></span>
                <span>{isRegistering ? 'Registrarse' : 'Iniciar Sesión'}</span>
              </button>

              {!isRegistering && (
                <div className="text-end mb-3">
                  <a href="#" onClick={(e) => { e.preventDefault(); setIsForgotMode(true); setError(''); setSuccessMsg(''); }} className="small text-decoration-none text-muted">
                    ¿Olvidaste tu contraseña?
                  </a>
                </div>
              )}
            </form>

            <div className="text-muted small mt-2">
              {isRegistering ? '¿Ya tienes cuenta? ' : '¿No tienes cuenta? '}
              <a href="#" onClick={(e) => { e.preventDefault(); setIsRegistering(!isRegistering); setError(''); setSuccessMsg(''); }} className="text-primary text-decoration-none fw-bold">
                {isRegistering ? 'Inicia sesión aquí' : 'Regístrate aquí'}
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Login;
