import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import api from './api';
import ListadoPlantel from './components/ListadoPlantel';
import FichaBuzo from './components/FichaBuzo';
import PantallaBuzo from './components/PantallaBuzo';
import Permisos from './components/Permisos';
import Usuarios from './components/Usuarios';
import Profile from './components/Profile';
import Directivas from './components/Directivas';
import PanelCursos from './components/PanelCursos';
import Login from './components/Login';
import Registro from './components/Registro';
import ResetPassword from './components/ResetPassword';
import Bitacora from './components/Bitacora';
import CompleteDiveLog from './components/CompleteDiveLog';
import Condiciones from './components/Condiciones';

const ES_REVISOR = (perfil) => perfil?.role === 'DOCTOR' || perfil?.role === 'NURSE';

// Sin rol confirmado no se muestra ninguna pantalla.
//
// Si la consulta del perfil falla no se sabe quién es la persona, y cualquier
// pantalla que se le muestre puede ser la que no le corresponde: la del buzo a
// un médico, o el listado del plantel a alguien que no puede verlo. Mostrar una
// pantalla ajena porque una consulta falló es peor que decir que algo falló.
// Por eso el fallo es un cartel con un botón para reintentar.
function SinRol({ onReintentar, onLogout }) {
  return (
    <div className="p-5 text-center" role="alert">
      <h1 className="fs-5 fw-bold">No se pudo cargar el perfil</h1>
      <p className="text-muted">
        Sin el perfil no se puede saber qué pantalla corresponde. Puede ser un
        problema de conexión.
      </p>
      <div className="d-flex gap-2 justify-content-center">
        <button type="button" className="btn btn-primary" onClick={onReintentar}>
          Reintentar
        </button>
        <button type="button" className="btn btn-outline-secondary" onClick={onLogout}>
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}

// El rol decide qué pantalla es `/dashboard`. El buzo —rol `USER`— ve la
// pantalla del §8.3; el administrador ve `Permisos`, que es lo único que hace
// desde la webapp (designar revisores y cargar las fechas del ciclo); el médico
// y el enfermero van al listado del plantel (`/plantel`), que es su herramienta
// de trabajo. Cualquier otro caso —perfil que no cargó, o un rol que no
// conocemos— no es una pantalla: es el cartel de `SinRol`.
function TableroSegunElRol({ perfil, onLogout, onReintentar }) {
  if (perfil && perfil.role === 'USER') {
    return <PantallaBuzo onLogout={onLogout} perfil={perfil} />;
  }
  if (perfil && perfil.role === 'ADMIN') {
    return <Permisos onLogout={onLogout} perfil={perfil} />;
  }
  if (ES_REVISOR(perfil)) {
    return <Navigate to="/plantel" replace />;
  }
  return <SinRol onReintentar={onReintentar} onLogout={onLogout} />;
}

// Las dos pantallas del plantel son sólo del médico y los enfermeros. Un buzo
// o el administrador que lleguen por la dirección vuelven a la suya; sin perfil,
// cartel. (El servidor responde 403 de todos modos: esto evita mostrarles una
// pantalla que sólo va a fallar.)
function SoloRevisores({ perfil, onLogout, onReintentar, children }) {
  if (!perfil) return <SinRol onReintentar={onReintentar} onLogout={onLogout} />;
  if (!ES_REVISOR(perfil)) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [perfil, setPerfil] = useState(undefined);
  const [intentoDelPerfil, setIntentoDelPerfil] = useState(0);

  // El perfil se pide UNA vez por sesión, acá arriba.
  //
  // Antes vivía dentro de la ruta `/dashboard`, así que se volvía a consultar
  // en cada navegación y mientras tanto la pantalla quedaba en blanco: se
  // entraba a `/dashboard` desde el perfil y había un parpadeo blanco antes de
  // que apareciera la barra. Acá arriba el componente no se desmonta al
  // navegar, así que la consulta ocurre una sola vez y no hay parpadeo.
  useEffect(() => {
    // Sin sesión no se consulta nada. El perfil lo limpia `logout`, no este
    // efecto: un `setState` sincrónico acá provoca un render en cascada.
    if (!isAuthenticated) return;
    let vigente = true;
    api.get('profiles/me/')
      .then(res => { if (vigente) setPerfil(res.data); })
      .catch(() => { if (vigente) setPerfil(null); });
    return () => { vigente = false; };
  }, [isAuthenticated, intentoDelPerfil]);

  // Vuelve a pedir el perfil. Pasa por `undefined` para que se vea "Cargando…"
  // y no el cartel, y para que no quede el viejo `null` mientras contesta.
  const reintentarElPerfil = () => {
    setPerfil(undefined);
    setIntentoDelPerfil((n) => n + 1);
  };

  const login = () => setIsAuthenticated(true);
  const logout = () => {
    localStorage.removeItem('token');
    setPerfil(undefined);
    setIsAuthenticated(false);
  };

  // Toda pantalla con sesion pasa por los dos porteros en el mismo orden:
  // primero hay sesion, despues estan aceptadas las condiciones. Antes cada
  // ruta repetia el ternario de la sesion.
  const protegida = (pantalla) => (
    isAuthenticated
      ? <Condiciones onLogout={logout}>{pantalla}</Condiciones>
      : <Navigate to="/login" />
  );
  // `undefined` es "todavía no contestó"; `null` es "falló la consulta". Sólo
  // la primera espera, y una sola vez por sesión.
  const esperandoElPerfil = isAuthenticated && perfil === undefined;

  return (
    <Router>
      {isAuthenticated && (
        <>
          <input type="checkbox" id="menu-toggle" className="menu-toggle" />
          <label htmlFor="menu-toggle" className="menu-btn"><i className="bi bi-list fs-2"></i></label>
            <label htmlFor="menu-toggle" className="menu-overlay" aria-label="Cerrar el menú"></label>
        </>
      )}
      <div className="container-fluid p-0 d-flex-wrapper">
        {esperandoElPerfil ? (
          <div className="p-5 text-center text-muted">Cargando…</div>
        ) : (
          <Routes>
            <Route path="/login" element={<Login onLogin={login} />} />
            <Route path="/registro" element={<Registro onLogin={login} />} />
            <Route path="/password-reset/:uid/:token" element={<ResetPassword />} />
            <Route
              path="/dashboard"
              element={protegida(<TableroSegunElRol perfil={perfil} onLogout={logout}
                                     onReintentar={reintentarElPerfil} />)}
            />
            <Route
              path="/plantel"
              element={protegida(<SoloRevisores perfil={perfil} onLogout={logout} onReintentar={reintentarElPerfil}>
                    <ListadoPlantel onLogout={logout} perfil={perfil} />
                  </SoloRevisores>)}
            />
            <Route
              path="/plantel/:id"
              element={protegida(<SoloRevisores perfil={perfil} onLogout={logout} onReintentar={reintentarElPerfil}>
                    <FichaBuzo onLogout={logout} perfil={perfil} />
                  </SoloRevisores>)}
            />
            <Route
              path="/usuarios"
              element={protegida(perfil && perfil.role === 'ADMIN'
                ? <Usuarios onLogout={logout} perfil={perfil} />
                : <Navigate to="/dashboard" replace />)}
            />
            <Route
              path="/cursos"
              element={protegida(perfil && perfil.role === 'ADMIN'
                ? <PanelCursos onLogout={logout} perfil={perfil} />
                : <Navigate to="/dashboard" replace />)}
            />
            <Route
              path="/directivas"
              element={protegida(<Directivas onLogout={logout} perfil={perfil} />)}
            />
            <Route
              path="/profile"
              element={protegida(<Profile onLogout={logout} perfil={perfil} />)}
            />
            <Route
              path="/bitacora"
              element={protegida(<Bitacora onLogout={logout} perfil={perfil} />)}
            />
            <Route
              path="/bitacora/scan/:token"
              element={protegida(<CompleteDiveLog />)}
            />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        )}
      </div>
    </Router>
  );
}

export default App;
