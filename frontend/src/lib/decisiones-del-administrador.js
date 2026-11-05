// Las decisiones de las que cuelga la pantalla del administrador.
//
// Viven acá y no dentro del componente por lo que costó el plan 2: su defecto
// más grave fue una decisión de presentación —un recuadro verde que decía "no
// falta nada" cuando faltaba todo— que ningún test podía cazar porque estaba
// enterrada en el JSX. Lo que decide qué ve una persona se prueba.

// Los tres lugares del ciclo, en el orden del ciclo. Los nombres son los del
// modelo (`HabilitationWindow.SLOT_CHOICES`); las etiquetas en castellano las
// manda el servidor, así que no se duplican acá.
import { aTexto } from './fecha-dd-mm-yyyy'

export const LUGARES = ['FIRST', 'SECOND', 'COMPLEMENTARY']

/** Cómo se muestra una fecha del ciclo, o que todavía no se cargó.
 *
 * "Sin cargar" tiene que leerse distinto de una fecha: un ciclo incompleto es
 * el estado normal, así que esto se ve todos los días.
 *
 * La cadena se parte en lugar de construir un `Date` a propósito. Un
 * `new Date('2026-11-18')` se interpreta como medianoche UTC, y al mostrarlo en
 * Buenos Aires (UTC−3) retrocede un día: el administrador carga el 18 y la
 * pantalla le dice 17.
 */
export function textoDeFecha(fecha) {
  if (!fecha) return 'Sin cargar'
  return aTexto(fecha)
}

/** La gente designada en un rol, y si no hay nadie.
 *
 * `vacia` existe para que la pantalla pueda decirlo con palabras. Una fila en
 * blanco es indistinguible de una lista que no cargó, y el administrador
 * concluiría que ya designó al enfermero.
 */
export function filaDeRol(designados, rol) {
  const gente = (designados && designados[rol]) || []
  return { gente, vacia: gente.length === 0 }
}

/** El cuerpo del PUT: sólo los lugares que cambiaron, o `null` si no cambió nada.
 *
 * Dos reglas, y las dos tienen consecuencias:
 *
 * Un input vaciado **no se manda**. En blanco significa "todavía no la cargué",
 * no "borrala": borrar una fecha desinscribe a todos los buzos anotados en
 * ella, y eso no puede ser el efecto de seleccionar el contenido y apretar
 * backspace.
 *
 * Sin cambios devuelve `null`. Un PUT sin ninguna fecha da 400, así que mandarlo
 * le mostraría un error rojo a quien no tocó nada.
 */
export function loQueSeManda(ciclo, editado, original) {
  const cuerpo = { cycle: ciclo }
  let hayAlgo = false

  for (const lugar of LUGARES) {
    const nuevo = editado[lugar]
    if (!nuevo) continue
    if (nuevo === (original[lugar] || '')) continue
    cuerpo[lugar] = nuevo
    hayAlgo = true
  }

  return hayAlgo ? cuerpo : null
}
