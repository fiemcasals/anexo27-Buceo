import React, { useState, useEffect } from 'react';
import api from '../api';

/**
 * Portero: nadie usa el sistema sin aceptar las condiciones.
 *
 * La fecha de aceptacion queda sellada en el perfil, asi que esto aparece una
 * sola vez por persona. Envuelve a la aplicacion entera y no a una pantalla:
 * el buzo, el medico y el administrador tienen que pasar por aca igual.
 */
const Condiciones = ({ onLogout, children }) => {
  const [aceptado, setAceptado] = useState(null); // null = todavia no sabemos
  const [rechazado, setRechazado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let vigente = true;
    api.get('profiles/me/')
      .then(res => { if (vigente) setAceptado(!!res.data.terms_accepted_at); })
      // Si el perfil no carga, no dejamos la app trabada detras del portero:
      // el 401 ya manda al login por su cuenta.
      .catch(() => { if (vigente) setAceptado(true); });
    return () => { vigente = false; };
  }, []);

  const aceptar = async () => {
    setGuardando(true);
    setError('');
    try {
      await api.post('profiles/accept-terms/');
      setAceptado(true);
    } catch {
      setError('No se pudo registrar la aceptación. Probá de nuevo.');
    } finally {
      setGuardando(false);
    }
  };

  if (aceptado === null) {
    return <div className="p-5 text-center text-muted">Cargando…</div>;
  }
  if (aceptado) return children;

  return (
    <div className="d-flex align-items-center justify-content-center bg-light p-4"
         style={{ minHeight: '100vh', width: '100%' }}>
      <div className="card border-0 shadow-sm p-4 p-md-5" style={{ maxWidth: '640px' }}>
        {rechazado ? (
          <>
            <h4 className="fw-bold mb-3">Entendido</h4>
            <p className="mb-4">
              Podés presentar tu documentación personalmente en la unidad, por los
              medios habituales. Tu cuenta queda como está: cuando quieras, volvés a
              ingresar y las condiciones te aparecen de nuevo.
            </p>
            <button className="btn btn-primary rounded-pill px-4 align-self-start"
                    onClick={onLogout}>
              Volver al ingreso
            </button>
          </>
        ) : (
          <>
            <h4 className="fw-bold mb-1">Condiciones de uso</h4>
            <p className="text-muted mb-4">Sistema en etapa de prueba</p>

            <p>
              Este sistema es un <strong>prototipo</strong> en evaluación. Al cargar
              documentación en él, usted acepta que la información quedará{' '}
              <strong>accesible para el administrador del sistema</strong>, responsable
              de su desarrollo y mantenimiento.
            </p>
            <p>
              Si tiene documentación o datos que prefiera mantener bajo reserva,{' '}
              <strong>puede entregarlos personalmente en la unidad</strong>, por los
              medios habituales.
            </p>
            <p className="mb-4">
              <strong>El uso de este sistema no es obligatorio</strong> hasta tanto se
              maximicen las políticas de privacidad y resguardo de la información.
            </p>

            {error && (
              <div className="alert alert-warning py-2" role="alert">{error}</div>
            )}

            <div className="d-flex flex-wrap gap-2">
              <button className="btn btn-primary rounded-pill px-4"
                      onClick={aceptar} disabled={guardando}>
                {guardando ? 'Guardando…' : 'Acepto'}
              </button>
              <button className="btn btn-outline-secondary rounded-pill px-4"
                      onClick={() => setRechazado(true)}>
                Ahora no
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Condiciones;
