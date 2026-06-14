import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import Dashboard from './components/Dashboard';
import Profile from './components/Profile';
import Login from './components/Login';
import Permissions from './components/Permissions';
import ResetPassword from './components/ResetPassword';
import Bitacora from './components/Bitacora';
import CompleteDiveLog from './components/CompleteDiveLog';

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
          <Route path="/password-reset/:uid/:token" element={<ResetPassword />} />
          <Route 
            path="/dashboard" 
            element={isAuthenticated ? <Dashboard onLogout={logout} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/profile" 
            element={isAuthenticated ? <Profile onLogout={logout} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/permissions" 
            element={isAuthenticated ? <Permissions onLogout={logout} /> : <Navigate to="/login" />} 
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
