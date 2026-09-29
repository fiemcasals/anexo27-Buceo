import React from 'react';
import { Link } from 'react-router-dom';

// ponytail: "Bitácora de Buceo" oculta a pedido. Para reactivarla, descomentar su item.
const ITEMS = [
  { to: '/dashboard', icon: 'grid', label: 'Dashboard' },
  { to: '/profile', icon: 'person-circle', label: 'Mi Perfil' },
  { to: '/permissions', icon: 'shield-lock', label: 'Permisos' },
  // { to: '/bitacora', icon: 'book', label: 'Bitácora de Buceo' },
  { to: '/admin', icon: 'sliders', label: 'Administración', adminOnly: true },
];

const closeMenu = () => {
  const toggle = document.getElementById('menu-toggle');
  if (toggle) toggle.checked = false;
};

const Sidebar = ({ active, onLogout, isSuperUser }) => (
  <div className="sidebar p-4 d-flex flex-column">
    <div className="d-flex align-items-center mb-5 ps-2">
      <div className="bg-white rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '35px', height: '35px' }}>
        <i className="bi bi-water text-primary fs-5"></i>
      </div>
      <h4 className="m-0 fw-bold">Anexo Buceo</h4>
    </div>

    <nav className="nav flex-column gap-2 flex-grow-1">
      {ITEMS.filter(i => !i.adminOnly || isSuperUser).map(i => (
        <Link key={i.to} to={i.to} onClick={closeMenu}
              className={`nav-link d-flex align-items-center ${active === i.to ? 'active' : ''}`}>
          <i className={`bi bi-${i.icon} me-3`}></i>
          <span>{i.label}</span>
        </Link>
      ))}
    </nav>

    <div className="mt-auto">
      <button className="btn btn-outline-light w-100 d-flex align-items-center justify-content-center gap-2 py-2 opacity-75 border-0"
              onClick={onLogout}>
        <i className="bi bi-box-arrow-left"></i><span>Cerrar Sesión</span>
      </button>
    </div>
  </div>
);

export default Sidebar;
