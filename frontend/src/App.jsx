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
import CompleteDiveLog from './components/CompleteDiveLog';

// El rol decide qué pantalla es `/dashboard`. El buzo —rol `USER`— ve la
// pantalla del §8.3; el médico, el enfermero y el administrador siguen viendo
// `Dashboard`, que es su herramienta de trabajo y que este plan no reemplaza.
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
  return <Dashboard onLogout={onLogout} />;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const login = () => setIsAuthenticated(true);
  const logout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

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
          <Route 
            path="/dashboard" 
            element={isAuthenticated ? <TableroSegunElRol onLogout={logout} /> : <Navigate to="/login" />}
          />
          <Route 
            path="/profile" 
            element={isAuthenticated ? <Profile onLogout={logout} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/bitacora" 
            element={isAuthenticated ? <Bitacora onLogout={logout} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/bitacora/scan/:token" 
            element={isAuthenticated ? <CompleteDiveLog /> : <Navigate to="/login" />} 
          />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
