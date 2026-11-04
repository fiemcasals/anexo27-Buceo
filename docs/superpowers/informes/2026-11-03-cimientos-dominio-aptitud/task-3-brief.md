## Task 3: Fechas de habilitación

**Files:**
- Modify: `backend/api/models.py`
- Modify: `backend/users/models.py` (la inscripción del buzo)
- Modify: `backend/api/admin.py`
- Create: `backend/api/tests/test_habilitation_window.py`
- Create: migraciones de `api` y `users` (generadas)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `HabilitationWindow` con `cycle: PositiveIntegerField`, `slot: CharField(choices=SLOT_CHOICES)`, `start_date`, `end_date`
  - `HabilitationWindow.SLOT_CHOICES` — `FIRST` → "1.ª fecha", `SECOND` → "2.ª fecha", `COMPLEMENTARY` → "Complementaria"
  - `HabilitationWindow.anexo27_earliest_date -> date` — `end_date - timedelta(days=30)`
  - `UserProfile.habilitation_window` — FK nullable a `HabilitationWindow`, `on_delete=SET_NULL`, `related_name="divers"`

- [ ] **Step 1: Write the failing tests**

```python
# backend/api/tests/test_habilitation_window.py
from datetime import date
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from api.models import HabilitationWindow


def _november_2026():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="FIRST",
        start_date=date(2026, 11, 18), end_date=date(2026, 11, 20),
    )


class HabilitationWindowTests(TestCase):
    def test_anexo_27_window_opens_thirty_days_before_the_last_day(self):
        self.assertEqual(_november_2026().anexo27_earliest_date, date(2026, 10, 21))

    def test_a_single_day_window_is_valid(self):
        w = HabilitationWindow(
            cycle=2026, slot="SECOND",
            start_date=date(2026, 12, 5), end_date=date(2026, 12, 5),
        )
        w.full_clean()  # no levanta

    def test_end_before_start_is_rejected(self):
        w = HabilitationWindow(
            cycle=2026, slot="SECOND",
            start_date=date(2026, 12, 5), end_date=date(2026, 12, 1),
        )
        with self.assertRaises(ValidationError):
            w.full_clean()

    def test_one_window_per_slot_per_cycle(self):
        _november_2026()
        with self.assertRaises(IntegrityError):
            HabilitationWindow.objects.create(
                cycle=2026, slot="FIRST",
                start_date=date(2026, 11, 25), end_date=date(2026, 11, 27),
            )

    def test_an_incomplete_cycle_is_normal(self):
        # Solo la primera cargada: el ciclo incompleto no es un error (spec §4.1).
        _november_2026()
        self.assertEqual(HabilitationWindow.objects.filter(cycle=2026).count(), 1)

    def test_the_three_slots_of_a_cycle(self):
        self.assertEqual(
            list(dict(HabilitationWindow.SLOT_CHOICES)),
            ["FIRST", "SECOND", "COMPLEMENTARY"],
        )

    def test_window_is_registered_in_the_django_admin(self):
        from django.contrib import admin
        self.assertIn(HabilitationWindow, admin.site._registry)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_habilitation_window -v 2`
Expected: FAIL — `ImportError: cannot import name 'HabilitationWindow'`

- [ ] **Step 3: Implement `HabilitationWindow` in `backend/api/models.py`**

`unique_together` (o `UniqueConstraint`) sobre `("cycle", "slot")`. `clean()` levanta `ValidationError` si `end_date < start_date`. Ordenamiento por defecto por `start_date`. El `__str__` tiene que ser legible para el desplegable del buzo y para el admin, con el rango en castellano — es cadena visible, así que impersonal (§10).

- [ ] **Step 4: Add `habilitation_window` to `UserProfile` in `backend/users/models.py`**

FK nullable: la mayoría de los buzos no va a tener fecha elegida, y §4.1 aclara que eso no siempre es culpa suya.

- [ ] **Step 5: Register `HabilitationWindow` in `backend/api/admin.py`**

Con `list_display` del ciclo, el lugar en el ciclo y el rango. Es la única forma de cargar fechas hasta el plan 4.

- [ ] **Step 6: Generate migrations and run them**

```bash
cd backend
./venv/Scripts/python.exe manage.py makemigrations api users
./venv/Scripts/python.exe manage.py migrate
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_habilitation_window -v 2`
Expected: PASS, 7 tests

- [ ] **Step 8: Commit**

```bash
git add backend/api/ backend/users/
git commit -m "feat(api): add habilitation windows and diver enrolment"
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
