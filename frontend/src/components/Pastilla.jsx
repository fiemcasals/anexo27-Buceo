// La pastilla de color de las dos pantallas del revisor: un estado, un conteo,
// un rótulo. El tono lo decide quien la usa (`ok`, `aviso`, `peligro`,
// `neutro`, `apagado`); los colores son los de los bocetos aprobados.

const TONOS = {
  ok: { background: '#E8F3EE', color: '#24745B' },
  aviso: { background: '#FFF4DF', color: '#8A5A12' },
  peligro: { background: '#FFF0ED', color: '#9F3D3D' },
  neutro: { background: '#f2f4f8', color: '#5b6684' },
  apagado: { background: '#f2f4f8', color: '#9aa3b8' },
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
