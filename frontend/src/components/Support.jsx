import React, { useState, useEffect } from 'react';
import api from '../api';
import Sidebar from './Sidebar';

// Los 13 puntos de la planilla de verificación del instructivo de pruebas.
const PASOS = [
  '1. Crear la cuenta e ingresar con el correo',
  '2. Recuperar la contraseña por correo',
  '3. Datos del perfil y código QR',
  '4. Cargar un estudio (PDF o foto) y abrirlo',
  '5. Compartir la documentación por correo',
  '6. Dictaminar con nivel Médico Auditor',
  '7. Nivel Lectura: ver sin poder dictaminar',
  '8. Compartir un estudio puntual sin exponer el resto',
  '9. Recibir el dictamen firmado',
  '10. Revocar el acceso',
  '11. No ver documentación ajena',
  '12. Panel de Administración',
  '13. Usar el sistema desde el celular',
  'Otro / no está en la lista',
];

const Support = ({ onLogout }) => {
  const [profile, setProfile] = useState(null);
  const [step, setStep] = useState(PASOS[0]);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.get('profiles/me/').then(res => setProfile(res.data)).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post('support/', { step, message });
      setSent(true);
      setMessage('');
    } catch (err) {
      alert(err.response?.data?.error || 'No se pudo enviar el reporte. Intentá de nuevo.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <Sidebar active="/soporte" onLogout={onLogout} isSuperUser={profile?.user?.is_superuser} />

      <div className="main-content flex-grow-1 p-5 bg-light overflow-auto">
        <div className="mb-5">
          <h2 className="fw-bold mb-1">Soporte</h2>
          <p className="text-muted">Contanos qué no funcionó. El reporte llega directo a quienes mantienen el sistema.</p>
        </div>

        <div className="row">
          <div className="col-lg-7">
            <div className="card border-0 shadow-sm p-4">
              {sent ? (
                <div className="text-center py-4">
                  <i className="bi bi-check-circle text-success" style={{ fontSize: '3rem' }}></i>
                  <h5 className="fw-bold mt-3">Reporte enviado</h5>
                  <p className="text-muted mb-4">Gracias. Si hace falta, te vamos a responder a tu correo.</p>
                  <button className="btn btn-outline-primary rounded-pill px-4" onClick={() => setSent(false)}>
                    Reportar otra cosa
                  </button>
                </div>
              ) : (
                <form onSubmit={submit}>
                  <label className="form-label fw-semibold">¿En qué paso te pasó?</label>
                  <select className="form-select rounded-pill mb-4" value={step} onChange={e => setStep(e.target.value)}>
                    {PASOS.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>

                  <label className="form-label fw-semibold">¿Qué pasó?</label>
                  <textarea className="form-control mb-2" rows="6" required
                            placeholder="Qué esperabas que pasara, qué pasó en realidad y el mensaje de error tal cual apareció."
                            value={message} onChange={e => setMessage(e.target.value)} />
                  <p className="text-muted small mb-4">
                    Se envían tu correo, el paso, lo que escribas y la fecha. No se adjuntan capturas de pantalla.
                  </p>

                  <button type="submit" className="btn btn-primary rounded-pill px-4" disabled={sending}>
                    {sending ? 'Enviando...' : 'Enviar reporte'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Support;
