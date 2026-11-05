import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import Soporte from './Soporte';
import CampoFecha from './CampoFecha';
import {
  textoDeFecha,
  filaDeRol,
  loQueSeManda,
} from '../lib/decisiones-del-administrador';

// La pantalla del administrador de la unidad. Hace dos cosas: designa al médico
// y a los enfermeros auxiliares, y carga las tres fechas de habilitación del
// ciclo. Nada más.
//
// Las dos vivían sólo en el admin de Django. Lo que la webapp ofrecía era dar
// permisos de instructor y de superusuario, que son de la bitácora de buceo
// —una sección aparte, de historial de buceo— y no del circuito de aptitud.

const ROLES = [
  { valor: 'DOCTOR', etiqueta: 'Médico' },
  { valor: 'NURSE', etiqueta: 'Enfermero auxiliar' },
];

// Los rótulos de las fechas son los que pidió la unidad, palabra por palabra.
// Un lugar que no esté acá cae en la etiqueta que manda el servidor: un lugar
// nuevo tiene que aparecer con su nombre, no sin rótulo.
const ROTULOS = {
  FIRST: 'Fecha 1ra Habilitación',
  SECOND: 'Fecha 2da Habilitación',
  COMPLEMENTARY: 'Fecha Habilitación complementaria',
};

// Un error de DRF llega como {campo: ["texto"]}. Esto saca el texto del campo
// pedido, que es lo que se muestra al lado del input. El §10 lo exige: un error
// que no está junto a su campo no se puede ubicar.
function errorDe(errores, campo) {
  const valor = errores && errores[campo];
  if (!valor) return null;
  return Array.isArray(valor) ? valor[0] : String(valor);
}

function Revisores({ designados, onDesignar, guardando, errores }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('DOCTOR');

  const enviar = (e) => {
    e.preventDefault();
    onDesignar({ email: email.trim(), role }, () => setEmail(''));
  };

  return (
    <section className="bg-white rounded-4 shadow-sm p-4 mb-4">
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: '#15213b' }}>
        Quién revisa los estudios
      </h2>
      <p className="text-muted mb-4" style={{ fontSize: '13px' }}>
        El médico y los enfermeros auxiliares ven los estudios de todos los
        buzos. El resto ve solamente los propios.
      </p>

      {ROLES.map(({ valor, etiqueta }) => {
        const fila = filaDeRol(designados, valor);
        return (
          <div key={valor} className="mb-4">
            <div className="text-uppercase fw-semibold mb-2"
                 style={{ fontSize: '11px', letterSpacing: '.08em', color: '#7a8499' }}>
              {etiqueta}
            </div>
            {fila.vacia ? (
              // Se dice con palabras y no con una fila en blanco: vacío es
              // indistinguible de "no cargó", y el administrador concluiría
              // que ya designó a alguien.
              <div className="text-muted fst-italic" style={{ fontSize: '14px' }}>
                Nadie designado todavía.
              </div>
            ) : (
              <ul className="list-unstyled m-0">
                {fila.gente.map((p) => (
                  <li key={p.email} className="d-flex flex-wrap align-items-baseline gap-2 py-1">
                    <span className="fw-medium" style={{ fontSize: '15px' }}>
                      {p.rank ? `${p.rank} ` : ''}{p.nombre}
                    </span>
                    <span className="text-muted" style={{ fontSize: '13px' }}>{p.email}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}

      <form onSubmit={enviar} className="border-top pt-4">
        <label className="form-label fw-semibold" style={{ fontSize: '14px' }}>
          Designar a alguien
        </label>
        <div className="row g-2 align-items-start">
          <div className="col-12 col-md-5">
            <input
              type="email"
              id="permisos-email"
              className={`form-control${errorDe(errores, 'email') ? ' is-invalid' : ''}`}
              placeholder="Correo de la persona"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            {errorDe(errores, 'email') && (
              <div className="invalid-feedback d-block">{errorDe(errores, 'email')}</div>
            )}
          </div>
          <div className="col-12 col-md-4">
            <select
              id="permisos-role"
              className={`form-select${errorDe(errores, 'role') ? ' is-invalid' : ''}`}
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="DOCTOR">Médico</option>
              <option value="NURSE">Enfermero auxiliar</option>
              <option value="USER">Quitarle el permiso</option>
            </select>
            {errorDe(errores, 'role') && (
              <div className="invalid-feedback d-block">{errorDe(errores, 'role')}</div>
            )}
          </div>
          <div className="col-12 col-md-3">
            <button type="submit" className="btn btn-primary w-100" disabled={guardando}>
              {guardando ? 'Guardando…' : 'Designar'}
            </button>
          </div>
        </div>
        <div className="form-text">
          Se la identifica por el correo con el que entra al sistema.
        </div>
      </form>
    </section>
  );
}

function Fechas({ ciclo, fechas, editado, onEditar, onGuardar, guardando, errores }) {
  const original = {};
  for (const f of fechas) original[f.slot] = f.fecha;
  const pendiente = loQueSeManda(ciclo, editado, original);

  return (
    <section className="bg-white rounded-4 shadow-sm p-4">
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: '#15213b' }}>
        Fechas de habilitación {ciclo}
      </h2>
      <p className="text-muted mb-4" style={{ fontSize: '13px' }}>
        Cada buzo elige una de estas fechas, y sus estudios tienen que estar
        vigentes ese día. Un ciclo con menos de tres cargadas es normal.
      </p>

      <div className="row g-3">
        {fechas.map((f) => {
          const error = errorDe(errores, f.slot);
          return (
            <div key={f.slot} className="col-12 col-md-4">
              <label htmlFor={`fecha-${f.slot}`} className="form-label fw-semibold"
                     style={{ fontSize: '13px' }}>
                {ROTULOS[f.slot] || f.etiqueta}
              </label>
              <CampoFecha
                id={`fecha-${f.slot}`}
                value={editado[f.slot] || ''}
                onChange={(iso) => onEditar(f.slot, iso)}
                error={error}
              />
              <div className="form-text">
                Guardada: {textoDeFecha(f.fecha)}
              </div>
            </div>
          );
        })}
      </div>

      {errorDe(errores, 'cycle') && (
        <div className="alert alert-danger mt-3 mb-0 py-2" style={{ fontSize: '14px' }}>
          {errorDe(errores, 'cycle')}
        </div>
      )}

      <div className="d-flex flex-wrap align-items-center gap-3 mt-4">
        <button type="button" className="btn btn-primary"
                disabled={!pendiente || guardando}
                onClick={() => onGuardar(pendiente)}>
          {guardando ? 'Guardando…' : 'Guardar fechas'}
        </button>
        <span className="text-muted" style={{ fontSize: '13px' }}>
          {pendiente
            ? 'Hay cambios sin guardar.'
            : 'Vaciar un campo no borra la fecha guardada.'}
        </span>
      </div>
    </section>
  );
}

const Permisos = ({ onLogout, perfil }) => {
  const [designados, setDesignados] = useState(null);
  const [ciclo, setCiclo] = useState(null);
  const [fechas, setFechas] = useState([]);
  const [editado, setEditado] = useState({});
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState(null);
  const [guardando, setGuardando] = useState(null);
  const [erroresRol, setErroresRol] = useState(null);
  const [erroresFecha, setErroresFecha] = useState(null);
  const [aviso, setAviso] = useState(null);

  const closeMenu = () => {
    const t = document.getElementById('menu-toggle');
    if (t) t.checked = false;
  };

  const traer = useCallback(() => {
    return Promise.all([
      api.get('admin/roles/'),
      api.get('admin/fechas/'),
    ]).then(([rs, fs]) => {
      setDesignados(rs.data);
      setCiclo(fs.data.cycle);
      setFechas(fs.data.fechas);
      // Los inputs arrancan con lo guardado, así que el administrador ve lo
      // que hay y no tres campos vacíos sobre un ciclo ya cargado.
      const inicial = {};
      for (const f of fs.data.fechas) inicial[f.slot] = f.fecha || '';
      setEditado(inicial);
      setFallo(null);
    });
  }, []);

  useEffect(() => {
    let vigente = true;
    traer()
      .catch(() => { if (vigente) setFallo('No se pudo cargar la pantalla.'); })
      .finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
  }, [traer]);

  const designar = (cuerpo, limpiar) => {
    setGuardando('rol');
    setErroresRol(null);
    setAviso(null);
    api.post('admin/roles/', cuerpo)
      .then((res) => {
        limpiar();
        setAviso(`${res.data.nombre} quedó como ${
          res.data.role === 'DOCTOR' ? 'médico'
            : res.data.role === 'NURSE' ? 'enfermero auxiliar' : 'buzo'}.`);
        return traer();
      })
      .catch((err) => setErroresRol(
        err.response?.data || { email: 'No se pudo designar.' }))
      .finally(() => setGuardando(null));
  };

  const guardarFechas = (cuerpo) => {
    if (!cuerpo) return;
    setGuardando('fechas');
    setErroresFecha(null);
    setAviso(null);
    api.put('admin/fechas/', cuerpo)
      .then((res) => {
        setCiclo(res.data.cycle);
        setFechas(res.data.fechas);
        const vuelta = {};
        for (const f of res.data.fechas) vuelta[f.slot] = f.fecha || '';
        setEditado(vuelta);
        setAviso('Fechas guardadas.');
      })
      .catch((err) => setErroresFecha(
        err.response?.data || { cycle: 'No se pudieron guardar las fechas.' }))
      .finally(() => setGuardando(null));
  };

  const nombre = [perfil?.last_name, perfil?.first_name].filter(Boolean).join(', ');

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <div className="sidebar p-4 d-flex flex-column">
        <div className="d-flex align-items-center mb-5 ps-2">
          <div className="bg-white rounded-circle d-flex align-items-center justify-content-center me-2"
               style={{ width: '35px', height: '35px' }}>
            <i className="bi bi-water text-primary fs-5"></i>
          </div>
          <h4 className="m-0 fw-bold">Anexo Buceo</h4>
        </div>

        <nav className="nav flex-column gap-2 flex-grow-1">
          <Link to="/dashboard" className="nav-link active d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-shield-lock me-3"></i>
            <span>Permisos</span>
          </Link>
          <Link to="/profile" className="nav-link d-flex align-items-center" onClick={closeMenu}>
            <i className="bi bi-person-circle me-3"></i>
            <span>Mi Perfil</span>
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

      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '720px' }}>
          <h1 className="fw-bold mb-0" style={{ fontSize: '20px', color: '#15213b' }}>
            Permisos
          </h1>
          {nombre && (
            <div className="mb-4" style={{ fontSize: '13px', color: '#7a8499' }}>
              {nombre}{perfil?.destination ? ` — ${perfil.destination}` : ''}
            </div>
          )}
          {!nombre && <div className="mb-4" />}

          {cargando && <div className="text-muted">Cargando…</div>}

          {fallo && (
            <div className="alert alert-warning" role="alert">{fallo}</div>
          )}

          {aviso && (
            <div className="alert alert-success py-2" role="status" style={{ fontSize: '14px' }}>
              {aviso}
            </div>
          )}

          {!cargando && !fallo && (
            <>
              <Revisores
                designados={designados}
                onDesignar={designar}
                guardando={guardando === 'rol'}
                errores={erroresRol}
              />
              <Fechas
                ciclo={ciclo}
                fechas={fechas}
                editado={editado}
                onEditar={(slot, valor) =>
                  setEditado((previo) => ({ ...previo, [slot]: valor }))}
                onGuardar={guardarFechas}
                guardando={guardando === 'fechas'}
                errores={erroresFecha}
              />
            </>
          )}
          <Soporte />
        </div>
      </div>
    </div>
  );
};

export default Permisos;
