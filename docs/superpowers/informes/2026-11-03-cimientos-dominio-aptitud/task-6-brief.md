## Task 6: Motor de cálculo de estados y aptitud

El corazón del sistema. Todo lo que los planes 2, 3 y 4 muestran o notifican sale de acá.

**Files:**
- Create: `backend/api/fitness.py`
- Create: `backend/api/tests/test_fitness.py`

**Interfaces:**
- Consumes: `api.catalog` (Tarea 1), `UserProfile.age_in_year` y `UserProfile.habilitation_window` (Tareas 2 y 3), `StudyBlock.study_code` / `is_current` (Tarea 4), `Comment.status` / `reviewer_role` (Tarea 5)
- Produces:
  - `StudyState` — enum: `NOT_REQUIRED`, `MISSING`, `BEFORE_WINDOW`, `IN_REVIEW`, `PRE_REVIEWED`, `APPROVED`, `REJECTED`, `EXPIRED`, `DATE_INVALID`
  - `DiverState` — enum: `NO_WINDOW`, `UNKNOWN_AGE`, `PROBLEM`, `INCOMPLETE`, `TO_REVIEW`, `APTO`
  - `SlotStatus` — dataclass congelada: `code: str`, `state: StudyState`, `block: StudyBlock | None`, `last_dictamen: Comment | None`, `expires_on: date | None`
  - `DiverSummary` — dataclass congelada: `required_codes: tuple[str, ...]`, `slots: tuple[SlotStatus, ...]`, `presented: int`, `approved: int`, `pending_review: int`, `pre_reviewed: int`, `problems: int`, `last_doctor_review: date | None`, `state: DiverState`, `is_apto: bool`
  - `required_codes(profile) -> tuple[str, ...]` — vacío si no hay fecha o no hay fecha de nacimiento
  - `diver_summary(profile, today: date) -> DiverSummary`

- [ ] **Step 1: Write the test helpers and the failing tests for the required set**

Los tres grupos de tests comparten estos ayudantes, al tope del módulo. Están
fijados acá porque los tests de los pasos 2 y 3 los usan y tienen que coincidir:

```python
# backend/api/tests/test_fitness.py — ayudantes
TODAY = date(2026, 11, 3)

def _november_2026():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="FIRST",
        start_date=date(2026, 11, 18), end_date=date(2026, 11, 20))

def _july_2027():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="COMPLEMENTARY",
        start_date=date(2027, 7, 12), end_date=date(2027, 7, 14))

def _diver(birth_year, birth_month=6, birth_day=15, window=None, dni=None):
    """Perfil de buzo. birth_year=None deja birth_date vacía."""
    ...

def _upload(profile, code, study_date, dictamenes=()):
    """Crea el StudyBlock vigente del punto y sus dictámenes en orden.
    dictamenes es una secuencia de (status, reviewer_role)."""
    ...
```

`_diver` genera un DNI único cuando no se le pasa uno, porque la Tarea 2 lo volvió
único y varios tests crean más de un buzo.

```python
# backend/api/tests/test_fitness.py — primera parte
class RequiredSetTests(TestCase):
    def test_under_forty_in_the_habilitation_year_owes_seven(self):
        # Nacido en 1988, habilitación de noviembre de 2026 -> 38
        p = _diver(birth_year=1988, window=_november_2026())
        self.assertEqual(fitness.required_codes(p), tuple("bcdefgh"))

    def test_turning_forty_during_the_habilitation_year_owes_eight(self):
        # Nacido el 31/12/1986: el 18 de noviembre de 2026 tiene 39 cumplidos,
        # pero el criterio de la unidad es la edad a fin de año -> 40.
        p = _diver(birth_year=1986, birth_month=12, birth_day=31,
                   window=_november_2026())
        self.assertEqual(fitness.required_codes(p), tuple("abcdefgh"))

    def test_the_complementary_date_uses_its_own_year(self):
        # Complementaria de julio de 2027: el mismo buzo es un año mayor.
        p = _diver(birth_year=1987, window=_july_2027())
        self.assertEqual(fitness.required_codes(p), tuple("abcdefgh"))

    def test_no_window_means_nothing_can_be_required(self):
        self.assertEqual(fitness.required_codes(_diver(birth_year=1988)), ())

    def test_no_birth_date_means_nothing_can_be_required(self):
        self.assertEqual(
            fitness.required_codes(_diver(birth_year=None, window=_november_2026())), ()
        )
```

- [ ] **Step 2: Write the failing tests for per-study state**

```python
# backend/api/tests/test_fitness.py — segunda parte
class SlotStateTests(TestCase):
    # Ventana: 18 al 20 de noviembre de 2026. El estudio tiene que estar
    # vigente el día 20, que es el más exigente.

    def test_approved_and_valid_through_the_last_day(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.APPROVED)

    def test_approved_but_expiring_inside_the_window_is_expired(self):
        # Vence el 19: no cubre el día 20.
        self.assertEqual(self._state("b", study_date=date(2025, 11, 19),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.EXPIRED)

    def test_a_nurse_approval_is_only_a_pre_review(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15),
                                     dictamen=("PRE_APPROVED", "NURSE")),
                         StudyState.PRE_REVIEWED)

    def test_uploaded_without_any_dictamen_is_in_review(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15)),
                         StudyState.IN_REVIEW)

    def test_the_last_dictamen_wins(self):
        # Pre-aprobado por el enfermero y después rechazado por el médico.
        self.assertEqual(
            self._state("b", study_date=date(2026, 1, 15),
                        dictamenes=[("PRE_APPROVED", "NURSE"), ("REJECTED", "DOCTOR")]),
            StudyState.REJECTED,
        )

    def test_a_point_that_does_not_apply_by_age(self):
        self.assertEqual(self._state_for_young_diver("a"), StudyState.NOT_REQUIRED)

    def test_a_required_point_with_nothing_uploaded_is_missing(self):
        self.assertEqual(self._state("g", block=None), StudyState.MISSING)

    def test_the_anexo_27_is_not_missing_before_its_window_opens(self):
        # La ventana abre el 21/10/2026; hoy es el 3/10.
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 3)),
                         StudyState.BEFORE_WINDOW)

    def test_the_anexo_27_is_missing_once_its_window_is_open(self):
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 25)),
                         StudyState.MISSING)

    def test_a_study_dated_after_the_window_is_flagged_not_trusted(self):
        # El buzo tipeó 2027 por 2026. No puede contar como vigente.
        self.assertEqual(self._state("b", study_date=date(2027, 1, 15),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.DATE_INVALID)

    def test_only_the_current_block_of_a_slot_is_considered(self):
        # Un rechazado histórico no debe pisar al reemplazo aprobado.
        p = _diver(birth_year=1988, window=_november_2026())
        _upload(p, "f", date(2026, 10, 18),
                dictamenes=[("REJECTED", "NURSE")])          # queda histórico
        _upload(p, "f", date(2026, 10, 30),
                dictamenes=[("APPROVED", "DOCTOR")])         # pasa a vigente
        slot = _slot_of(fitness.diver_summary(p, TODAY), "f")
        self.assertEqual(slot.state, StudyState.APPROVED)
        self.assertEqual(slot.block.study_date, date(2026, 10, 30))
```

El ayudante `_slot_of(summary, code) -> SlotStatus` devuelve el `SlotStatus` de un
punto, y lo usan tanto este test como los del paso 3. `self._state(...)` es un
envoltorio del mismo módulo que arma un buzo con un único punto cargado y devuelve
directamente su `StudyState`, para que los tests de esta clase sean de una línea;
acepta `code`, `study_date`, `dictamen` o `dictamenes`, `block=None` y `today`
(que por defecto es `TODAY`). `self._state_for_young_diver(code)` hace lo mismo con
un buzo de 38 años.

- [ ] **Step 3: Write the failing tests for the diver summary**

Los `self._diver_with_…` y `self._summary_…` de esta clase son fábricas de una o
dos líneas sobre `_diver` y `_upload`; sus nombres dicen qué tienen que armar. El
buzo base de esta clase tiene 38 años en 2026, así que le corresponden **siete**
puntos (`b`…`h`), que es de dónde salen los 7 de las aserciones.

```python
# backend/api/tests/test_fitness.py — tercera parte
class DiverSummaryTests(TestCase):
    def test_apto_needs_every_required_point_approved_by_the_doctor(self):
        s = fitness.diver_summary(self._diver_with_all_approved_by_doctor(), TODAY)
        self.assertTrue(s.is_apto)
        self.assertEqual(s.state, DiverState.APTO)
        self.assertEqual(s.approved, 7)

    def test_nurse_pre_approvals_never_make_anyone_apto(self):
        s = fitness.diver_summary(self._diver_with_all_pre_approved(), TODAY)
        self.assertFalse(s.is_apto)
        self.assertEqual(s.approved, 0)
        self.assertEqual(s.pre_reviewed, 7)

    def test_without_a_window_nobody_is_apto(self):
        s = fitness.diver_summary(_diver(birth_year=1988), TODAY)
        self.assertFalse(s.is_apto)
        self.assertEqual(s.state, DiverState.NO_WINDOW)

    def test_without_a_birth_date_the_state_says_so(self):
        s = fitness.diver_summary(
            _diver(birth_year=None, window=_november_2026()), TODAY)
        self.assertEqual(s.state, DiverState.UNKNOWN_AGE)
        self.assertFalse(s.is_apto)

    def test_a_rejection_outranks_an_incomplete_set(self):
        self.assertEqual(self._summary_with_one_rejected_and_two_missing().state,
                         DiverState.PROBLEM)

    def test_presented_counts_rejected_and_expired_as_presented(self):
        # "Documentación completa" significa todo subido, no todo aprobado (§8.1).
        self.assertEqual(self._summary_all_uploaded_one_rejected().presented, 7)

    def test_last_doctor_review_ignores_nurse_dictamenes(self):
        s = self._summary_reviewed_by_doctor_then_nurse()
        self.assertEqual(s.last_doctor_review, date(2026, 10, 14))

    def test_last_doctor_review_is_none_when_the_doctor_never_looked(self):
        self.assertIsNone(self._summary_only_pre_reviewed().last_doctor_review)
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_fitness -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.fitness'`

- [ ] **Step 5: Implement `backend/api/fitness.py`**

Funciones puras: reciben el perfil con sus relaciones y `today`, no consultan nada por su cuenta más allá de lo que necesiten para juntar los bloques vigentes y su último dictamen. El plan 3 va a necesitar hacer esto para 150 perfiles sin caer en N+1 (§13), así que `diver_summary` no debe disparar consultas por cada punto: recibe el perfil y usa `prefetch_related` desde el llamador.

El orden de evaluación de `DiverState` es el que fija el spec (§7): `NO_WINDOW` y `UNKNOWN_AGE` primero porque sin ellos no hay contra qué medir, después `PROBLEM` (cualquier `REJECTED`, `EXPIRED` o `DATE_INVALID`), después `INCOMPLETE` (algún `MISSING`), después `TO_REVIEW` (algún `IN_REVIEW` o `PRE_REVIEWED`), y `APTO` solo si todos los exigidos están `APPROVED`.

La vigencia de un punto se evalúa así: `study_date + validity_days >= window.end_date` y además `study_date <= window.end_date`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_fitness -v 2`
Expected: PASS

- [ ] **Step 7: Run the whole suite**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test -v 2`
Expected: PASS, todos los tests de las seis tareas

- [ ] **Step 8: Commit**

```bash
git add backend/api/fitness.py backend/api/tests/test_fitness.py
git commit -m "feat(api): add the fitness engine that derives study states and aptitude"
```

---



---

## Global Constraints (del plan — valores textuales, obligatorios)


Valores copiados textuales del spec. Son requisitos implícitos de todas las tareas.

- **Los ocho estudios exigidos** (§4), con su vigencia y a quién le corresponden:
  - `a` — "Electrocardiograma de esfuerzo" — 365 días — **solo a partir de los 40 años**
  - `b` — "Ecocardiograma con informe (sin excepción)" — 365 días — todos
  - `c` — "Electroencefalograma" — 365 días — todos
  - `d` — "Radiografía de tórax, frente y perfil" — 365 días — todos
  - `e` — "Radiografía de senos frontales y paranasales" — 365 días — todos
  - `f` — "Hemograma, eritrosedimentación, dosaje de urea, dosaje de glucosa y orina completo" — 365 días — todos
  - `g` — "Ficha de control odontológico (actualizada)" — 365 días — todos
  - `h` — "Anexo 27 ORIGINAL, firmado por el médico militar y Jefe de Elemento" — **30 días** — todos
- **El punto `f` NO incluye CHAGAS y dura 365 días.** La versión de `STUDY_OPTIONS` en `Dashboard.jsx` que dice "CHAGAS (máx 30 días)" está derogada (§4). Los 30 días son exclusivos del punto `h`.
- **Edad = año de la habilitación − año de nacimiento** (§4). Una resta de años, **no** una edad cumplida. El que cumple 40 en cualquier momento de ese año debe los ocho estudios.
- **La vigencia se evalúa contra el rango de la fecha de habilitación elegida, no contra hoy**, y el estudio tiene que estar vigente **todos los días del rango** (§4.1, §15.17).
- **Ventana del Anexo 27 = `end_date − 30 días`** del rango elegido (§4.1).
- **Apto** = para cada estudio exigido existe una **aprobación del médico** y el estudio está vigente en todo el rango (§7). **Las aprobaciones de los enfermeros no cuentan para el apto.**
- **Un buzo sin fecha de habilitación elegida no puede estar apto** (§7).
- **Las tres fechas del ciclo son 1.ª, 2.ª y complementaria**, se cargan de a una y el ciclo incompleto es el estado normal (§4.1).
- **Grados, lista cerrada y en orden jerárquico** (§5): Oficiales `GD GB CY CR TC MY CT TP TT ST`; Suboficiales `SM SP SA SI SG CI CB`.
- **Motivos de rechazo, lista cerrada** (§6): "Estudio fuera del plazo de la directiva", "Valores no aptos para realizar la actividad", "Documento ilegible", "Otros". El detalle en texto libre se completa siempre.
- **El rol es único y excluyente** (§15.20): buzo, enfermero auxiliar, médico, admin. El médico, los enfermeros y el admin no presentan estudios.
- **Un solo archivo por punto, y el punto se dictamina completo o nada** (§4).
- **Ningún estado se guarda ni se tipea**: todo se deriva de dictámenes y fechas (§7).
- **Tono impersonal** en toda cadena visible (§10). En este plan aplica a las etiquetas de `choices`.
- **El DNI es obligatorio y único** (§5).

### Nota sobre la base de datos de desarrollo

Las migraciones de este plan vuelven el DNI obligatorio y único y reemplazan `age` por `birth_date`. El §16 del spec aclara que los datos actuales son de prueba, así que **la base de desarrollo se recrea**: borrar `backend/db.sqlite3`, correr `migrate` y volver a correr el script de datos de prueba. No hay migración de datos a escribir.
