// La pastilla de color de las dos pantallas del revisor: un estado, un conteo,
// un rótulo. El tono lo decide quien la usa (`ok`, `aviso`, `peligro`,
// `neutro`, `apagado`); los colores son los de los bocetos aprobados.

const TONOS = {
  ok: { background: '#eaf7ee', color: '#1d7a3d' },
  aviso: { background: '#fff6e5', color: '#9a6508' },
  peligro: { background: '#fdecec', color: '#a52a2a' },
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
