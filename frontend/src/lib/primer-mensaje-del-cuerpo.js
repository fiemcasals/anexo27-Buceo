// El primer mensaje legible de un cuerpo de error de DRF, para cuando ningún
// campo conocido del formulario lo recibe. Prefiere `non_field_errors` y
// `detail`; si no están, toma el primero de los demás campos. Devuelve '' si el
// cuerpo no trae ningún texto.
function primerTexto(valor) {
  if (typeof valor === 'string') return valor.trim()
  if (Array.isArray(valor)) {
    for (const item of valor) {
      const texto = primerTexto(item)
      if (texto) return texto
    }
    return ''
  }
  if (valor && typeof valor === 'object') {
    for (const item of Object.values(valor)) {
      const texto = primerTexto(item)
      if (texto) return texto
    }
  }
  return ''
}

export function primerMensajeDelCuerpo(cuerpo) {
  if (!cuerpo || typeof cuerpo !== 'object') return ''
  return primerTexto(cuerpo.non_field_errors) || primerTexto(cuerpo.detail) || primerTexto(cuerpo)
}
