import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import api from './api';
import Dashboard from './components/Dashboard';
import PantallaBuzo from './components/PantallaBuzo';
import Permisos from './components/Permisos';
import Profile from './components/Profile';
import Login from './components/Login';
import Registro from './components/Registro';
import ResetPassword from './components/ResetPassword';
import Bitacora from './components/Bitacora';
import CompleteDiveLog from './components/CompleteDiveLog';

// El rol decide qué pantalla es `/dashboard`. El buzo —rol `USER`— ve la
// pantalla del §8.3; el administrador ve `Permisos`, que es lo único que hace
// desde la webapp (designar revisores y cargar las fechas del ciclo); el médico
// y el enfermero siguen viendo `Dashboard`, que es su herramienta de trabajo.
//
// Si la consulta del rol falla se cae en `Dashboard`, que es lo que había
// antes: una falla de red no tiene que dejar a nadie frente a una pantalla en
// blanco ni, peor, mostrarle la pantalla del rol equivocado.
function TableroSegunElRol({ perfil, onLogout }) {
  if (perfil && perfil.role === 'USER') {
    return <PantallaBuzo onLogout={onLogout} perfil={perfil} />;
  }
  if (perfil && perfil.role === 'ADMIN') {
    return <Permisos onLogout={onLogout} perfil={perfil} />;
  }
  return <Dashboard onLogout={onLogout} perfil={perfil} />;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [perfil, setPerfil] = useState(undefined);

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
  }, [isAuthenticated]);

  const login = () => setIsAuthenticated(true);
  const logout = () => {
    localStorage.removeItem('token');
    setPerfil(undefined);
    setIsAuthenticated(false);
  };

  // `undefined` es "todavía no contestó"; `null` es "falló la consulta". Sólo
  // la primera espera, y una sola vez por sesión.
  const esperandoElPerfil = isAuthenticated && perfil === undefined;

  return (
    <Router>
      {isAuthenticated && (
        <>
          <input type="checkbox" id="menu-toggle" className="menu-toggle" />
          <label htmlFor="menu-toggle" className="menu-btn"><i className="bi bi-list fs-2"></i></label>
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
              element={isAuthenticated
                ? <TableroSegunElRol perfil={perfil} onLogout={logout} />
                : <Navigate to="/login" />}
            />
            <Route
              path="/profile"
              element={isAuthenticated ? <Profile onLogout={logout} perfil={perfil} /> : <Navigate to="/login" />}
            />
            <Route
              path="/bitacora"
              element={isAuthenticated ? <Bitacora onLogout={logout} perfil={perfil} /> : <Navigate to="/login" />}
            />
            <Route
              path="/bitacora/scan/:token"
              element={isAuthenticated ? <CompleteDiveLog /> : <Navigate to="/login" />}
            />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        )}
      </div>
    </Router>
  );
}

export default App;
