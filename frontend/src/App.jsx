import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import api from './api';
import Dashboard from './components/Dashboard';
import PantallaBuzo from './components/PantallaBuzo';
import Profile from './components/Profile';
import Login from './components/Login';
import Registro from './components/Registro';
import ResetPassword from './components/ResetPassword';
import Bitacora from './components/Bitacora';
import Permisos from './components/Permisos';
import CompleteDiveLog from './components/CompleteDiveLog';
import Condiciones from './components/Condiciones';

// El rol decide qué pantalla es `/dashboard`. El buzo —rol `USER`— ve la
// pantalla del §8.3; el administrador ve `Permisos`, que es lo único que hace
// desde la webapp (designar revisores y cargar las fechas del ciclo); el médico
// y el enfermero siguen viendo `Dashboard`, que es su herramienta de trabajo.
//
// El instructor es un buzo (`role === 'USER'` con `is_instructor`): también
// presenta sus estudios, así que recibe la pantalla nueva. Ser instructor es
// una capacidad extra, no otro rol.
//
// Si la consulta del rol falla se cae en `Dashboard`, que es lo que había
// antes: una falla de red no tiene que dejar a nadie frente a una pantalla en
// blanco ni, peor, mostrarle la pantalla del rol equivocado.
function TableroSegunElRol({ onLogout }) {
  const [perfil, setPerfil] = useState(undefined);

  useEffect(() => {
    let vigente = true;
    api.get('profiles/me/')
      .then(res => { if (vigente) setPerfil(res.data); })
      .catch(() => { if (vigente) setPerfil(null); });
    return () => { vigente = false; };
  }, []);

  if (perfil === undefined) {
    return <div className="p-5 text-center text-muted">Cargando…</div>;
  }
  if (perfil && perfil.role === 'USER') {
    return <PantallaBuzo onLogout={onLogout} perfil={perfil} />;
  }
  if (perfil && perfil.role === 'ADMIN') {
    return <Permisos onLogout={onLogout} perfil={perfil} />;
  }
  return <Dashboard onLogout={onLogout} />;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const login = () => setIsAuthenticated(true);
  const logout = () => {
    localStorage.removeItem('token');
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

  return (
    <Router>
      {isAuthenticated && (
        <>
          <input type="checkbox" id="menu-toggle" className="menu-toggle" />
          <label htmlFor="menu-toggle" className="menu-btn"><i className="bi bi-list fs-2"></i></label>
        </>
      )}
      <div className="container-fluid p-0 d-flex-wrapper">
        <Routes>
          <Route path="/login" element={<Login onLogin={login} />} />
          <Route path="/registro" element={<Registro onLogin={login} />} />
          <Route path="/password-reset/:uid/:token" element={<ResetPassword />} />
          <Route path="/dashboard" element={protegida(<TableroSegunElRol onLogout={logout} />)} />
          <Route path="/profile" element={protegida(<Profile onLogout={logout} />)} />
          <Route path="/bitacora" element={protegida(<Bitacora onLogout={logout} />)} />
          <Route path="/bitacora/scan/:token" element={protegida(<CompleteDiveLog />)} />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
