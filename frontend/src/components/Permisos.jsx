import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { nombreConGrado } from '../lib/nombre-con-grado';
import Soporte from './Soporte';
import BarraLateral from './BarraLateral';
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
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: 'var(--texto-fuerte)' }}>
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
                 style={{ fontSize: '11px', letterSpacing: '.08em', color: 'var(--texto-suave)' }}>
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
                      {p.nombre}
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
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: 'var(--texto-fuerte)' }}>
        Fechas de habilitación {ciclo}
      </h2>
      <p className="text-muted mb-4" style={{ fontSize: '13px' }}>
        Cada buzo elige una de estas fechas, y sus estudios tienen que estar
        vigentes ese día.
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

function Campeones({ datos, onGuardar, ocupado }) {
  const anioActual = new Date().getFullYear();
  const [anio, setAnio] = useState(anioActual);
  const [grupo, setGrupo] = useState('');
  if (!datos) return null;
  const nombreDe = (codigo) => datos.grupos.find((g) => g.codigo === codigo)?.nombre || codigo;
  return (
    <section className="bg-white rounded-4 shadow-sm p-4 mt-4">
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: 'var(--texto-fuerte)' }}>
        Grupo campeón
      </h2>
      <p className="text-muted mb-3" style={{ fontSize: '13px' }}>
        El grupo que ganó la competencia del último día de la habilitación. Se
        muestra en el perfil de sus integrantes hasta que se cargue otro año.
      </p>
      {datos.campeones.length > 0 && (
        <ul className="list-unstyled mb-3" style={{ fontSize: '14px' }}>
          {datos.campeones.map((c, i) => (
            <li key={c.year}>
              <strong>{c.year}</strong> · {nombreDe(c.group)}
              {i === 0 && <span className="text-muted"> (vigente)</span>}
            </li>
          ))}
        </ul>
      )}
      <div className="row g-2 align-items-end">
        <div className="col-4 col-sm-auto">
          <label htmlFor="campeon-anio" className="form-label fw-semibold" style={{ fontSize: '13px' }}>Año</label>
          <input id="campeon-anio" type="number" className="form-control"
                 value={anio} onChange={(e) => setAnio(e.target.value)} />
        </div>
        <div className="col-8 col-sm-auto">
          <label htmlFor="campeon-grupo" className="form-label fw-semibold" style={{ fontSize: '13px' }}>Grupo</label>
          <select id="campeon-grupo" className="form-select" value={grupo}
                  onChange={(e) => setGrupo(e.target.value)}>
            <option value="">Elegir el grupo</option>
            {datos.grupos.map((g) => <option key={g.codigo} value={g.codigo}>{g.nombre}</option>)}
          </select>
        </div>
        <div className="col-12 col-sm-auto">
          <button type="button" className="btn btn-primary w-100" disabled={!grupo || !anio || ocupado}
                  onClick={() => onGuardar({ year: Number(anio), group: grupo })}>
            Guardar campeón
          </button>
        </div>
      </div>
    </section>
  );
}

function Adicionales({ adicionales, onAgregar, onQuitar, ocupado, errores }) {
  const [nueva, setNueva] = useState('');
  const error = errorDe(errores, 'fecha');
  return (
    <section className="bg-white rounded-4 shadow-sm p-4 mt-4">
      <h2 className="fw-bold mb-1" style={{ fontSize: '17px', color: 'var(--texto-fuerte)' }}>
        Fechas adicionales
      </h2>
      <p className="text-muted mb-3" style={{ fontSize: '13px' }}>
        Otras fechas de habilitación, además de las tres del ciclo. Los buzos
        también pueden elegirlas.
      </p>
      {adicionales.length === 0 && (
        <div className="text-muted mb-3" style={{ fontSize: '13px' }}>
          Todavía no hay fechas adicionales.
        </div>
      )}
      {adicionales.map((a) => (
        <div key={a.id} className="d-flex align-items-center gap-3 mb-2">
          <span style={{ fontSize: '14px' }}>{textoDeFecha(a.fecha)}</span>
          <button type="button" className="btn btn-outline-secondary btn-sm"
                  disabled={ocupado} onClick={() => onQuitar(a.id)}>
            Quitar
          </button>
        </div>
      ))}
      <div className="d-flex flex-wrap align-items-start gap-3 mt-3">
        <div style={{ minWidth: '200px' }}>
          <CampoFecha id="fecha-adicional" value={nueva}
                      onChange={setNueva} error={error} />
        </div>
        <button type="button" className="btn btn-primary"
                disabled={!nueva || ocupado}
                onClick={() => { onAgregar(nueva); setNueva(''); }}>
          Agregar fecha
        </button>
      </div>
    </section>
  );
}

const Permisos = ({ onLogout, perfil }) => {
  const [designados, setDesignados] = useState(null);
  const [ciclo, setCiclo] = useState(null);
  const [fechas, setFechas] = useState([]);
  const [adicionales, setAdicionales] = useState([]);
  const [campeones, setCampeones] = useState(null);
  const [editado, setEditado] = useState({});
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState(null);
  const [guardando, setGuardando] = useState(null);
  const [erroresRol, setErroresRol] = useState(null);
  const [erroresFecha, setErroresFecha] = useState(null);
  const [aviso, setAviso] = useState(null);


  const traer = useCallback(() => {
    return Promise.all([
      api.get('admin/roles/'),
      api.get('admin/fechas/'),
      api.get('admin/campeones/'),
    ]).then(([rs, fs, cs]) => {
      setDesignados(rs.data);
      setCampeones(cs.data);
      setCiclo(fs.data.cycle);
      setFechas(fs.data.fechas);
      setAdicionales(fs.data.adicionales || []);
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
        setAdicionales(res.data.adicionales || []);
        const vuelta = {};
        for (const f of res.data.fechas) vuelta[f.slot] = f.fecha || '';
        setEditado(vuelta);
        setAviso('Fechas guardadas.');
      })
      .catch((err) => setErroresFecha(
        err.response?.data || { cycle: 'No se pudieron guardar las fechas.' }))
      .finally(() => setGuardando(null));
  };

  const guardarCampeon = (cuerpo) => {
    setGuardando('campeon');
    setErroresFecha(null);
    setAviso(null);
    api.put('admin/campeones/', cuerpo)
      .then((res) => { setCampeones(res.data); setAviso('Grupo campeón guardado.'); })
      .catch((err) => setErroresFecha(
        err.response?.data || { cycle: 'No se pudo guardar el campeón.' }))
      .finally(() => setGuardando(null));
  };

  const agregarAdicional = (fecha) => {
    setGuardando('adicional');
    setErroresFecha(null);
    setAviso(null);
    api.post('admin/fechas/adicionales/', { cycle: ciclo, fecha })
      .then(() => { setAviso('Fecha adicional agregada.'); return traer(); })
      .catch((err) => setErroresFecha(
        err.response?.data || { cycle: 'No se pudo agregar la fecha.' }))
      .finally(() => setGuardando(null));
  };

  const quitarAdicional = (id) => {
    setGuardando('adicional');
    setErroresFecha(null);
    setAviso(null);
    api.delete(`admin/fechas/adicionales/${id}/`)
      .then(() => { setAviso('Fecha adicional quitada.'); return traer(); })
      .catch((err) => setErroresFecha({
        cycle: err.response?.data?.detail || 'No se pudo quitar la fecha.' }))
      .finally(() => setGuardando(null));
  };

  const nombre = nombreConGrado({
    grado: perfil?.rank, nombre: perfil?.first_name, apellido: perfil?.last_name,
  });

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <BarraLateral role={perfil?.role} onLogout={onLogout} />

      <div className="flex-grow-1 bg-light">
        <div className="mx-auto px-3 py-4" style={{ maxWidth: '720px' }}>
          <h1 className="fw-bold mb-0" style={{ fontSize: '20px', color: 'var(--texto-fuerte)' }}>
            Permisos
          </h1>
          {nombre && (
            <div className="mb-4" style={{ fontSize: '13px', color: 'var(--texto-suave)' }}>
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
              <Adicionales
                adicionales={adicionales}
                onAgregar={agregarAdicional}
                onQuitar={quitarAdicional}
                ocupado={guardando === 'adicional'}
                errores={erroresFecha}
              />
              <Campeones datos={campeones} onGuardar={guardarCampeon}
                         ocupado={guardando === 'campeon'} />
            </>
          )}
          <Soporte />
        </div>
      </div>
    </div>
  );
};

export default Permisos;
