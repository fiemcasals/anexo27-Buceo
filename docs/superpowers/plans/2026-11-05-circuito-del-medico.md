# Circuito del médico y los enfermeros — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el médico y los enfermeros auxiliares revisen los estudios de las 150 personas del plantel desde dos pantallas —un listado con buscador, filtros y contadores, y una ficha por buzo— sin que el navegador se baje el plantel entero, y que el buzo reciba un correo cuando le rechazan un estudio.

**Architecture:** Un endpoint nuevo devuelve una fila por buzo, ya contada y paginada. Los conteos salen de `fitness.diver_summary`, que es la única implementación de la regla: no se reimplementa nada en SQL. El plantel se baja con el `prefetch_related` que `fitness.py` ya trae escrito —unas tres consultas— y el buscador, los filtros, el orden y la paginación se resuelven en Python sobre esas 150 filas. El frontend reemplaza `Dashboard.jsx` por dos pantallas nuevas que piden sólo lo que muestran.

**Tech Stack:** Django 6.0.3, DRF 3.16.1, SQLite, React 19, Vite 7, Bootstrap 5, vitest.

**Spec:** `docs/superpowers/specs/2026-11-05-circuito-del-medico-design.md`, que a su vez argumenta desde `docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md`. **Los dos se leen.**

## Global Constraints

- Sin dependencias nuevas. Backend Django 6.0.3 + DRF 3.16.1 sobre SQLite; frontend React 19 + Vite 7 + Bootstrap 5.
- **`fitness.diver_summary` es la única implementación de la regla.** Ningún conteo, vigencia, estado ni "último dictamen" se reimplementa con `annotate`, `Subquery` ni SQL crudo. Una optimización que duplique la regla es un defecto, no una mejora.
- El plantel se baja con el `select_related`/`prefetch_related` que `api/fitness.py:26-38` trae escrito en su docstring. Copiarlo, no inventar otro.
- Todos los textos de interfaz **en impersonal** (§10 del spec viejo). Nada de "tu", "tus", "podés".
- Las fechas que una persona escribe o lee van en **dd/mm/aaaa**, con el componente `frontend/src/components/CampoFecha.jsx` y la biblioteca `frontend/src/lib/fecha-dd-mm-yyyy.js`.
- Tests de frontend: sólo lógica pura en `frontend/src/lib/*.test.js`, que es lo que `frontend/vitest.config.js` recoge. No existe `@testing-library` y agregarlo viola la restricción de dependencias. Las pantallas se verifican corriendo la aplicación.
- **No correr `migrate` ni `create_test_data.py` contra `backend/db.sqlite3`**, que está sembrada y en uso. Los tests usan su propia base.
- `core.autocrlf=true`: el árbol de trabajo tiene CRLF. Un reemplazo por script tiene que detectar el fin de línea del archivo.
- Correr la suite entera (`python manage.py test` y `npm run test`) antes de cada commit, no sólo el test de la tarea.

## Review Focus

Entradas que el diseño implica y que ninguna tarea ejercitaría si nadie las nombra. Cada una tiene su test asignado a la tarea que la posee.

1. **Un buzo sin turno** (`DiverState.NO_WINDOW`): `required_codes` devuelve vacío y todos los conteos dan cero. La fila no puede mostrar "0/0" si subió ocho estudios. → Tarea 2.
2. **Un buzo sin fecha de nacimiento** (`UNKNOWN_AGE`): no se sabe si le tocan siete u ocho. → Tarea 2.
3. **Un buzo con un vencido y un rechazado a la vez**: la precedencia de `DiverState` lo manda a `REJECTED`, así que desaparece del contador de vencidos. → Tarea 3.
4. **El buzo de 40 años justos** medido contra el año del turno y no contra hoy: es el límite donde el denominador salta de 7 a 8. → Tarea 2.
5. **Un rechazo sin motivo ni detalle**: hoy pasa el serializador y revienta contra la `CheckConstraint` con un 500. Es el POST exacto del diálogo que esta plan construye. → Tarea 6.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `backend/api/plantel.py` *(nuevo)* | Arma la fila de cada buzo a partir de `diver_summary`, y aplica búsqueda, filtros, orden y paginación en memoria. Sin Django REST adentro: funciones puras sobre una lista. |
| `backend/api/views.py` | `PlantelView`: baja el plantel con el prefetch, llama a `plantel.py`, serializa. |
| `backend/api/serializers.py` | `CommentSerializer.validate`: exigir motivo y detalle en un rechazo. |
| `backend/api/correo.py` *(nuevo)* | Arma y manda el correo de rechazo. Un fallo no propaga. |
| `frontend/src/lib/plantel.js` *(nuevo)* | Lectura y escritura de los filtros en la query string. Lógica pura, con tests. |
| `frontend/src/components/ListadoPlantel.jsx` *(nuevo)* | §8.1. |
| `frontend/src/components/FichaBuzo.jsx` *(nuevo)* | §8.2. |
| `frontend/src/App.jsx` | Rutas nuevas y el fallback que deja de ser `Dashboard`. |

Se borran: `backend/api/report_pdf.py`, `api/tests/test_report_pdf.py`, `api/tests/test_anexo27_api.py`, `Anexo27View`, su ruta, y `frontend/src/components/Dashboard.jsx`.

---

## Task 1: Sacar el generador de Anexo 27

Primero porque despeja el terreno: `Dashboard.jsx` se borra en la tarea 8 y esto quita su única dependencia de backend viva.

**Files:**
- Delete: `backend/api/report_pdf.py`, `backend/api/tests/test_report_pdf.py`, `backend/api/tests/test_anexo27_api.py`
- Modify: `backend/api/views.py` (quitar `Anexo27View` y el import `from .report_pdf import generate_anexo_27`), `backend/api/urls.py` (quitar `Anexo27View` del import y su `router.register`)

**Interfaces:**
- Produces: nada. Deja de existir la ruta `anexo27/`.

- [ ] **Step 1: Borrar los tres archivos y las referencias**

El Anexo 27 es un documento que el buzo sube ya firmado (punto h de la directiva); el sistema no lo emite.

- [ ] **Step 2: Verificar que no quedó ninguna referencia**

Run: `grep -rn "anexo27\|report_pdf\|Anexo27View" backend/ --include=*.py | grep -v venv`
Expected: sin resultados.

- [ ] **Step 3: Correr la suite**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test`
Expected: OK, con menos tests que antes (se fueron los de `report_pdf` y `anexo27_api`).

- [ ] **Step 4: Commit**

---

## Task 2: La fila de un buzo

El corazón. Convierte un `UserProfile` en la fila que el listado muestra, y resuelve acá los tres casos límite del Review Focus.

**Files:**
- Create: `backend/api/plantel.py`
- Test: `backend/api/tests/test_plantel.py`

**Interfaces:**
- Consumes: `fitness.diver_summary(profile, today) -> DiverSummary` con `presented, approved, pending_review, pre_reviewed, problems, expired, rejected, last_doctor_review, required_codes, slots`; `fitness.DiverState`; `UserProfile.habilitation_window`, `.dni`, `.birth_date`, `.role`.
- Produces: `fila(profile, today) -> dict` con exactamente estas claves: `id`, `grado`, `apellido`, `nombre`, `unidad`, `dni`, `edad`, `turno`, `presentados`, `exigidos`, `a_revisar`, `sin_tocar`, `pre_revisados`, `vencidos`, `rechazados`, `ultima_revision`, `estado`, `subida_mas_vieja_sin_dictamen`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class FilaDeUnBuzoTests(TestCase):
    def test_el_denominador_sale_de_la_edad_contra_el_año_del_turno(self):
        # 39 años hoy pero 40 en el año del turno: le corresponden ocho.
        fila = plantel.fila(self.perfil_que_cumple_40_en_el_ciclo, self.hoy)
        self.assertEqual(fila['exigidos'], 8)
        self.assertEqual(fila['edad'], 40)

    def test_a_revisar_suma_lo_sin_tocar_y_lo_pre_revisado(self):
        fila = plantel.fila(self.perfil_con_1_sin_tocar_y_1_pre_revisado, self.hoy)
        self.assertEqual(fila['a_revisar'], 2)
        self.assertEqual(fila['sin_tocar'], 1)
        self.assertEqual(fila['pre_revisados'], 1)

    def test_sin_turno_no_dice_cero_sobre_cero(self):
        # Subió los ocho pero no se inscribió: el exigido no se puede determinar.
        fila = plantel.fila(self.perfil_sin_turno_con_8_subidos, self.hoy)
        self.assertEqual(fila['presentados'], 8)
        self.assertIsNone(fila['exigidos'])
        self.assertIsNone(fila['turno'])
        self.assertIsNone(fila['edad'])
        self.assertEqual(fila['estado'], 'NO_WINDOW')

    def test_sin_fecha_de_nacimiento_el_exigido_queda_sin_determinar(self):
        fila = plantel.fila(self.perfil_sin_birth_date, self.hoy)
        self.assertIsNone(fila['exigidos'])
        self.assertEqual(fila['estado'], 'UNKNOWN_AGE')

    def test_la_ultima_revision_cuenta_solo_dictamenes_del_medico(self):
        # Un enfermero pre-aprobó hoy; el médico no miró nunca.
        fila = plantel.fila(self.perfil_solo_pre_revisado, self.hoy)
        self.assertIsNone(fila['ultima_revision'])

    def test_la_subida_mas_vieja_mira_solo_lo_que_no_tiene_dictamen(self):
        # Un estudio viejo ya dictaminado no puede encabezar la pila cruda.
        fila = plantel.fila(self.perfil_con_viejo_dictaminado_y_nuevo_sin_tocar, self.hoy)
        self.assertEqual(fila['subida_mas_vieja_sin_dictamen'],
                         self.bloque_nuevo_sin_dictamen.created_at)
```

`presentados` sale de `DiverSummary.presented`; `exigidos` es `len(required_codes)` **o `None`** cuando no hay turno o no hay edad —ahí está la diferencia con el cero que mentiría—; `a_revisar` es `pending_review + pre_reviewed`; `edad` es la edad de la regla, no la de hoy.

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_plantel -v 2`
Expected: FAIL, `module 'api.plantel' has no attribute 'fila'`.

- [ ] **Step 3: Escribir `fila(profile: UserProfile, today: date) -> dict` en `backend/api/plantel.py`**

No consulta la base: lee del perfil ya prefetcheado, igual que `fitness`. `subida_mas_vieja_sin_dictamen` recorre los `slots` de `DiverSummary` quedándose con los de estado `IN_REVIEW` o `PRE_REVIEWED` y toma el `block.created_at` más chico; `None` si no hay ninguno.

- [ ] **Step 4: Correr y ver que pasan**

- [ ] **Step 5: Commit**

---

## Task 3: Buscar, filtrar, ordenar y contar

Todo en memoria sobre la lista de filas. Sin Django adentro: son funciones sobre listas de diccionarios, así que los tests son baratos y exhaustivos.

**Files:**
- Modify: `backend/api/plantel.py`
- Test: `backend/api/tests/test_plantel.py`

**Interfaces:**
- Consumes: `fila()` de la tarea 2.
- Produces:
  - `buscar(filas, texto) -> list[dict]`
  - `filtrar(filas, *, filtro=None, turno=None) -> list[dict]` — `filtro` en `('todos', 'completa', 'incompleta', 'pendientes')`; `turno` es el id de una `HabilitationWindow`, o el literal `'sin'` para los no inscriptos.
  - `contar(filas) -> dict` con `aptos`, `a_revisar`, `vencidos`, y `por_filtro` con los cuatro conteos.
  - `ordenar(filas, criterio) -> list[dict]` — criterios: `'apellido'`, `'ultima_revision'`, `'pendientes'`, `'pila_rapida'`, `'pila_cruda'`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class BuscarTests(TestCase):
    def test_busca_por_apellido_nombre_dni_y_grado_en_un_solo_campo(self):
        for texto in ('gomez', 'María', '12.345.675', 'Cabo'):
            self.assertIn(self.fila_gomez, plantel.buscar(self.filas, texto))

    def test_ignora_mayusculas_acentos_y_puntos_del_dni(self):
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, 'GOMEZ'))
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, 'gómez'))
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, '12345675'))


class FiltrarTests(TestCase):
    def test_documentacion_completa_no_mira_el_dictamen(self):
        # Spec §8.1: un rechazado cuenta como completo, el papel está presentado.
        completas = plantel.filtrar(self.filas, filtro='completa')
        self.assertIn(self.fila_con_todo_subido_y_uno_rechazado, completas)

    def test_sin_turno_se_filtra_con_el_literal_sin(self):
        self.assertEqual(plantel.filtrar(self.filas, turno='sin'),
                         [self.fila_sin_turno])

    def test_el_de_exigidos_desconocido_no_cuenta_como_completo(self):
        self.assertNotIn(self.fila_sin_turno,
                         plantel.filtrar(self.filas, filtro='completa'))


class ContarTests(TestCase):
    def test_cuenta_buzos_y_no_estudios(self):
        # Tres buzos con pendientes, que entre todos suman seis estudios.
        self.assertEqual(plantel.contar(self.filas)['a_revisar'], 3)

    def test_un_buzo_cae_en_un_solo_contador(self):
        # Con un vencido y un rechazado, DiverState lo manda a REJECTED:
        # sale de "vencidos" y no hay doble conteo.
        c = plantel.contar([self.fila_con_vencido_y_rechazado])
        self.assertEqual(c['vencidos'], 0)

    def test_contar_sobre_lo_filtrado_da_lo_filtrado(self):
        del_turno = plantel.filtrar(self.filas, turno=self.turno_1ra.pk)
        self.assertEqual(plantel.contar(del_turno)['aptos'], 1)
        self.assertEqual(plantel.contar(self.filas)['aptos'], 2)


class OrdenarTests(TestCase):
    def test_pila_rapida_pone_primero_lo_pre_revisado(self):
        primera = plantel.ordenar(self.filas, 'pila_rapida')[0]
        self.assertGreater(primera['pre_revisados'], 0)

    def test_pila_cruda_pone_primero_la_subida_mas_vieja_sin_dictamen(self):
        primera = plantel.ordenar(self.filas, 'pila_cruda')[0]
        self.assertEqual(primera, self.fila_con_la_subida_mas_vieja)

    def test_los_que_no_tienen_nada_esperando_van_al_fondo_en_pila_cruda(self):
        self.assertEqual(plantel.ordenar(self.filas, 'pila_cruda')[-1],
                         self.fila_sin_nada_pendiente)
```

- [ ] **Step 2: Correr y ver que fallan**

- [ ] **Step 3: Implementar las cuatro funciones**

`contar` cuenta buzos: `aptos` son los de estado `APTO`, `vencidos` los de `EXPIRED`, `a_revisar` los que tienen `a_revisar > 0`. Para la búsqueda sin acentos, `unicodedata.normalize('NFKD', ...)`; del DNI se quitan puntos y espacios en los dos lados de la comparación.

- [ ] **Step 4: Correr y ver que pasan**

- [ ] **Step 5: Commit**

---

## Task 4: El endpoint

**Files:**
- Modify: `backend/api/views.py`, `backend/api/urls.py`
- Test: `backend/api/tests/test_plantel_api.py` *(nuevo)*

**Interfaces:**
- Consumes: todo `plantel.py`.
- Produces: `GET /api/plantel/` con `?buscar=`, `?filtro=`, `?turno=`, `?orden=`, `?pagina=`. Devuelve `{'contadores': {...}, 'total': int, 'pagina': int, 'paginas': int, 'filas': [...]}`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class SoloLosRevisoresEntranTests(APITestCase):
    def test_el_buzo_recibe_403(self):
        self.client.force_authenticate(self.buzo)
        self.assertEqual(self.client.get('/api/plantel/').status_code, 403)

    def test_el_medico_y_el_enfermero_entran(self):
        for u in (self.medico, self.enfermero):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get('/api/plantel/').status_code, 200)


class ElPlantelSonLosBuzosTests(APITestCase):
    def test_el_medico_y_el_admin_no_figuran_en_el_plantel(self):
        # Spec §5: no aparecen en "Personal a controlar".
        ids = [f['id'] for f in self.get_filas()]
        self.assertNotIn(self.medico.profile.pk, ids)
        self.assertNotIn(self.admin.profile.pk, ids)


class NoHayNMasUnoTests(APITestCase):
    def test_el_plantel_entero_cuesta_un_numero_fijo_y_chico_de_consultas(self):
        # Es el test que impide que una "optimización" con annotate pase
        # inadvertida, y el que detecta que alguien rompió el prefetch.
        self.crear_buzos(5)
        with self.assertNumQueries(self.CONSULTAS) as _:
            self.client.get('/api/plantel/')
        self.crear_buzos(20)
        with self.assertNumQueries(self.CONSULTAS):
            self.client.get('/api/plantel/')


class ElListadoYLaFichaDicenLoMismoTests(APITestCase):
    def test_cada_fila_coincide_con_diver_summary_de_ese_buzo(self):
        for f in self.get_filas():
            resumen = fitness.diver_summary(
                UserProfile.objects.get(pk=f['id']), self.hoy)
            self.assertEqual(f['presentados'], resumen.presented)
            self.assertEqual(f['a_revisar'],
                             resumen.pending_review + resumen.pre_reviewed)
            self.assertEqual(f['rechazados'], resumen.rejected)
            self.assertEqual(f['vencidos'], resumen.expired)
```

El conjunto de `ElListadoYLaFichaDicenLoMismoTests` tiene que incluir los cinco casos del Review Focus: sin turno, sin fecha de nacimiento, 40 justos, vencido+rechazado, y sin nada subido.

- [ ] **Step 2: Correr y ver que fallan**

- [ ] **Step 3: Implementar `PlantelView(APIView)` y la permiso `EsRevisor`**

`EsRevisor` usa `roles.es_revisor(perfil)`, igual que `EsElAdministrador` en `views.py`. El queryset es `UserProfile.objects.filter(role='USER')` con el `select_related`/`prefetch_related` **copiado del docstring de `api/fitness.py`**. La paginación es propia, de a 50: DRF no tiene `DEFAULT_PAGINATION_CLASS`.

- [ ] **Step 4: Correr y ver que pasan**

- [ ] **Step 5: Commit**

---

## Task 5: Revertir una aprobación

**Files:**
- Modify: `backend/api/serializers.py`, `backend/api/views.py`
- Test: `backend/api/tests/test_dictamen.py`

**Interfaces:**
- Produces: el médico puede llevar a `IN_REVIEW` un punto que él aprobó.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_el_medico_revierte_su_propia_aprobacion(self):
    # Sin esto una aprobación equivocada deja al buzo apto hasta que venza:
    # el buzo no puede reemplazar lo aprobado y la ficha no ofrece acciones.
    r = self.revertir(self.medico, self.aprobacion_del_medico)
    self.assertEqual(r.status_code, 200)
    self.assertEqual(self.estado_del_punto(), StudyState.IN_REVIEW)

def test_queda_asentado_quien_revirtio_y_cuando(self):
    self.revertir(self.medico, self.aprobacion_del_medico)
    ultimo = self.dictamenes_del_punto().last()
    self.assertEqual(ultimo.doctor, self.medico)
    self.assertIsNotNone(ultimo.created_at)

def test_el_enfermero_no_revierte_una_aprobacion_del_medico(self):
    self.assertEqual(self.revertir(self.enfermero, self.aprobacion_del_medico)
                     .status_code, 403)

def test_otro_medico_no_revierte_lo_que_no_aprobo(self):
    self.assertEqual(self.revertir(self.otro_medico, self.aprobacion_del_medico)
                     .status_code, 403)
```

- [ ] **Step 2: Correr y ver que fallan**

- [ ] **Step 3: Implementar**

Reusar `SoloQuienDictamino` (`views.py:197-228`), que ya restringe al autor.

- [ ] **Step 4: Correr y ver que pasan** · **Step 5: Commit**

---

## Task 6: El rechazo exige motivo, y manda el correo

Las dos cosas van juntas: son el mismo POST.

**Files:**
- Modify: `backend/api/serializers.py` (`CommentSerializer.validate`), `backend/api/views.py`
- Create: `backend/api/correo.py`
- Test: `backend/api/tests/test_comment_api.py`, `backend/api/tests/test_correo.py` *(nuevo)*

**Interfaces:**
- Produces: `correo.avisar_rechazo(comment) -> bool` — `True` si salió. No propaga excepciones.

- [ ] **Step 1: Escribir los tests que fallan**

```python
class UnRechazoExigeMotivoYDetalleTests(APITestCase):
    def test_rechazar_sin_motivo_da_400_y_no_500(self):
        # Hoy pasa el serializador y revienta contra la CheckConstraint
        # `rejection_has_reason_and_detail` como IntegrityError. Es el POST
        # exacto que manda el diálogo de rechazo.
        r = self.post(status='REJECTED', rejection_reason='', content='')
        self.assertEqual(r.status_code, 400)
        self.assertIn('rejection_reason', r.data)

    def test_rechazar_sin_detalle_da_400(self):
        r = self.post(status='REJECTED', rejection_reason='ILLEGIBLE', content='')
        self.assertEqual(r.status_code, 400)

    def test_una_aprobacion_no_lleva_motivo(self):
        r = self.post(status='APPROVED', rejection_reason='ILLEGIBLE')
        self.assertEqual(r.status_code, 400)


class ElCorreoDeRechazoTests(APITestCase):
    def test_un_rechazo_manda_un_correo_al_buzo(self):
        self.rechazar()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.buzo.email])

    def test_dice_que_estudio_el_motivo_y_el_detalle(self):
        self.rechazar(rejection_reason='ILLEGIBLE', content='Salió cortada.')
        cuerpo = mail.outbox[0].body
        self.assertIn('Documento ilegible', cuerpo)
        self.assertIn('Salió cortada.', cuerpo)
        self.assertIn(self.titulo_del_estudio, cuerpo)

    def test_una_aprobacion_no_manda_nada(self):
        self.aprobar()
        self.assertEqual(len(mail.outbox), 0)

    def test_el_rechazo_del_enfermero_tambien_avisa(self):
        self.rechazar(como=self.enfermero)
        self.assertEqual(len(mail.outbox), 1)

    def test_si_el_correo_falla_el_rechazo_se_guarda_igual(self):
        # El dictamen es lo importante: un servidor de correo caído no puede
        # impedir que el médico trabaje.
        with mock.patch('api.correo.send_mail', side_effect=SMTPException):
            r = self.rechazar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.dictamenes_del_punto().count(), 1)

    def test_el_texto_va_en_impersonal(self):
        self.rechazar()
        for palabra in (' tu ', ' tus ', 'podés', 'tenés'):
            self.assertNotIn(palabra, mail.outbox[0].body)
```

- [ ] **Step 2: Correr y ver que fallan**

- [ ] **Step 3: Implementar**

El enganche va en `perform_create` de la vista de dictámenes, **no en una señal ni en `Model.save()`**: una señal dispararía también desde el admin de Django y desde los scripts de siembra. Un `PATCH` que convierte un dictamen en rechazo avisa igual; uno que sólo corrige el detalle de un rechazo ya avisado, no.

- [ ] **Step 4: Correr y ver que pasan** · **Step 5: Commit**

---

## Task 7: Los filtros viven en la dirección de la página

**Files:**
- Create: `frontend/src/lib/plantel.js`, `frontend/src/lib/plantel.test.js`

**Interfaces:**
- Produces: `leerFiltros(search) -> {buscar, filtro, turno, orden, pagina}` y `escribirFiltros(filtros) -> string`.

- [ ] **Step 1: Escribir los tests que fallan**

```js
it('una dirección vacía da los valores de arranque', () => {
  expect(leerFiltros('')).toEqual(
    { buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 1 })
})

it('ida y vuelta: lo que escribe vuelve igual', () => {
  const f = { buscar: 'gómez', filtro: 'pendientes', turno: 3, orden: 'apellido', pagina: 2 }
  expect(leerFiltros(escribirFiltros(f))).toEqual(f)
})

it('no escribe lo que está en su valor de arranque, para no ensuciar la dirección', () => {
  expect(escribirFiltros({ buscar: '', filtro: 'todos', turno: null, orden: null, pagina: 1 }))
    .toBe('')
})

it('una página o un filtro inventados caen en el valor de arranque', () => {
  expect(leerFiltros('?pagina=cero&filtro=inventado'))
    .toMatchObject({ pagina: 1, filtro: 'todos' })
})

it('el turno "sin" sobrevive, que no es un número', () => {
  expect(leerFiltros('?turno=sin').turno).toBe('sin')
})
```

- [ ] **Step 2: Correr y ver que fallan** · **Step 3: Implementar** · **Step 4: Correr** · **Step 5: Commit**

---

## Task 8: Las dos pantallas

**Files:**
- Create: `frontend/src/components/ListadoPlantel.jsx`, `frontend/src/components/FichaBuzo.jsx`
- Modify: `frontend/src/App.jsx`
- Delete: `frontend/src/components/Dashboard.jsx`

**Interfaces:**
- Consumes: `GET /api/plantel/` (tarea 4), `frontend/src/lib/plantel.js` (tarea 7), `BarraLateral`, `CampoFecha`.

Referencia visual: `docs/superpowers/specs/2026-11-03-bocetos/1-listado-medico.html` y `2-ficha-buzo.html`. **Los textos del segundo llevan el tono viejo y van pasados a impersonal.**

- [ ] **Step 1: `ListadoPlantel.jsx`**

Contadores arriba, buscador, los cuatro filtros con su conteo, el filtro de turno, el desplegable de orden. Columna de turno con lugar y fecha en dd/mm/aaaa, "Sin turno" para los no inscriptos. "Presentados" muestra `presentados/exigidos`, y cuando `exigidos` es `null`, "N subidos · sin turno". La columna "A revisar" muestra las dos pilas separadas. Orden inicial: `pila_rapida` para el médico, `pila_cruda` para el enfermero.

- [ ] **Step 2: `FichaBuzo.jsx`**

Encabezado con grado, apellido, nombre, DNI, edad, unidad, cuántos le corresponden y el turno. Cuatro contadores. Los ocho puntos siempre, en orden a–h. Botones sólo en lo que espera dictamen; **Revertir** en lo aprobado por el médico. Diálogo de rechazo con los cuatro `REJECTION_REASONS`, el campo de detalle, y el aviso de que se manda un correo con la dirección a la vista. Volver al listado conserva los filtros.

- [ ] **Step 3: Rutas y fallback en `App.jsx`**

`/plantel` y `/plantel/:id`. `TableroSegunElRol` deja de caer en `Dashboard` cuando falla la consulta del perfil: **sin rol confirmado no se muestra ninguna pantalla**, sino un cartel que lo dice y un botón para reintentar. Borrar `Dashboard.jsx`.

- [ ] **Step 4: Lint, build y la suite entera**

Run: `cd frontend && npm run lint && npm run build && npm run test`
Expected: lint sin errores nuevos, build OK, tests en verde.

- [ ] **Step 5: Verificar en el navegador**

Levantar los dos servidores y entrar como médico y como enfermero. Comprobar: que el denominador cambia con la edad, que el filtro de turno recalcula los contadores, que el buzo sin turno no dice "0/0", que el enfermero ve "Apto", que aprobar como enfermero deja pre-revisado, y que un rechazo imprime el correo en la terminal del backend. **No enviar nada que modifique a los usuarios sembrados.**

- [ ] **Step 6: Commit**
