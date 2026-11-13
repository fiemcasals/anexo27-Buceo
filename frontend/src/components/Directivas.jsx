import { useState, useEffect, useCallback } from 'react';
import api from '../api';
import BarraLateral from './BarraLateral';

// Las directivas (de habilitación, de inmersión, de cada curso), siempre en PDF.
// Todos las ven como título + enlace de descarga; el administrador además las
// carga y las borra.

function mensajeDe(err, porDefecto) {
  const d = err.response?.data;
  if (d && typeof d === 'object') {
    const texto = Object.values(d).flat().join(' ');
    if (texto) return texto;
  }
  return porDefecto;
}

const Directivas = ({ onLogout, perfil }) => {
  const esAdmin = perfil?.role === 'ADMIN';
  const [directivas, setDirectivas] = useState(null);
  const [fallo, setFallo] = useState('');
  const [aviso, setAviso] = useState('');
  const [titulo, setTitulo] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [subiendo, setSubiendo] = useState(false);
  const [claveInput, setClaveInput] = useState(0); // para vaciar el input de archivo

  const traer = useCallback(async () => {
    try {
      const res = await api.get('directivas/');
      setDirectivas(res.data);
      setFallo('');
    } catch (err) {
      setFallo(mensajeDe(err, 'No se pudieron traer las directivas.'));
    }
  }, []);

  useEffect(() => { traer(); }, [traer]);

  const cargar = async (e) => {
    e.preventDefault();
    setAviso(''); setFallo('');
    if (!titulo.trim() || !archivo) {
      setFallo('Escribí el título y elegí el PDF.');
      return;
    }
    const datos = new FormData();
    datos.append('title', titulo.trim());
    datos.append('file', archivo);
    setSubiendo(true);
    try {
      await api.post('directivas/', datos);
      setTitulo(''); setArchivo(null); setClaveInput(n => n + 1);
      setAviso('Directiva cargada.');
      await traer();
    } catch (err) {
      setFallo(mensajeDe(err, 'No se pudo cargar la directiva.'));
    } finally {
      setSubiendo(false);
    }
  };

  const borrar = async (d) => {
    if (!window.confirm(`¿Borrar la directiva "${d.title}"?`)) return;
    setAviso(''); setFallo('');
    try {
      await api.delete(`directivas/${d.id}/`);
      setAviso('Directiva borrada.');
      await traer();
    } catch (err) {
      setFallo(mensajeDe(err, 'No se pudo borrar la directiva.'));
    }
  };

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={perfil?.role} onLogout={onLogout} />
      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '900px' }}>
          <h1 className="fw-bold mb-3" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
            Directivas
          </h1>

          {fallo && <div className="alert alert-warning" role="alert">{fallo}</div>}
          {aviso && <div className="alert alert-success py-2" role="status">{aviso}</div>}

          {esAdmin && (
            <form onSubmit={cargar} className="card p-3 mb-4">
              <div className="fw-semibold mb-2">Cargar una directiva</div>
              <div className="d-flex flex-wrap gap-2">
                <input type="text" className="form-control" style={{ flex: '1 1 240px', width: 'auto' }}
                       placeholder="Título (ej.: Directiva de inmersión)" aria-label="Título"
                       maxLength={200} value={titulo} onChange={(e) => setTitulo(e.target.value)} />
                <input key={claveInput} type="file" accept="application/pdf,.pdf"
                       className="form-control" style={{ flex: '1 1 240px', width: 'auto' }}
                       aria-label="Archivo PDF" onChange={(e) => setArchivo(e.target.files[0] || null)} />
                <button type="submit" className="btn btn-primary" disabled={subiendo}>
                  {subiendo ? 'Subiendo…' : 'Cargar'}
                </button>
              </div>
              <div className="form-text">Sólo PDF, hasta 20 MB.</div>
            </form>
          )}

          {!directivas && !fallo && <div className="text-muted">Cargando…</div>}
          {directivas && directivas.length === 0 && (
            <div className="text-muted">Todavía no hay directivas cargadas.</div>
          )}
          {directivas && directivas.length > 0 && (
            <div className="d-flex flex-column gap-2">
              {directivas.map(d => (
                <div key={d.id} className="card px-3 py-2 d-flex flex-row align-items-center gap-2">
                  <i className="bi bi-file-earmark-pdf"></i>
                  <a href={d.url} target="_blank" rel="noopener noreferrer" download
                     style={{ flex: '1 1 0', minWidth: 0, overflowWrap: 'anywhere' }}>
                    {d.title}
                  </a>
                  {esAdmin && (
                    <button type="button" className="btn btn-sm btn-outline-danger"
                            onClick={() => borrar(d)} aria-label={`Borrar ${d.title}`}>
                      <i className="bi bi-trash"></i>
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Directivas;
