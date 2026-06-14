import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

const CompleteDiveLog = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchLog();
  }, [token]);

  const fetchLog = async () => {
    try {
      const res = await api.get(`dive-logs/by-token/${token}/`);
      setLog(res.data);
      if (res.data.is_completed) {
        setError('Esta bitácora ya fue completada y firmada.');
      }
    } catch (err) {
      if (err.response?.status === 401) {
        alert("Debes iniciar sesión para confirmar tu buceo.");
        navigate('/login');
      } else {
        setError('Token inválido o no encontrado.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    try {
      await api.post(`dive-logs/by-token/${token}/complete/`);
      alert('¡Bitácora firmada digitalmente con éxito!');
      navigate('/bitacora');
    } catch (err) {
      alert(err.response?.data?.error || 'Error al completar la bitácora');
    }
  };

  if (loading) return <div className="p-5 text-center">Cargando datos del buceo...</div>;

  if (error) return (
    <div className="container py-5">
      <div className="alert alert-danger shadow-sm rounded-4 text-center p-5">
        <i className="bi bi-exclamation-triangle fs-1 d-block mb-3"></i>
        <h4 className="fw-bold">{error}</h4>
        <button className="btn btn-primary mt-4 rounded-pill px-4" onClick={() => navigate('/bitacora')}>Ir a mi Bitácora</button>
      </div>
    </div>
  );

  return (
    <div className="container py-5" style={{ maxWidth: '800px' }}>
      <div className="card border-0 shadow-lg rounded-4 overflow-hidden mb-4">
        <div className="bg-primary text-white p-4 text-center">
          <i className="bi bi-water fs-1 mb-2"></i>
          <h3 className="fw-bold m-0">Confirmar Bitácora de Buceo</h3>
          <p className="opacity-75 m-0 mt-2">Revisa los datos cargados por tu instructor antes de firmar</p>
        </div>
        
        <div className="p-4 bg-light border-bottom">
          <h6 className="fw-bold text-uppercase small text-primary mb-3">Datos de la Actividad</h6>
          <div className="row g-2 small mb-4">
            <div className="col-sm-6"><span className="text-muted">Lugar:</span> <span className="fw-medium">{log.activity_details.location_coords}</span></div>
            <div className="col-sm-6"><span className="text-muted">Fecha:</span> <span className="fw-medium">{log.activity_details.date}</span></div>
            <div className="col-sm-6"><span className="text-muted">Escribiente:</span> <span className="fw-medium">{log.activity_details.instructor_name}</span></div>
            <div className="col-sm-6"><span className="text-muted">Profundidad Máx:</span> <span className="fw-medium">{log.activity_details.max_depth_meters}m</span></div>
            <div className="col-sm-6"><span className="text-muted">Tiempo Fondo:</span> <span className="fw-medium">{log.activity_details.duration_minutes} min</span></div>
            <div className="col-sm-6"><span className="text-muted">Buzo Seg:</span> <span className="fw-medium">{log.activity_details.safety_diver_name || '-'}</span></div>
          </div>

          <h6 className="fw-bold text-uppercase small text-primary mb-3 border-top pt-3">Tu Equipamiento y Consumo</h6>
          <div className="row g-2 small mb-4">
            <div className="col-sm-6"><span className="text-muted">Equipo:</span> <span className="fw-medium">{log.equipment_type || '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Traje:</span> <span className="fw-medium">{log.suit_type || '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Lastre:</span> <span className="fw-medium">{log.weight_kgs ? `${log.weight_kgs} kg` : '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Botellón:</span> <span className="fw-medium">{log.tank_type || '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Gas:</span> <span className="fw-medium">{log.gas_type}</span></div>
            <div className="col-sm-6"><span className="text-muted">Presión Inicial:</span> <span className="fw-medium">{log.start_pressure_bar ? `${log.start_pressure_bar} bar` : '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Presión Final:</span> <span className="fw-medium">{log.end_pressure_bar ? `${log.end_pressure_bar} bar` : '-'}</span></div>
          </div>

          <h6 className="fw-bold text-uppercase small text-primary mb-3 border-top pt-3">Descompresión y Observaciones</h6>
          <div className="row g-2 small mb-4">
            <div className="col-sm-6"><span className="text-muted">Nitrógeno PRE:</span> <span className="fw-medium">{log.residual_nitrogen_pre || '-'}</span></div>
            <div className="col-sm-6"><span className="text-muted">Nitrógeno POST:</span> <span className="fw-medium">{log.residual_nitrogen_post || '-'}</span></div>
            <div className="col-12"><span className="text-muted">Parada Descompresión:</span> <span className="fw-medium">{log.decompression_stop ? `Sí (${log.decompression_depth_meters}m por ${log.decompression_time_minutes} min)` : 'No'}</span></div>
            {log.diver_notes && <div className="col-12 mt-2"><span className="text-muted">Observaciones:</span> <span className="fw-medium d-block mt-1">{log.diver_notes}</span></div>}
          </div>

          <div className="mt-5 text-center">
            <p className="text-muted small mb-3">Al aceptar, firmas digitalmente esta bitácora asociándola a tu perfil.</p>
            <button className="btn btn-success px-5 py-3 rounded-pill fw-bold shadow-sm w-100" onClick={handleConfirm}>
              <i className="bi bi-pen-fill me-2"></i>Aceptar y Firmar Bitácora
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompleteDiveLog;
