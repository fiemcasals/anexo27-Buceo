// Cómo se nombra a una persona en todas las pantallas: "grado Nombre APELLIDO".
// Sin grado se omite el grado; sin nada cargado devuelve la cadena vacía (cada
// pantalla decide qué mostrar en ese caso).
export function nombreConGrado({ grado, nombre, apellido } = {}) {
  return [grado, nombre, apellido ? apellido.toLocaleUpperCase('es-AR') : '']
    .map(parte => (parte || '').trim())
    .filter(Boolean)
    .join(' ')
}
