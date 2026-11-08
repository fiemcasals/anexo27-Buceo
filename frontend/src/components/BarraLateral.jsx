import { Link, useLocation } from 'react-router-dom';

// La barra lateral, una sola vez.
//
// Antes la dibujaba cada pantalla por su cuenta —cinco copias— y cada una le
// ponía distinto nombre al mismo enlace: "Dashboard" en tres, "Estudios
// médicos" en la del buzo, "Permisos" en la del administrador. Al navegar, el
// nombre cambiaba delante de la persona, porque recién al llegar se dibujaba la
// barra de la pantalla nueva.
//
// Ahora el rótulo sale del rol y es el mismo antes y después de navegar.

// Qué es `/dashboard` para cada rol. Es su pantalla de trabajo, y el nombre la
// nombra: el buzo presenta estudios, el administrador reparte permisos, el
// médico y el enfermero revisan.
const PANTALLA_PRINCIPAL = {
  USER: { texto: 'Estudios médicos', icono: 'bi-clipboard2-pulse' },
  ADMIN: { texto: 'Permisos', imagen: '/logo-buzos.png' },
  // El médico y el enfermero trabajan en el listado del plantel, que tiene su
  // propia ruta: ahí es donde el enlace tiene que quedar marcado, también al
  // abrir la ficha de un buzo (`/plantel/:id`).
  DOCTOR: { texto: 'Estudios médicos', icono: 'bi-clipboard2-pulse', ruta: '/plantel' },
  NURSE: { texto: 'Estudios médicos', icono: 'bi-clipboard2-pulse', ruta: '/plantel' },
};

const POR_DEFECTO = { texto: 'Estudios médicos', icono: 'bi-clipboard2-pulse' };

function cerrarElMenu() {
  const t = document.getElementById('menu-toggle');
  if (t) t.checked = false;
}

const BarraLateral = ({ role, onLogout }) => {
  const { pathname } = useLocation();
  // Un rol que no conocemos cae en el rótulo neutro en lugar de dejar el
  // enlace sin nombre. Es la misma decisión que con los estados de un estudio:
  // algo desconocido no puede dejar la pantalla rota.
  const principal = PANTALLA_PRINCIPAL[role] || POR_DEFECTO;

  const rutaPrincipal = principal.ruta || '/dashboard';
  const enLaPrincipal = pathname === rutaPrincipal || pathname.startsWith(`${rutaPrincipal}/`);

  const clase = (ruta) =>
    `nav-link d-flex align-items-center${pathname === ruta ? ' active' : ''}`;

  return (
    <div className="sidebar p-4 d-flex flex-column">
      <div className="d-flex align-items-center mb-5 ps-2">
        <img src="/logo-buzos.png" alt="" width="34" height="42" className="me-2"
             style={{ objectFit: 'contain' }} />
        <h4 className="m-0 fw-bold" style={{ fontSize: '1.05rem', lineHeight: 1.25 }}>Div Ec Capac Anf</h4>
      </div>

      <nav className="nav flex-column gap-2 flex-grow-1">
        <Link to={rutaPrincipal}
              className={`nav-link d-flex align-items-center${enLaPrincipal ? ' active' : ''}`}
              onClick={cerrarElMenu}>
          {principal.imagen
            ? <img src={principal.imagen} alt="" width="20" height="20" className="me-3" style={{ objectFit: "contain" }} />
            : <i className={`bi ${principal.icono} me-3`}></i>}
          <span>{principal.texto}</span>
        </Link>
        {role === 'ADMIN' && (
          <Link to="/usuarios" className={clase('/usuarios')} onClick={cerrarElMenu}>
            <i className="bi bi-people me-3"></i>
            <span>Usuarios</span>
          </Link>
        )}
        <Link to="/profile" className={clase('/profile')} onClick={cerrarElMenu}>
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
  );
};

export default BarraLateral;
