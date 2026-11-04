## Task 4: Cada estudio atado a un punto de la directiva

**Files:**
- Modify: `backend/api/models.py` (`StudyBlock`)
- Create: `backend/api/tests/test_study_block.py`
- Create: migración de `api` (generada)

**Interfaces:**
- Consumes: `api.catalog.CODES`, `api.catalog.get` (Tarea 1)
- Produces:
  - `StudyBlock.study_code: CharField(max_length=1, choices=…)` — obligatorio
  - `StudyBlock.is_current: BooleanField(default=True)`
  - `StudyBlock.save()` — al crear un bloque vigente para un `(user, study_code)`, baja `is_current` de los anteriores de ese mismo par y copia el texto del catálogo en `title`

- [ ] **Step 1: Write the failing tests**

```python
# backend/api/tests/test_study_block.py
from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from api import catalog
from api.models import StudyBlock


class StudyBlockTests(TestCase):
    def setUp(self):
        self.diver = User.objects.create(username="buzo1")

    def _block(self, code="g", day=date(2026, 10, 28)):
        return StudyBlock.objects.create(
            user=self.diver, study_code=code, study_date=day
        )

    def test_uploading_a_replacement_demotes_the_previous_one(self):
        first = self._block()
        second = self._block(day=date(2026, 11, 3))
        first.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_a_replacement_does_not_touch_another_point(self):
        other = self._block(code="b")
        self._block(code="g")
        self._block(code="g")
        other.refresh_from_db()
        self.assertTrue(other.is_current)

    def test_a_replacement_does_not_touch_another_diver(self):
        someone_else = StudyBlock.objects.create(
            user=User.objects.create(username="buzo2"),
            study_code="g", study_date=date(2026, 10, 1),
        )
        self._block(code="g")
        someone_else.refresh_from_db()
        self.assertTrue(someone_else.is_current)

    def test_title_comes_from_the_catalog_not_from_free_text(self):
        self.assertEqual(self._block(code="f").title, catalog.get("f").text)

    def test_study_code_must_be_one_of_the_eight(self):
        with self.assertRaises(ValidationError):
            StudyBlock(
                user=self.diver, study_code="z", study_date=date(2026, 1, 1)
            ).full_clean()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_study_block -v 2`
Expected: FAIL — `StudyBlock() got unexpected keyword arguments: 'study_code'`

- [ ] **Step 3: Implement the changes to `StudyBlock` in `backend/api/models.py`**

`study_code` con `choices=[(c, c) for c in catalog.CODES]`. `title` **se deja como campo** pero lo llena `save()` desde el catálogo: así el dashboard actual sigue andando hasta que los planes 2 y 3 lo reemplacen, y la fuente de verdad pasa a ser el catálogo (§14). `pdf_attachment` queda como está — la compresión es del plan 2.

La baja de los anteriores va en `save()`, y solo al crear (cuando `self._state.adding` y `is_current`), para que un `save()` de actualización no se desarme a sí mismo.

- [ ] **Step 4: Generate the migration and run it**

```bash
cd backend
./venv/Scripts/python.exe manage.py makemigrations api
./venv/Scripts/python.exe manage.py migrate
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_study_block -v 2`
Expected: PASS, 5 tests

- [ ] **Step 6: Commit**

```bash
git add backend/api/
git commit -m "feat(api): bind each study to a directive point and keep one current per slot"
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

---

## Correcciones del controlador a este brief (obligatorias)

Son resoluciones tomadas antes de empezar, sobre defectos detectados en el texto del
plan. Tienen prioridad sobre el texto de arriba.

1. **`test_study_code_must_be_one_of_the_eight` tal como está escrito pasa por el
   motivo equivocado.** `StudyBlock.title` y `StudyBlock.pdf_attachment` también son
   obligatorios, así que `full_clean()` sobre un bloque recién armado levanta
   `ValidationError` por ellos aunque `study_code` fuera válido — el test no probaría
   nada. Hay que afirmar que el error es **de `study_code`**, inspeccionando
   `cm.exception.message_dict` (o `error_dict`) y verificando que la clave
   `study_code` está presente.

2. **La tarea también agrega `study_code` a `StudyBlockSerializer`** en
   `backend/api/serializers.py`, en `Meta.fields`. Al volverse obligatorio en el
   modelo, la API queda incoherente sin él.

   Consecuencia aceptada y conocida: `POST /api/blocks/` desde el frontend actual
   queda roto, porque `Dashboard.jsx` no manda `study_code`. Es deliberado — el flujo
   de carga se reescribe completo en el plan 2 (carga por punto, sin desplegable), así
   que arreglar el formulario viejo es trabajo que se tira. **No toques el frontend.**
   La afirmación del plan de que "el frontend sigue andando" vale para la lectura, no
   para la carga.
