# Pantalla del buzo y carga de estudios — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un buzo se registre con los datos del §5, se inscriba a una fecha de habilitación, suba cada estudio en su punto de la directiva con la imagen comprimida sin enterarse, y vea en una sola pantalla cuántos le faltan.

**Architecture:** El cálculo ya está construido y testeado: `api/fitness.diver_summary()` devuelve todo lo que la pantalla necesita. Este plan no lo recalcula en el cliente — agrega un endpoint que lo serializa (`GET /api/mi-estado/`) y una pantalla que lo muestra. La compresión ocurre dos veces, en el navegador para que la subida sea rápida con datos móviles y en el servidor porque al cliente no se le cree nada (§11). Los componentes quedan finos: la lógica decidible vive en el backend o en tres módulos puros de `frontend/src/lib/`, que son los únicos que llevan tests unitarios.

**Tech Stack:** Django 6.0.3 + DRF 3.16.1, `manage.py test` (el proyecto no usa pytest). Pillow 12.1.1 ya instalado; se agrega `pillow-heif`. React 19 + Vite 7 + Bootstrap 5, `react-hook-form` ya presente. Se agrega **vitest** para los tres módulos puros de `src/lib/`; las pantallas se verifican manejando la app real.

**Spec:** `docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md`

**Decisiones posteriores:** `docs/superpowers/specs/2026-11-03-decisiones-posteriores.md` (D-1 a D-6)

**Bocetos aprobados:** `docs/superpowers/specs/2026-11-03-bocetos/3-pantalla-buzo.html` es la referencia visual de este plan. **Abrirlo en el navegador antes de empezar.**

---

## Mapa de planes

Segundo de cuatro. El plan 1 está mergeado en `main` (merge `4c70bd1`).

| | Plan | Estado |
|---|---|---|
| 1 | Cimientos del dominio y cálculo de aptitud | **Hecho.** Catálogo, fechas, roles, motor de estados. 220 tests. |
| **2** | **Pantalla del buzo y carga de estudios** (este) | — |
| 3 | Circuito del médico y los enfermeros | Después. |
| 4 | Panel del admin, notificaciones y procesos programados | Después. |

**No hacen falta migraciones.** El plan 1 dejó el modelo completo: `UserProfile.dni` ya es único, `rank` ya tiene la lista cerrada del §5 como `choices`, y existen `birth_date`, `destination` y `habilitation_window`. Esos campos siguen siendo opcionales **en el modelo a propósito** — el admin crea al médico y a los enfermeros sin DNI ni fecha de nacimiento, y volverlos `NOT NULL` rompería eso. La obligatoriedad que pide el §5 es **del registro**, y va en el serializador (Tarea 5).

---

## Global Constraints

Valores textuales del spec. Son requisitos implícitos de todas las tareas.

- **Tono impersonal, sin tutear y sin dirigirse a la persona** (§10). Vocabulario fijo y literal en toda la aplicación: **Falta subir · En revisión · Revisados · Sin presentar · No corresponde · Vencido el … · Faltan N estudios**. No "Te faltan", no "Subí de nuevo", no "La doctora". Aplica a cada cadena que se vea en pantalla.
- **Fechas escritas en castellano**: "Vence el 12 de octubre de 2027". **No** "12/10/2027" ni "vigencia 365 días" (§8.3).
- **Los cuatro grupos de la pantalla del buzo, en este orden y con estos títulos exactos** (§8.3): **Falta subir** → **En revisión** → **Revisados** → **No corresponde**.
- **El buzo no elige el tipo de estudio de una lista.** Entra por el botón de ese estudio, así que el punto ya está determinado. Esto elimina el desplegable de ocho renglones de `Dashboard.jsx` y es el cambio que más errores de carga evita (§8.3).
- **La carga tiene exactamente dos campos** (§8.3): la **fecha que figura en el documento** (con la aclaración de que es la impresa en el estudio, no la de hoy) y el **archivo** (tomar foto o elegir archivo).
- **Compresión resultante** (§11): JPEG de **2.000 píxeles en el lado mayor, calidad 75, sin metadatos EXIF**. **Los PDF se dejan como están** — recomprimirlos arriesga que una radiografía quede ilegible.
- **El buzo no se entera de nada de la compresión. No hay ninguna opción ni ningún paso extra** (§11). Debajo del formulario, el aviso de que la imagen se reduce automáticamente y no hace falta hacer nada.
- **HEIC hay que soportarlo** (§11): los iPhone sacan fotos en HEIC y el servidor no sabe abrirlo. Se convierte a JPEG en el servidor.
- **Tope de tamaño con un mensaje claro y en castellano si se pasa** (§11).
- **La vigencia se evalúa contra el rango de la fecha de habilitación elegida, no contra hoy**, y el estudio tiene que estar vigente **todos los días del rango** (§4.1, §15.17).
- **Un buzo sin fecha elegida no siempre es un buzo que no hizo su parte** (§4.1, §15.21). La pantalla distingue "no eligió" de "no hay nada que elegir", y en el segundo caso **no se lo reprocha**.
- **Antes de su ventana, el Anexo 27 no se muestra como faltante** (§15.19): dice desde cuándo se puede presentar. La ventana es `end_date − 30 días` del rango elegido.
- **Lo que no corresponde se muestra igual, apagado y explicado** ("Se exige a partir de los 40 años de edad"). Si se escondiera, el que cumple 40 se encontraría de golpe con un estudio nuevo sin entender de dónde salió (§8.3).
- **El buzo puede reemplazar un estudio que está En revisión o Pre-revisado, no uno ya aprobado por el médico** (§15.10). Al reemplazar, vuelve a En revisión y el dictamen anterior queda en el historial.
- **El buzo puede cambiar la fecha elegida mientras esa fecha no haya pasado**, y cambiarla recalcula todos sus vencimientos, así que **la pantalla tiene que mostrar el efecto, no cambiarlo en silencio** (§15.18).
- **Ni la pantalla del buzo ni los correos nombran a quién rechazó** (§15.12). El motivo del rechazo se muestra textual, en la misma tarjeta donde está el botón para arreglarlo.
- **Datos del registro** (§5): grado, nombre, apellido, DNI, unidad, fecha de nacimiento, correo electrónico **pedido dos veces** (§15.11). **No se verifica la dirección**; la pantalla del buzo muestra siempre a qué dirección se mandan los avisos, con la opción de corregirla.
- **El grado es una lista cerrada**, en orden jerárquico y agrupada (§5). Oficiales: `GD GB CY CR TC MY CT TP TT ST`. Suboficiales: `SM SP SA SI SG CI CB`. Los valores ya están en `UserProfile.RANK_CHOICES`; **no se redefinen en el frontend**, se piden al backend.
- **"Unidad" se implementa sobre `UserProfile.destination`**, que ya existe (§15.5).
- **El rol es único y excluyente** (§15.20). El médico, los enfermeros y el admin **no presentan estudios**: la pantalla del buzo no es para ellos.
- **Una sola pantalla. Sin pestañas, sin "Mis estudios" contra "Compartidos", sin sección de permisos** (§8.3).
- **`Permission` no se elimina del modelo** (§5): se deja de usar y la pantalla sale de la navegación. Borrar el modelo es trabajo innecesario y riesgoso.
- **Un test que afirme un error tiene que afirmar también qué campo lo produjo**, no sólo el código de estado. Lo aprendimos en la Tarea 2: tres tests daban 400 por `title` obligatorio y no por la regla que decían probar, así que parecían probar algo y medían otra cosa. Un `assertEqual(status_code, 400)` no distingue de dónde vino el 400. Además, la Tarea 9 muestra "los errores del backend junto a su campo": si el error no viene atado a su campo, la pantalla no puede ubicarlo.

---

## Review Focus

Clases de entrada que el spec implica, que ninguna tarea exige por sí sola, y que van a lastimar a alguien si se rompen. Cada una tiene su test agregado a la tarea dueña del código.

1. **Foto HEIC de un iPhone.** El spec dice que "hoy no existe y va a morder". El buzo aprieta "tomar foto" y no tiene por qué saber qué formato usa su teléfono; si el servidor devuelve 500, pierde el estudio y no sabe por qué. *(Tarea 1)*
2. **Buzo sin fecha elegida porque la que le interesa no está publicada.** Es el caso real de quien espera la complementaria. Tratarlo igual que al que no eligió lo reprocha por algo que no hizo (§15.21). *(Tareas 4 y 7)*
3. **Anexo 27 fuera de su ventana.** Faltan once meses para que pueda presentarlo. Pintarlo de faltante lo entrena a ignorar el rojo justo en el punto que más importa (§15.19). *(Tareas 4 y 7)*
4. **Reemplazo de un estudio ya aprobado por el médico.** Permitirlo deja cambiar un documento a espaldas del médico, que en un registro médico militar es inaceptable (§15.10). *(Tarea 2)*
5. **Archivo que no es imagen ni PDF, o que pasa el tope.** Un `.docx`, un `.zip` o una foto de 12 MB con datos móviles. Tiene que salir un mensaje claro en castellano y no una traza de Pillow (§11). *(Tarea 1)*

---

## File Structure

**Backend** — nada de esto toca el motor de `api/fitness.py`, que ya está cerrado y testeado.

| Archivo | Responsabilidad |
|---|---|
| `backend/api/images.py` *(nuevo)* | Compresión del lado del servidor. Un solo punto de entrada. |
| `backend/api/estado.py` *(nuevo)* | Serializa el `DiverSummary` del motor a la forma que consume la pantalla. Aparte de `serializers.py`, que ya tiene 300 líneas y otra responsabilidad. |
| `backend/api/serializers.py` *(modificar)* | `StudyBlockSerializer`: `study_code` obligatorio al crear, reemplazo según §15.10. |
| `backend/api/views.py` *(modificar)* | `MiEstadoView`, inscripción a una fecha, compresión enganchada en la carga. |
| `backend/api/urls.py` *(modificar)* | Las rutas nuevas. |
| `backend/users/serializers.py` *(nuevo)* | Registro con los datos del §5. |
| `backend/requirements.txt` *(modificar)* | `pillow-heif`. |

**Frontend** — los tres módulos de `lib/` son los únicos con tests unitarios. Son puros: entra un dato, sale un dato, no tocan la red.

| Archivo | Responsabilidad |
|---|---|
| `frontend/src/lib/fecha-castellano.js` *(nuevo)* | Una fecha ISO a "12 de octubre de 2027". |
| `frontend/src/lib/agrupar-estudios.js` *(nuevo)* | Los ocho puntos a los cuatro grupos del §8.3, en orden. |
| `frontend/src/lib/comprimir-imagen.js` *(nuevo)* | Reducción en el navegador. PDF pasa de largo. |
| `frontend/src/components/PantallaBuzo.jsx` *(nuevo)* | La pantalla única del §8.3. |
| `frontend/src/components/CargarEstudio.jsx` *(nuevo)* | El formulario de dos campos. |
| `frontend/src/components/Registro.jsx` *(nuevo)* | El registro del §5. |
| `frontend/src/App.jsx` *(modificar)* | Rutas: entra `/registro`, sale `/permissions`. |
| `frontend/src/components/Permissions.jsx` *(borrar)* | Carry-forward de D-5: concede algo que ya nadie consulta. |
| `frontend/src/components/Dashboard.jsx` | **No se borra en este plan.** Tiene adentro la vista del médico que el plan 3 reemplaza. Deja de ser la pantalla del buzo, nada más. |
| `frontend/vitest.config.js` *(nuevo)*, `package.json` *(modificar)* | Infraestructura de tests. |

---

## Tarea 1: Compresión en el servidor

Primera porque todas las cargas pasan por acá y porque es la única pieza de este plan que es puro cálculo: se testea entera sin base de datos ni HTTP.

**Files:**
- Create: `backend/api/images.py`
- Create: `backend/api/tests/test_images.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces:
  - `MAX_UPLOAD_BYTES: int` — el tope, 12 MiB (`12 * 1024 * 1024`).
  - `LADO_MAYOR = 2000`, `CALIDAD = 75` — los valores del §11, como constantes nombradas.
  - `class ArchivoRechazado(Exception)` — con `.mensaje: str`, siempre en castellano e impersonal. La Tarea 2 la traduce a un 400.
  - `comprimir(archivo: UploadedFile) -> UploadedFile` — devuelve el archivo listo para guardar. Un PDF vuelve intacto. Una imagen vuelve como JPEG de `LADO_MAYOR` en el lado mayor, calidad `CALIDAD`, sin EXIF, con la extensión del nombre cambiada a `.jpg`. Cualquier otro tipo levanta `ArchivoRechazado`.

- [ ] **Step 1: Agregar `pillow-heif` y escribir los tests que fallan**

Agregar `pillow-heif` a `requirements.txt` e instalarlo en el venv.

En `test_images.py`, una clase por comportamiento. Los archivos de prueba se arman en memoria con Pillow; no se versionan binarios.

```python
class ReduceLasFotosDeCelularTests(SimpleTestCase):
    def test_una_foto_grande_sale_en_2000_pixeles_de_lado_mayor(self):
        # 4032x3024 es el tamaño real de una foto de celular
        salida = comprimir(_imagen(4032, 3024, 'JPEG'))
        self.assertEqual(max(Image.open(salida).size), 2000)

    def test_la_proporcion_no_se_deforma(self):
        ancho, alto = Image.open(comprimir(_imagen(4032, 3024, 'JPEG'))).size
        self.assertAlmostEqual(ancho / alto, 4032 / 3024, places=2)

    def test_una_foto_mas_chica_que_el_tope_no_se_agranda(self):
        self.assertEqual(Image.open(comprimir(_imagen(800, 600, 'JPEG'))).size, (800, 600))

    def test_sale_sin_metadatos_exif_de_la_camara(self):
        self.assertFalse(Image.open(comprimir(_imagen_con_exif(4032, 3024))).getexif())


class ElHeicDelIphoneSeConvierteTests(SimpleTestCase):
    # Review Focus 1
    def test_una_foto_heic_sale_como_jpeg(self):
        self.assertEqual(Image.open(comprimir(_imagen(4032, 3024, 'HEIF'))).format, 'JPEG')

    def test_el_nombre_pasa_a_jpg(self):
        salida = comprimir(_imagen(100, 100, 'HEIF', nombre='foto.heic'))
        self.assertTrue(salida.name.endswith('.jpg'))


class ElPdfNoSeTocaTests(SimpleTestCase):
    def test_un_pdf_vuelve_byte_a_byte_igual(self):
        entrada = _pdf()
        esperado = entrada.read()
        entrada.seek(0)
        self.assertEqual(comprimir(entrada).read(), esperado)


class LoQueNoSeAceptaTests(SimpleTestCase):
    # Review Focus 5
    def test_un_docx_se_rechaza_con_mensaje_en_castellano(self):
        with self.assertRaises(ArchivoRechazado) as cm:
            comprimir(_archivo(b'PK\x03\x04', 'informe.docx'))
        self.assertIn('imagen', cm.exception.mensaje.lower())

    def test_un_archivo_que_pasa_el_tope_se_rechaza_antes_de_abrirlo(self):
        with self.assertRaises(ArchivoRechazado):
            comprimir(_archivo(b'\xff\xd8' + b'x' * MAX_UPLOAD_BYTES, 'enorme.jpg'))

    def test_el_mensaje_del_tope_dice_el_limite(self):
        with self.assertRaises(ArchivoRechazado) as cm:
            comprimir(_archivo(b'\xff\xd8' + b'x' * MAX_UPLOAD_BYTES, 'e.jpg'))
        self.assertIn('12', cm.exception.mensaje)

    def test_un_jpg_mentido_que_no_es_imagen_se_rechaza_sin_traza_de_pillow(self):
        with self.assertRaises(ArchivoRechazado):
            comprimir(_archivo(b'no soy una imagen', 'mentira.jpg'))
```

El tipo se decide **por el contenido, no por la extensión** — de ahí el test del `.jpg` mentido.

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_images -v 2`

Expected: FAIL con `ImportError: cannot import name 'comprimir'`. Si alguno pasa, el test está mal escrito.

- [ ] **Step 3: Implementar `api/images.py`**

`pillow_heif.register_heif_opener()` a nivel de módulo, una sola vez. El tope se controla con `archivo.size` **antes** de abrir nada. `Image.open` dentro de `try`, y `OSError` / `UnidentifiedImageError` se traducen a `ArchivoRechazado`. Para descartar el EXIF, construir una imagen nueva y pegarle los píxeles en vez de confiar en que `save` lo omita. El PDF se reconoce por sus primeros bytes (`%PDF`) y se devuelve tal cual, con el puntero al inicio.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_images -v 2`

Expected: PASS, los 11.

- [ ] **Step 5: Control de mutación**

El defecto recurrente de este proyecto es el test que no puede fallar. Rompé a mano cada una de estas tres cosas, una por vez, y confirmá que un test se pone rojo; si alguna no rompe nada, falta el test.

- `LADO_MAYOR = 2000` → `3000`
- el chequeo de `MAX_UPLOAD_BYTES` → quitarlo
- el descarte del EXIF → quitarlo

- [ ] **Step 6: Commit**

```bash
git add backend/api/images.py backend/api/tests/test_images.py backend/requirements.txt
git commit -m "feat(api): comprimir las fotos en el servidor, con HEIC"
```

---

## Tarea 2: La carga entra en su punto de la directiva

**Files:**
- Modify: `backend/api/serializers.py` (`StudyBlockSerializer`, líneas 121-129)
- Modify: `backend/api/views.py` (`StudyBlockViewSet`, líneas 115-145)
- Modify: `backend/api/tests/test_study_block_api.py`

**Interfaces:**
- Consumes: `api.images.comprimir`, `api.images.ArchivoRechazado` (Tarea 1).
- Produces: `POST /api/blocks/` con `study_code`, `study_date` y `pdf_attachment`. `study_code` es **obligatorio** al crear. El `title` **no se acepta del cliente**: lo pone `StudyBlock.save()` desde el catálogo. Un reemplazo es un `POST` al mismo `study_code`, no un `PATCH`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class ElPuntoLoDecideElBotonTests(APITestCase):
    def test_crear_sin_study_code_da_400(self):
        # Hoy el modelo tiene default, así que esto pasa sin el arreglo
        r = _client(self.buzo).post('/api/blocks/',
                                    {'study_date': '2026-10-01', 'pdf_attachment': _pdf()})
        self.assertEqual(r.status_code, 400)
        self.assertIn('study_code', r.data)

    def test_el_title_que_manda_el_cliente_se_ignora(self):
        r = _client(self.buzo).post('/api/blocks/', {
            'study_code': 'c', 'study_date': '2026-10-01',
            'title': 'Electrocardiograma de esfuerzo', 'pdf_attachment': _pdf()})
        self.assertEqual(StudyBlock.objects.get(pk=r.data['id']).title,
                         'Electroencefalograma')


class LaFotoSeComprimeAlRecibirlaTests(APITestCase):
    def test_una_foto_grande_queda_guardada_en_2000_pixeles(self):
        r = _client(self.buzo).post('/api/blocks/', {
            'study_code': 'c', 'study_date': '2026-10-01',
            'pdf_attachment': _imagen(4032, 3024, 'JPEG')})
        bloque = StudyBlock.objects.get(pk=r.data['id'])
        self.assertEqual(max(Image.open(bloque.pdf_attachment).size), 2000)

    def test_un_archivo_rechazado_sale_como_400_y_no_como_500(self):
        # Review Focus 5
        r = _client(self.buzo).post('/api/blocks/', {
            'study_code': 'c', 'study_date': '2026-10-01',
            'pdf_attachment': _archivo(b'PK\x03\x04', 'informe.docx')})
        self.assertEqual(r.status_code, 400)


class ElReemplazoTests(APITestCase):
    # Review Focus 4
    def test_se_puede_reemplazar_un_estudio_en_revision(self):
        anterior = _estudio(self.buzo, 'c')            # sin dictamen
        self.assertEqual(_client(self.buzo).post('/api/blocks/', _carga('c')).status_code, 201)
        anterior.refresh_from_db()
        self.assertFalse(anterior.is_current)

    def test_se_puede_reemplazar_uno_pre_revisado(self):
        anterior = _estudio(self.buzo, 'c')
        _dictamen(anterior, self.enfermero, 'PRE_APPROVED')
        self.assertEqual(_client(self.buzo).post('/api/blocks/', _carga('c')).status_code, 201)

    def test_NO_se_puede_reemplazar_uno_aprobado_por_el_medico(self):
        anterior = _estudio(self.buzo, 'c')
        _dictamen(anterior, self.medico, 'APPROVED')
        self.assertEqual(_client(self.buzo).post('/api/blocks/', _carga('c')).status_code, 400)
        anterior.refresh_from_db()
        self.assertTrue(anterior.is_current)

    def test_el_estudio_aprobado_sigue_siendo_el_vigente_despues_del_rechazo(self):
        anterior = _estudio(self.buzo, 'c')
        _dictamen(anterior, self.medico, 'APPROVED')
        _client(self.buzo).post('/api/blocks/', _carga('c'))
        self.assertEqual(
            StudyBlock.objects.filter(user=self.buzo, study_code='c', is_current=True).count(), 1)

    def test_el_dictamen_anterior_queda_en_el_historial(self):
        anterior = _estudio(self.buzo, 'c')
        _dictamen(anterior, self.enfermero, 'PRE_APPROVED')
        _client(self.buzo).post('/api/blocks/', _carga('c'))
        self.assertTrue(Comment.objects.filter(block=anterior).exists())
```

El reemplazo se apoya en lo que ya hace `StudyBlock.save()`: baja el `is_current` del anterior del mismo punto. Lo que falta es **impedirlo cuando el anterior está aprobado por el médico**.

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_study_block_api -v 2`

Expected: FAIL. Cada uno por su propio motivo; el de `study_code` falla con 201 en lugar de 400, porque hoy el modelo tiene `default`.

- [ ] **Step 3: Implementar**

En `StudyBlockSerializer`: `title` pasa a `read_only_fields`, `study_code` se declara `required=True`, y `validate()` rechaza el reemplazo cuando el estudio vigente de ese punto tiene un `APPROVED` del médico como último dictamen. Para saberlo, reusar `api.fitness` en lugar de reimplementar la búsqueda del último dictamen.

En `StudyBlockViewSet.perform_create`: pasar el archivo por `images.comprimir` antes de guardar, y traducir `ArchivoRechazado` a `serializers.ValidationError({'pdf_attachment': e.mensaje})`.

- [ ] **Step 4: Correr la suite entera y verificar que pasa**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test`

Expected: PASS. **La suite completa, no sólo este archivo** — `study_code` pasando a obligatorio puede romper tests de otras tareas que lo omitían.

- [ ] **Step 5: Control de mutación**

Quitar la condición que impide reemplazar un estudio aprobado → `test_NO_se_puede_reemplazar_uno_aprobado_por_el_medico` tiene que ponerse rojo.

- [ ] **Step 6: Commit**

```bash
git add backend/api/serializers.py backend/api/views.py backend/api/tests/test_study_block_api.py
git commit -m "feat(api): el estudio entra en su punto y se comprime al recibirlo"
```

---

## Tarea 3: Inscripción a una fecha de habilitación

**Files:**
- Modify: `backend/api/views.py`, `backend/api/serializers.py`, `backend/api/urls.py`
- Create: `backend/api/tests/test_inscripcion_api.py`

**Interfaces:**
- Consumes: `HabilitationWindow` (plan 1), con `cycle`, `slot`, `start_date`, `end_date`, `anexo27_earliest_date`.
- Produces:
  - `GET /api/fechas/` — las fechas publicadas, ordenadas por `start_date`. Cada una con `id`, `slot`, `slot_display`, `start_date`, `end_date`, `ya_paso: bool`. Sólo lectura: cargarlas es del plan 4.
  - `PUT /api/mi-fecha/` con `{"window": <id>}` — inscribe o cambia. 400 si la fecha ya pasó. `{"window": null}` desinscribe.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class LasFechasPublicadasTests(APITestCase):
    def test_las_fechas_salen_ordenadas_por_inicio(self):
        _fecha(slot='SECOND', inicio='2026-12-10', fin='2026-12-12')
        _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        datos = _client(self.buzo).get('/api/fechas/').data
        self.assertEqual([f['slot'] for f in datos], ['FIRST', 'SECOND'])

    def test_un_ciclo_incompleto_devuelve_solo_las_que_existen(self):
        # 4.1: el ciclo incompleto es el estado normal
        _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        self.assertEqual(len(_client(self.buzo).get('/api/fechas/').data), 1)

    def test_una_fecha_que_ya_paso_viene_marcada(self):
        _fecha(slot='FIRST', inicio='2026-01-10', fin='2026-01-12')
        self.assertTrue(_client(self.buzo).get('/api/fechas/').data[0]['ya_paso'])


class InscribirseTests(APITestCase):
    def test_elegir_una_fecha_la_guarda_en_el_perfil(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        self.assertEqual(r.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.habilitation_window_id, futura.pk)

    def test_cambiarla_mientras_no_paso_se_permite(self):
        # 15.18
        primera = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        segunda = _fecha(slot='SECOND', inicio='2026-12-10', fin='2026-12-12')
        _client(self.buzo).put('/api/mi-fecha/', {'window': primera.pk})
        _client(self.buzo).put('/api/mi-fecha/', {'window': segunda.pk})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.habilitation_window_id, segunda.pk)

    def test_cambiar_a_una_fecha_que_ya_paso_da_400_por_la_fecha(self):
        pasada = _fecha(slot='FIRST', inicio='2026-01-10', fin='2026-01-12')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': pasada.pk})
        self.assertEqual(r.status_code, 400)
        # El error va atado a `window`, no suelto: un 400 generico no distingue
        # "esa fecha ya paso" de "ese id no existe", y la pantalla necesita
        # poder ubicar el mensaje junto al campo.
        self.assertIn('window', r.data)

    def test_desinscribirse_deja_el_perfil_sin_fecha(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        _client(self.buzo).put('/api/mi-fecha/', {'window': None})
        self.perfil.refresh_from_db()
        self.assertIsNone(self.perfil.habilitation_window_id)

    def test_el_buzo_no_puede_inscribir_a_otro(self):
        # 5: ve y gestiona lo suyo, nada mas. La vista actua sobre request.user,
        # asi que no hay id de perfil que mandar; este test fija esa forma.
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        self.perfil_del_otro.refresh_from_db()
        self.assertIsNone(self.perfil_del_otro.habilitation_window_id)
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_inscripcion_api -v 2`

Expected: FAIL con 404 en las rutas nuevas.

- [ ] **Step 3: Implementar**

`ya_paso` se calcula contra `date.today()` comparando con `end_date`: una fecha cuyo último día ya pasó no se puede elegir. `PUT /api/mi-fecha/` actúa siempre sobre `request.user.profile`, nunca sobre un id que venga del cliente — así el último test pasa por construcción y no por una comprobación aparte.

- [ ] **Step 4: Correr y verificar que pasan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_inscripcion_api -v 2`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api/views.py backend/api/serializers.py backend/api/urls.py backend/api/tests/test_inscripcion_api.py
git commit -m "feat(api): el buzo se inscribe a una fecha y la puede cambiar"
```

---

## Tarea 4: El endpoint del estado del buzo

Lo que la pantalla consume. No recalcula nada: serializa el `DiverSummary` que el plan 1 dejó testeado.

**Files:**
- Create: `backend/api/estado.py`
- Create: `backend/api/tests/test_estado_api.py`
- Modify: `backend/api/views.py`, `backend/api/urls.py`

**Interfaces:**
- Consumes: `api.fitness.diver_summary(profile, today) -> DiverSummary`, con `slots: tuple[SlotStatus, ...]`, `presented`, `approved`, `pending_review`, `pre_reviewed`, `problems`, `expired`, `rejected`, `state: DiverState`, `is_apto`; cada `SlotStatus` con `code`, `state: StudyState`, `block`, `last_dictamen`, `expires_on`. `api.catalog.get(code) -> RequiredStudy` con `.text`, `.validity_days`, `.min_age`, `.upload_hint`.
- Produces: `GET /api/mi-estado/`, un objeto con:
  - `fecha_elegida`: la fecha inscripta, o `null`. Cuando es `null`, `hay_fechas_para_elegir: bool` dice si **existe algo que elegir** — así la pantalla distingue "no eligió" de "no hay nada que elegir" (§15.21).
  - `faltan: int`, `revisados: int`, `total_exigidos: int` — para "Faltan N estudios" y "2 de 7 revisados".
  - `correo: str` — la dirección a la que van los avisos (§15.11).
  - `estudios`: los **ocho** puntos del catálogo en orden `a`–`h`, cada uno con `code`, `texto` (del catálogo), `estado` (el nombre del `StudyState`), `corresponde: bool`, `motivo_no_corresponde: str|None`, `vence_el: date|None`, `desde_cuando: date|None` (sólo el Anexo 27 antes de su ventana), `rechazo: {motivo, detalle}|None`, `puede_reemplazarse: bool`, `archivo: url|None`.
  - **No incluye `is_apto` ni quién dictaminó** (§15.12): el apto es del plan 3 y el nombre del revisor no se le muestra al buzo.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class ElEstadoDelBuzoTests(APITestCase):
    def test_devuelve_los_ocho_puntos_siempre(self):
        self.assertEqual([e['code'] for e in _get(self.buzo)['estudios']], list('abcdefgh'))

    def test_el_de_mas_de_40_tiene_los_ocho_exigidos(self):
        self.assertEqual(_get(self.mayor)['total_exigidos'], 8)

    def test_el_menor_de_40_tiene_siete(self):
        self.assertEqual(_get(self.menor)['total_exigidos'], 7)

    def test_el_punto_a_de_un_menor_de_40_viene_como_no_corresponde_y_explicado(self):
        # §8.3: se muestra igual, apagado y explicado
        punto_a = _punto(_get(self.menor), 'a')
        self.assertFalse(punto_a['corresponde'])
        self.assertIn('40', punto_a['motivo_no_corresponde'])

    def test_no_expone_el_apto_ni_quien_dictamino(self):
        # §15.12
        cuerpo = _get(self.buzo)
        self.assertNotIn('is_apto', cuerpo)
        self.assertNotIn('doctor', json.dumps(cuerpo))


class SinFechaElegidaTests(APITestCase):
    # Review Focus 2 — §15.21
    def test_sin_fecha_y_con_fechas_publicadas_marca_que_hay_para_elegir(self):
        _fecha(slot='FIRST')
        cuerpo = _get(self.sin_fecha)
        self.assertIsNone(cuerpo['fecha_elegida'])
        self.assertTrue(cuerpo['hay_fechas_para_elegir'])

    def test_sin_fecha_y_sin_fechas_publicadas_marca_que_no_hay_nada_que_elegir(self):
        HabilitationWindow.objects.all().delete()
        self.assertFalse(_get(self.sin_fecha)['hay_fechas_para_elegir'])

    def test_sin_fecha_no_revienta_por_None(self):
        self.assertEqual(_client(self.sin_fecha).get('/api/mi-estado/').status_code, 200)


class SinFechaDeNacimientoTests(APITestCase):
    # El motor tiene un DiverState.UNKNOWN_AGE, asi que el caso existe: el
    # registro de la Tarea 5 vuelve birth_date obligatorio, pero los perfiles
    # que ya estan en la base pueden no tenerla y la pantalla no puede caerse.
    def test_sin_birth_date_responde_200(self):
        self.perfil.birth_date = None
        self.perfil.save()
        self.assertEqual(_client(self.buzo).get('/api/mi-estado/').status_code, 200)

    def test_sin_birth_date_no_adivina_la_edad_ni_exige_el_punto_a(self):
        self.perfil.birth_date = None
        self.perfil.save()
        self.assertFalse(_punto(_get(self.buzo), 'a')['corresponde'])


class ElAnexo27AntesDeSuVentanaTests(APITestCase):
    # Review Focus 3 — §15.19
    def test_antes_de_la_ventana_no_sale_como_faltante(self):
        self.assertEqual(_punto(_get(self.buzo), 'h')['estado'], 'BEFORE_WINDOW')

    def test_antes_de_la_ventana_dice_desde_cuando(self):
        self.assertEqual(_punto(_get(self.buzo), 'h')['desde_cuando'],
                         str(self.fecha.end_date - timedelta(days=30)))


class ElRechazoSeMuestraTextualTests(APITestCase):
    def test_el_motivo_y_el_detalle_viajan_al_buzo(self):
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='ILLEGIBLE', content='La fotografia esta cortada.')
        rechazo = _punto(_get(self.buzo), 'c')['rechazo']
        self.assertEqual(rechazo['detalle'], 'La fotografia esta cortada.')
        self.assertIn('ilegible', rechazo['motivo'].lower())

    def test_el_rechazo_no_dice_quien_rechazo(self):
        # 15.12
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='ILLEGIBLE', content='Cortada.')
        self.assertNotIn(self.medico.last_name, json.dumps(_get(self.buzo)))


class SinConsultasDeMasTests(APITestCase):
    # §13
    def test_el_estado_no_hace_una_consulta_por_estudio(self):
        with CaptureQueriesContext(connection) as ctx:
            _get(self.buzo)
        self.assertLess(len(ctx.captured_queries), 12)
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_estado_api -v 2`

Expected: FAIL con 404.

- [ ] **Step 3: Implementar `api/estado.py` y la vista**

`estado.py` expone `armar_estado(profile, today) -> dict`. El `motivo_no_corresponde` sale de `catalog.get(code).min_age`: con `min_age` puesto, el texto es **"Se exige a partir de los 40 años de edad"** (literal del §8.3). `puede_reemplazarse` es la misma regla de la Tarea 2 — **importarla, no reescribirla**. Para el presupuesto de consultas, precargar los estudios con sus dictámenes antes de llamar al motor.

- [ ] **Step 4: Correr y verificar que pasan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_estado_api -v 2`

Expected: PASS.

- [ ] **Step 5: Control de mutación**

Cambiar `hay_fechas_para_elegir` por un `False` fijo → tiene que romper `test_sin_fecha_y_con_fechas_publicadas_marca_que_hay_para_elegir`.

- [ ] **Step 6: Commit**

```bash
git add backend/api/estado.py backend/api/tests/test_estado_api.py backend/api/views.py backend/api/urls.py
git commit -m "feat(api): endpoint del estado del buzo, sin exponer el apto"
```

---

## Tarea 5: Registro con los datos del §5

**Files:**
- Create: `backend/users/serializers.py`
- Create: `backend/users/tests/test_registro_api.py`
- Modify: `backend/core/settings.py` (`REST_AUTH['REGISTER_SERIALIZER']`)
- Modify: `backend/api/urls.py` (las rutas `/api/grados/` y `/api/mi-correo/`)

**Interfaces:**
- Consumes: `UserProfile.RANK_CHOICES` y `UserProfile.RANK_VALUES` (plan 1).
- Produces:
  - `POST /api/auth/registration/` pide, además de lo que ya pide dj-rest-auth: `first_name`, `last_name`, `dni`, `rank`, `destination`, `birth_date`. Todos obligatorios. El correo **se pide dos veces** y los dos tienen que coincidir.
  - `GET /api/grados/` — la lista cerrada del §5 agrupada, para que el desplegable **no** la redefina: `[{"grupo": "Oficiales", "grados": [{"valor": "GD", "etiqueta": "..."}, ...]}, ...]`, en el orden jerárquico del modelo.
  - `PUT /api/mi-correo/` con `{"email": "..."}` — corrige la dirección a la que van los avisos. **El §15.11 la exige**, y es lo único que repara un correo mal tipeado en el registro — que es el riesgo que ese mismo párrafo acepta a cambio de no poner un paso de verificación. El correo vive en `User`, no en `UserProfile`, y allauth guarda su propia copia en `EmailAddress`: hay que actualizar **las dos**, o el usuario queda sin poder entrar.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class LoQueElRegistroExigeTests(APITestCase):
    def test_un_registro_completo_se_acepta(self):
        # El positivo primero: sin esto los cuatro negativos de abajo pasarian
        # igual con un endpoint que rechaza todo.
        self.assertEqual(_registrar().status_code, 201)

    def test_sin_dni_da_400_por_ese_campo(self):
        r = _registrar(dni=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)

    def test_sin_grado_da_400_por_ese_campo(self):
        r = _registrar(rank=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('rank', r.data)

    def test_sin_fecha_de_nacimiento_da_400_por_ese_campo(self):
        r = _registrar(birth_date=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('birth_date', r.data)

    def test_sin_unidad_da_400_por_ese_campo(self):
        r = _registrar(destination=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('destination', r.data)


class ElDniNoSeRepiteTests(APITestCase):
    def test_un_dni_ya_registrado_da_400_y_no_un_500(self):
        # §5: es lo que hace viable el cotejo manual del admin
        _registrar(dni='30111222')
        r = _registrar(dni='30111222', email='otro@b.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)

    def test_el_dni_repetido_no_deja_un_usuario_huerfano(self):
        _registrar(dni='30111222')
        antes = User.objects.count()
        _registrar(dni='30111222', email='otro@b.com')
        self.assertEqual(User.objects.count(), antes)


class ElCorreoSePideDosVecesTests(APITestCase):
    # §15.11
    def test_si_los_dos_correos_no_coinciden_da_400_por_el_segundo(self):
        r = _registrar(email='a@b.com', email2='c@d.com')
        self.assertEqual(r.status_code, 400)
        # Atado a `email2` y no a `non_field_errors`: el §15.11 pide el correo
        # dos veces justamente para atajar el error de tipeo, y el que se
        # corrige es el segundo.
        self.assertIn('email2', r.data)

    def test_si_coinciden_se_registra(self):
        self.assertEqual(_registrar(email='a@b.com', email2='a@b.com').status_code, 201)


class ElGradoEsListaCerradaTests(APITestCase):
    def test_un_grado_inventado_da_400_por_el_grado(self):
        # "Sgto." es exactamente lo que el §5 quiere impedir: con 150 personas
        # escribiendo su propio grado convivirian "Sgto", "Sgto.", "Sargento"
        # y "SG" en la misma base.
        r = _registrar(rank='Sgto.')
        self.assertEqual(r.status_code, 400)
        self.assertIn('rank', r.data)

    def test_el_endpoint_de_grados_devuelve_los_dos_grupos_en_orden_jerarquico(self):
        grupos = _client(None).get('/api/grados/').data
        self.assertEqual([g['grupo'] for g in grupos], ['Oficiales', 'Suboficiales'])
        self.assertEqual([g['valor'] for g in grupos[0]['grados']][:3], ['GD', 'GB', 'CY'])


class CorregirElCorreoTests(APITestCase):
    # 15.11: la pantalla muestra a que direccion van los avisos, con la opcion
    # de corregirla. Sin esto, un correo mal tipeado no tiene arreglo y el buzo
    # no se entera de ningun rechazo.
    def test_cambiar_el_correo_lo_actualiza_en_el_usuario(self):
        _client(self.buzo).put('/api/mi-correo/', {'email': 'bien@b.com'})
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.email, 'bien@b.com')

    def test_cambiar_el_correo_lo_actualiza_tambien_en_allauth(self):
        # Si EmailAddress queda con el viejo, el login por correo deja de andar
        _client(self.buzo).put('/api/mi-correo/', {'email': 'bien@b.com'})
        self.assertTrue(
            EmailAddress.objects.filter(user=self.buzo, email='bien@b.com').exists())
        self.assertFalse(
            EmailAddress.objects.filter(user=self.buzo, email='mal@b.com').exists())

    def test_un_correo_ya_usado_por_otro_da_400_por_el_correo(self):
        r = _client(self.buzo).put('/api/mi-correo/', {'email': self.otro.email})
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)

    def test_el_buzo_no_puede_cambiar_el_correo_de_otro(self):
        # Actua siempre sobre request.user: no hay id que mandar
        _client(self.buzo).put('/api/mi-correo/', {'email': 'bien@b.com'})
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.email, 'otro@b.com')


class ElQueSeRegistraEsBuzoTests(APITestCase):
    def test_el_rol_sale_buzo_y_no_se_puede_pedir_otro(self):
        # §5 + D-5: el rol lo designa el admin. 'USER' es el valor real del rol
        # buzo en UserProfile.ROLE_CHOICES, y es el default del campo.
        _registrar(email='nuevo@b.com', role='DOCTOR')
        self.assertEqual(UserProfile.objects.get(user__email='nuevo@b.com').role, 'USER')
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test users.tests.test_registro_api -v 2`

Expected: FAIL — hoy el registro acepta sin esos campos.

- [ ] **Step 3: Implementar**

Heredar de `dj_rest_auth.registration.serializers.RegisterSerializer` y agregar los campos; el perfil se completa dentro de la **misma transacción** que el usuario, que es lo que hace pasar `test_el_dni_repetido_no_deja_un_usuario_huerfano`. El DNI duplicado se valida en el serializador — la restricción de la base sola saldría como 500. El `role` **no se declara como campo**, así que un cliente no puede pedirlo (D-5). El rol buzo es `'USER'` en `UserProfile.ROLE_CHOICES` y además el `default` del campo, así que el último test pasa sin código nuevo mientras `role` no sea un campo del serializador: es un test de regresión, no de implementación.

- [ ] **Step 4: Correr la suite entera y verificar que pasa**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/users/serializers.py backend/users/tests/ backend/core/settings.py backend/api/urls.py
git commit -m "feat(users): el registro pide los datos del parrafo 5 y el DNI no se repite"
```

---

## Tarea 6: Vitest y los tres módulos puros

**Files:**
- Create: `frontend/vitest.config.js`
- Modify: `frontend/package.json` (script `test`, devDependency `vitest`)
- Create: `frontend/src/lib/fecha-castellano.js` + `fecha-castellano.test.js`
- Create: `frontend/src/lib/agrupar-estudios.js` + `agrupar-estudios.test.js`
- Create: `frontend/src/lib/comprimir-imagen.js` + `comprimir-imagen.test.js`

**Interfaces:**
- Produces:
  - `enCastellano(iso: string|null) -> string` — `'2027-10-12'` a `'12 de octubre de 2027'`; cadena vacía con `null`.
  - `agrupar(estudios: Estudio[]) -> [{titulo: string, estudios: Estudio[]}]` — los cuatro grupos del §8.3, en orden, **siempre los cuatro**, aunque alguno quede vacío (la pantalla decide si lo dibuja). El mapa cubre los **nueve** estados de `StudyState`, sin excepción:

    | Grupo | Estados de `StudyState` |
    |---|---|
    | **Falta subir** | `MISSING`, `REJECTED`, `EXPIRED`, `DATE_INVALID`, `BEFORE_WINDOW` |
    | **En revisión** | `IN_REVIEW`, `PRE_REVIEWED` |
    | **Revisados** | `APPROVED` |
    | **No corresponde** | `NOT_REQUIRED` |

    `DATE_INVALID` acompaña a `EXPIRED` porque el motor ya los junta (`fitness.EXPIRED_STATES`): en los dos casos hay que subir de nuevo.

    **`BEFORE_WINDOW` va en "Falta subir", y eso no contradice al §15.19.** El motor lo cuenta como faltante (`fitness.INCOMPLETE_STATES = {MISSING, BEFORE_WINDOW}`), así que entra en el "Faltan N estudios" y tiene que estar en el grupo. Lo que el §15.19 prohíbe es **mostrarlo como faltante**: sin rojo y sin botón de subir, con "Se puede presentar a partir del …" en su lugar. Eso es presentación, y es la Tarea 7 la que lo hace (paso 1, punto 6).
  - `comprimirEnElNavegador(file: File) -> Promise<File>` — reduce a 2000 px de lado mayor, calidad 0.75. Un PDF vuelve sin tocar. **No valida ni rechaza**: eso es del servidor (Tarea 1), que es quien no puede ser engañado.

- [ ] **Step 1: Instalar vitest y escribir los tests que fallan**

`npm install -D vitest`, script `"test": "vitest run"`. Sin jsdom global: estos módulos no tocan el DOM, salvo `comprimir-imagen`, que declara su entorno en el propio archivo con `// @vitest-environment jsdom`.

```javascript
// fecha-castellano.test.js
it('escribe el mes con palabras, como pide el §8.3', () => {
  expect(enCastellano('2027-10-12')).toBe('12 de octubre de 2027');
});

it('no mete el cero adelante en los dias de un digito', () => {
  expect(enCastellano('2027-01-05')).toBe('5 de enero de 2027');
});

it('no se corre un dia por la zona horaria', () => {
  // Una fecha ISO suelta en new Date() se interpreta como UTC y en
  // Argentina (UTC-3) retrocede un dia. Es el error clasico.
  expect(enCastellano('2027-03-01')).toBe('1 de marzo de 2027');
});

it('devuelve cadena vacia con null, para que la pantalla no imprima "undefined"', () => {
  expect(enCastellano(null)).toBe('');
});

// agrupar-estudios.test.js
it('devuelve los cuatro grupos en el orden del §8.3', () => {
  expect(agrupar([]).map(g => g.titulo))
    .toEqual(['Falta subir', 'En revisión', 'Revisados', 'No corresponde']);
});

it('el vencido y el rechazado van a "Falta subir", porque hay algo que hacer', () => {
  const grupos = agrupar([{ code: 'b', estado: 'EXPIRED' }, { code: 'c', estado: 'REJECTED' }]);
  expect(grupos[0].estudios.map(e => e.code)).toEqual(['b', 'c']);
});

it('el BEFORE_WINDOW va en "Falta subir", porque el motor lo cuenta', () => {
  // El §15.19 le prohibe el rojo y el boton, no el grupo. Ver el mapa arriba.
  expect(agrupar([{ code: 'h', estado: 'BEFORE_WINDOW' }])[0].estudios.map(e => e.code))
    .toEqual(['h']);
});

it('no deja ningun estado afuera de los cuatro grupos', () => {
  // Si manana se agrega un StudyState, este test lo caza antes que un buzo
  const todos = ['NOT_REQUIRED', 'MISSING', 'BEFORE_WINDOW', 'IN_REVIEW', 'PRE_REVIEWED',
                 'APPROVED', 'REJECTED', 'EXPIRED', 'DATE_INVALID'];
  const agrupados = agrupar(todos.map((estado, i) => ({ code: String(i), estado })));
  expect(agrupados.flatMap(g => g.estudios).length).toBe(todos.length);
});

it('el que no corresponde va al cuarto grupo y no desaparece', () => {
  const grupos = agrupar([{ code: 'a', estado: 'NOT_REQUIRED' }]);
  expect(grupos[3].estudios.map(e => e.code)).toEqual(['a']);
});

// comprimir-imagen.test.js
it('reduce una imagen grande a 2000 px de lado mayor', async () => { /* ... */ });
it('deja un PDF intacto', async () => { /* ... */ });
it('devuelve un File, no un Blob, para que el nombre sobreviva', async () => { /* ... */ });
```

Los nueve nombres de estado del mapa están verificados contra `api/fitness.StudyState`. Si alguno no coincide, el que manda es `fitness.py`.

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd frontend && npm run test`

Expected: FAIL por módulos inexistentes.

- [ ] **Step 3: Implementar los tres módulos**

`enCastellano` se arma partiendo la cadena ISO a mano (`split('-')`) y **no** con `new Date(iso)`, que es lo que produce el corrimiento de zona horaria del tercer test. `agrupar` mapea los nombres de `StudyState` a los cuatro grupos; el mapa es la única pieza que decide algo, así que va explícito y no por heurística sobre el nombre del estado. `comprimirEnElNavegador` usa `createImageBitmap` más `OffscreenCanvas`, con respaldo a un `<canvas>`.

- [ ] **Step 4: Correr y verificar que pasan**

Run: `cd frontend && npm run test`

Expected: PASS.

- [ ] **Step 5: Control de mutación**

Cambiar el orden de los cuatro grupos → el primer test de `agrupar` se pone rojo. Cambiar `enCastellano` para que use `new Date(iso)` → el test de la zona horaria se pone rojo.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.js frontend/src/lib/
git commit -m "feat(front): vitest y los tres modulos puros de la pantalla del buzo"
```

---

## Tarea 7: La pantalla del buzo

La que más cuidado necesita. Mobile-first. `3-pantalla-buzo.html` es la referencia visual: **abrirlo antes de escribir el componente.**

**Files:**
- Create: `frontend/src/components/PantallaBuzo.jsx`
- Modify: `frontend/src/App.jsx` (ruta `/dashboard` para el buzo)

**Interfaces:**
- Consumes: `GET /api/mi-estado/`, `GET /api/fechas/`, `PUT /api/mi-fecha/` (Tareas 3 y 4); `enCastellano`, `agrupar` (Tarea 6).
- Produces: la pantalla. El botón de cada estudio de "Falta subir" abre `CargarEstudio` (Tarea 8) con el `code` ya determinado.

- [ ] **Step 1: Construir la pantalla**

De arriba a abajo, en este orden, que es el del §8.3:

1. **La fecha de habilitación, primero.** A qué fecha está inscripto, con la opción de cambiarla. Si no eligió y `hay_fechas_para_elegir` es `true`, elegir es **la acción principal de la pantalla, por encima de los estudios**. Si es `false`, el texto dice que la fecha todavía no se publicó y **no lo reprocha** (§15.21). Cambiarla **muestra el efecto** sobre los vencimientos, no lo cambia en silencio (§15.18).
2. **"Faltan N estudios", en grande.** Al llegar a cero, el bloque pasa a verde.
3. **Barra de progreso** con "2 de 7 revisados".
4. **Los cuatro grupos** de `agrupar()`, con los títulos exactos.
5. En "Falta subir", **un botón grande por estudio**. El motivo del rechazo, **textual**, en la misma tarjeta que el botón para arreglarlo.
6. El Anexo 27 antes de su ventana dice **desde cuándo** se puede presentar, en castellano.
7. Lo que no corresponde, **apagado y con su explicación**.
8. **El correo al que van los avisos**, con la opción de corregirlo, contra `PUT /api/mi-correo/` (§15.11).

Sin pestañas, sin "Compartidos conmigo", sin permisos.

- [ ] **Step 2: Verificar en la app real**

Arrancar backend y frontend y recorrerla con los usuarios sembrados, que cubren los casos de borde a propósito. **Mirar las capturas, no sólo el DOM.**

| Usuario sembrado | Qué tiene que mostrar |
|---|---|
| `apto` | Los siete en "Revisados", bloque en verde, "Faltan 0 estudios" |
| `cumple40` | El punto `a` **exigido**, ocho en total |
| `mayor` | Igual, con los ocho |
| un menor de 40 | El punto `a` en "No corresponde", apagado, con "Se exige a partir de los 40 años de edad" |
| `vencido` | El vencido en "Falta subir", con su fecha en castellano |
| `rechazo` | El motivo textual junto al botón, **sin nombrar a quién rechazó** |
| `preaprobado` | En "En revisión", reemplazable |
| `enrevision` | En "En revisión" |
| un buzo sin fecha | Elegir fecha como acción principal |
| sin fechas cargadas | El texto que dice que todavía no se publicó, sin reproche |

**En viewport de celular**, que es la situación real de uso.

> **No correr `create_test_data.py` sin motivo.** `backend/db.sqlite3` está sembrada y el script **borra** los usuarios de su lista con todo lo asociado. Si hace falta resembrar, el comando exacto está en el docstring del script y necesita `SEED_CONFIRM=1`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PantallaBuzo.jsx frontend/src/App.jsx
git commit -m "feat(front): la pantalla unica del buzo"
```

---

## Tarea 8: La carga de un estudio

**Files:**
- Create: `frontend/src/components/CargarEstudio.jsx`

**Interfaces:**
- Consumes: `comprimirEnElNavegador` (Tarea 6), `POST /api/blocks/` (Tarea 2), `react-hook-form` (ya instalado).
- Produces: el formulario. Recibe el `code` por prop — **no hay desplegable de tipo de estudio**.

- [ ] **Step 1: Construir el formulario**

Dos campos y nada más:

1. **Fecha que figura en el documento**, con la aclaración literal de que es la fecha impresa en el estudio y no la de hoy.
2. **Archivo**: `<input type="file" accept="image/*,.pdf,.heic" capture="environment">`, que en el celular ofrece la cámara.

Arriba, el nombre del estudio que se está cargando, tomado del `texto` que vino en `/api/mi-estado/`. Debajo, el aviso de que la imagen se reduce automáticamente y no hace falta hacer nada. El `upload_hint` del catálogo se muestra cuando el punto lo tiene (`d` y `f` lo tienen).

El archivo pasa por `comprimirEnElNavegador` antes de enviarse. El 400 del servidor se muestra tal cual: el mensaje ya viene en castellano e impersonal de la Tarea 1.

- [ ] **Step 2: Verificar en la app real**

Subir una foto grande y confirmar en el servidor que quedó en 2000 px. Subir un `.docx` y confirmar que sale el mensaje en castellano y no una traza. Subir un PDF y confirmar que no se tocó. Reemplazar un estudio en revisión y confirmar que vuelve a "En revisión". Confirmar que sobre uno aprobado la pantalla no ofrece el botón.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CargarEstudio.jsx
git commit -m "feat(front): carga de un estudio, dos campos y el punto ya determinado"
```

---

## Tarea 9: Registro y salida de la pantalla de permisos

**Files:**
- Create: `frontend/src/components/Registro.jsx`
- Modify: `frontend/src/App.jsx`
- Delete: `frontend/src/components/Permissions.jsx`

**Interfaces:**
- Consumes: `POST /api/auth/registration/` y `GET /api/grados/` (Tarea 5).

- [ ] **Step 1: Construir el registro**

Los campos del §5: grado (desplegable **agrupado** en Oficiales y Suboficiales, con los valores que trae `/api/grados/` — **no** redefinidos en el frontend), nombre, apellido, DNI, unidad, fecha de nacimiento, correo **dos veces**, contraseña. Los errores del backend se muestran junto a su campo.

- [ ] **Step 2: Sacar Permisos de la navegación y borrar el componente**

Carry-forward de D-5: la pantalla y su ruta en `App.jsx:43` conceden algo que ya nadie consulta, porque el acceso sale del rol. **El modelo `Permission` no se toca** (§5): sólo se va la pantalla.

Buscar referencias antes de borrar:

```bash
cd frontend && grep -rn "Permissions\|/permissions" src/
```

- [ ] **Step 3: Verificar en la app real**

Registrar un usuario nuevo de punta a punta y confirmar que entra a la pantalla del buzo con rol buzo. Probar un DNI repetido y ver el error junto al campo. Probar dos correos distintos. Confirmar que `/permissions` ya no existe y que ninguna pantalla la linkea.

- [ ] **Step 4: Correr todo**

```bash
cd backend && ./venv/Scripts/python.exe manage.py test
cd ../frontend && npm run test && npm run lint && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Registro.jsx frontend/src/App.jsx
git rm frontend/src/components/Permissions.jsx
git commit -m "feat(front): registro del parrafo 5 y sale la pantalla de permisos"
```

---

## Lo que este plan NO hace

Para que nadie lo busque acá:

- **La pantalla del médico y la de los enfermeros** (§8.1, §8.2) son del plan 3. `Dashboard.jsx` queda en pie justamente por eso.
- **El panel del admin** (§8.5), **cargar fechas de habilitación**, **los tres correos** (§9) y **la limpieza por retención** (§12) son del plan 4. Mientras tanto las fechas se cargan desde el admin de Django, que el plan 1 dejó registrado a propósito (D-1).
- **`access_level` sigue mintiendo piadosamente** su nombre: dice "puede dictaminar". Reemplazarlo por uno honesto es carry-forward del plan 3 (D-5).
- **El listado de 150 buzos del §8.1 no tiene vía de datos** todavía. Es carry-forward del plan 3 (D-5).
