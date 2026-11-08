// La pastilla de color de las dos pantallas del revisor: un estado, un conteo,
// un rótulo. El tono lo decide quien la usa (`ok`, `aviso`, `peligro`,
// `neutro`, `apagado`); los colores son los de los bocetos aprobados.

const TONOS = {
  ok: { background: 'var(--ok-fondo)', color: 'var(--ok)' },
  aviso: { background: 'var(--aviso-fondo)', color: 'var(--aviso-texto)' },
  info: { background: 'var(--info-fondo)', color: 'var(--info)' },
  peligro: { background: 'var(--peligro-fondo)', color: 'var(--peligro-texto)' },
  neutro: { background: 'var(--superficie-2)', color: 'var(--texto-suave)' },
  apagado: { background: 'var(--superficie-2)', color: 'var(--texto-suave)' },
};

const Pastilla = ({ tono = 'neutro', children, titulo }) => (
  <span
    title={titulo}
    style={{
      ...(TONOS[tono] || TONOS.neutro),
      borderRadius: '999px',
      padding: '4px 11px',
      fontSize: '11.5px',
      fontWeight: 600,
      whiteSpace: 'nowrap',
      display: 'inline-block',
    }}
  >
    {children}
  </span>
);

export default Pastilla;
