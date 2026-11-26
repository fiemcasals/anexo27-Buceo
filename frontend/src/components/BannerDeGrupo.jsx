import { useState } from 'react';

const ORO = '#D4AF37';

// El emblema es opcional: se busca /emblemas/<grupo>.svg, y si no está, .png; si
// tampoco, el banner se ve igual, sin imagen.
function Emblema({ codigo }) {
  const [formato, setFormato] = useState('svg');
  if (formato === null) return null;
  return (
    <img src={`/emblemas/${codigo.toLowerCase()}.${formato}`} alt="" height="46"
         onError={() => setFormato(formato === 'svg' ? 'png' : null)}
         style={{ flex: '0 0 auto', height: '46px', width: 'auto', maxWidth: '64px', objectFit: 'contain' }} />
  );
}

/** El grupo del buzo en mayúsculas doradas sobre su color, y la estrella de campeón. */
export default function BannerDeGrupo({ grupo, campeon }) {
  if (!grupo) return null;
  return (
    <div className="d-flex align-items-center gap-2 gap-sm-3 rounded-3 px-3 py-2 mb-3"
         style={{ background: grupo.color, color: ORO, maxWidth: '100%', overflow: 'hidden' }}
         role="img" aria-label={`Grupo ${grupo.nombre}${campeon ? `, campeón ${campeon.anio}` : ''}`}>
      <Emblema codigo={grupo.codigo} />
      <div className="fw-bold text-uppercase flex-grow-1 text-truncate"
           style={{ minWidth: 0, fontSize: 'clamp(13px, 4.4vw, 17px)', letterSpacing: 'clamp(1px, 0.7vw, 3px)' }}>
        {grupo.nombre}
      </div>
      {campeon && (
        <div className="d-flex align-items-center gap-1 text-nowrap"
             title={`Grupo campeón ${campeon.anio}`}
             style={{ fontSize: '11.5px', letterSpacing: '1px', fontWeight: 600 }}>
          <i className="bi bi-star-fill" style={{ fontSize: '17px' }}></i>
          <span className="d-none d-sm-inline">CAMPEÓN {campeon.anio}</span>
        </div>
      )}
    </div>
  );
}
