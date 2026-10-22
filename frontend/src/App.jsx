import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import Dashboard from './components/Dashboard';
import Profile from './components/Profile';
import Login from './components/Login';
import Permissions from './components/Permissions';
import Admin from './components/Admin';
import ResetPassword from './components/ResetPassword';
import Bitacora from './components/Bitacora';
import CompleteDiveLog from './components/CompleteDiveLog';
import Support from './components/Support';
import Terms from './components/Terms';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const login = () => setIsAuthenticated(true);
  const logout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  const guarded = (element) =>
    isAuthenticated ? <Terms onLogout={logout}>{element}</Terms> : <Navigate to="/login" />;

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
          <Route path="/password-reset/:uid/:token" element={<ResetPassword />} />
          <Route 
            path="/dashboard" 
            element={guarded(<Dashboard onLogout={logout} />)} 
          />
          <Route 
            path="/profile" 
            element={guarded(<Profile onLogout={logout} />)} 
          />
          <Route 
            path="/permissions" 
            element={guarded(<Permissions onLogout={logout} />)} 
          />
          <Route 
            path="/soporte" 
            element={guarded(<Support onLogout={logout} />)} 
          />
          <Route 
            path="/admin" 
            element={guarded(<Admin onLogout={logout} />)} 
          />
          {/* Bitácora oculta de la navegación; las rutas quedan activas para reactivarla */}
          <Route 
            path="/bitacora" 
            element={guarded(<Bitacora onLogout={logout} />)} 
          />
          <Route 
            path="/bitacora/scan/:token" 
            element={guarded(<CompleteDiveLog />)} 
          />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
