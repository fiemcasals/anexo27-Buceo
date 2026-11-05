import { useState, useRef } from 'react';
import { aTexto, aIso, enmascarar } from '../lib/fecha-dd-mm-yyyy';

// Un campo de fecha que se escribe y se lee en dd/mm/yyyy.
//
// Reemplaza a `<input type="date">`, que el navegador dibuja con **su** idioma
// y no con el de la página: con Chrome en inglés muestra mm/dd/yyyy, y no hay
// atributo ni CSS que lo cambie. La única forma de fijar el formato es poner un
// campo de texto propio.
//
// Al lado queda un botón que abre el calendario nativo. No se saca, porque en
// el celular el selector nativo es una rueda y tipear ocho dígitos ahí es peor
// —y el campo donde más importa es la fecha del estudio, que es justo donde el
// §8.3 previó que la gente iba a tipear 2027 por 2026.
//
// Hacia afuera habla ISO: `value` e `onChange` usan 'aaaa-mm-dd', como la API.
// Mientras la fecha está incompleta, `onChange` recibe '' y no una fecha a
// medias, así que nunca se manda algo como '2026-11-' al servidor.

// Si el navegador puede abrir el calendario del sistema a pedido. Es una
// propiedad del entorno y no un estado, así que se resuelve una sola vez al
// cargar el módulo: ponerlo en `useState` dentro de un efecto provoca un
// segundo render por cada campo y React lo marca como error.
const HAY_CALENDARIO = typeof HTMLInputElement !== 'undefined'
  && typeof HTMLInputElement.prototype.showPicker === 'function';

const CampoFecha = ({
  id,
  value,
  onChange,
  className = '',
  error = null,
  min,
  max,
  required = false,
  ...resto
}) => {
  const [tocado, setTocado] = useState(false);
  const nativo = useRef(null);

  // El texto es estado local porque lo que se tipea pasa por formas que no son
  // una fecha todavía ('18/1'), y eso no se puede guardar en `value`, que habla
  // ISO. Pero cuando el valor cambia desde afuera —lo trajo el servidor— el
  // texto tiene que seguirlo.
  //
  // El ajuste se hace **durante el render** y no en un `useEffect`: es el
  // patrón que React recomienda para corregir estado cuando cambia una prop,
  // porque vuelve a renderizar antes de pintar, sin el parpadeo ni el render en
  // cascada que provoca el efecto. `ultimoIso` es lo último que vimos, así que
  // el eco de lo que acabamos de emitir no pisa lo que se está escribiendo.
  const [estado, setEstado] = useState(
    () => ({ texto: aTexto(value), ultimoIso: value || null }));

  let texto = estado.texto;
  const entrante = value || null;
  if (entrante !== estado.ultimoIso) {
    texto = aTexto(value);
    setEstado({ texto, ultimoIso: entrante });
  }

  const emitir = (iso, visible) => {
    setEstado({ texto: visible, ultimoIso: iso || null });
    onChange(iso || '');
  };

  const alTipear = (e) => {
    const visible = enmascarar(e.target.value);
    emitir(aIso(visible) || '', visible);
  };

  const abrirCalendario = () => {
    if (!nativo.current) return;
    try {
      nativo.current.showPicker();
    } catch {
      // Algunos navegadores lo rechazan si no viene de un gesto directo. No
      // se avisa nada: el campo de texto sigue andando, que es lo principal.
    }
  };

  const desdeCalendario = (e) => {
    const iso = e.target.value;
    emitir(iso, aTexto(iso));
  };

  // El aviso aparece sólo cuando lo escrito ya está completo —diez caracteres—
  // o cuando se salió del campo. Mostrarlo en el tercer dígito lo pintaría de
  // rojo a cualquiera que esté tipeando bien.
  const roto = texto !== '' && aIso(texto) === null;
  const propio = roto && (texto.length === 10 || tocado)
    ? 'Esa fecha no existe. Escribila como dd/mm/aaaa.'
    : null;
  const aMostrar = error || propio;

  return (
    <>
      <div className="input-group">
        <input
          type="text"
          id={id}
          className={`form-control${aMostrar ? ' is-invalid' : ''} ${className}`}
          placeholder="dd/mm/aaaa"
          value={texto}
          onChange={alTipear}
          onBlur={() => setTocado(true)}
          // `inputMode` saca el teclado numérico en el celular; `type` sigue
          // siendo text para que el formato lo decidamos nosotros.
          inputMode="numeric"
          autoComplete="off"
          maxLength={10}
          required={required}
          aria-describedby={aMostrar ? `${id}-error` : undefined}
          {...resto}
        />
        {HAY_CALENDARIO && (
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={abrirCalendario}
            aria-label="Abrir el calendario"
            title="Abrir el calendario"
          >
            <i className="bi bi-calendar3"></i>
          </button>
        )}
      </div>

      {/* El selector nativo, sin ocupar lugar: sólo se usa para abrir el
          calendario del sistema. `tabIndex={-1}` lo saca del recorrido con
          Tab, así que no hay dos paradas para el mismo dato. */}
      <input
        ref={nativo}
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        value={aIso(texto) || ''}
        onChange={desdeCalendario}
        min={min}
        max={max}
        style={{
          position: 'absolute', width: 1, height: 1,
          opacity: 0, pointerEvents: 'none', border: 0, padding: 0,
        }}
      />

      {aMostrar && (
        <div id={`${id}-error`} className="invalid-feedback d-block">
          {aMostrar}
        </div>
      )}
    </>
  );
};

export default CampoFecha;
