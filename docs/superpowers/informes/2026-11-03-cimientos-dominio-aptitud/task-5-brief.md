## Task 5: Dictámenes en dos etapas con motivo de rechazo

**Files:**
- Modify: `backend/api/models.py` (`Comment`)
- Create: `backend/api/tests/test_dictamen.py`
- Create: migración de `api` (generada)

**Interfaces:**
- Consumes: `StudyBlock` (Tarea 4)
- Produces:
  - `Comment.STATUS_CHOICES` — `PRE_APPROVED` → "Pre-revisado", `APPROVED` → "Aprobado", `REJECTED` → "Rechazado con Observación"
  - `Comment.REJECTION_REASONS` — las cuatro del spec, con sus textos exactos
  - `Comment.reviewer_role: CharField` — `DOCTOR` | `NURSE`
  - `Comment.rejection_reason: CharField(blank=True)`
  - `Comment.clean()` — exige motivo y detalle en los rechazos, y los prohíbe fuera de ellos

- [ ] **Step 1: Write the failing tests**

```python
# backend/api/tests/test_dictamen.py
from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from api.models import Comment, StudyBlock


class DictamenTests(TestCase):
    def setUp(self):
        self.reviewer = User.objects.create(username="medico")
        self.block = StudyBlock.objects.create(
            user=User.objects.create(username="buzo1"),
            study_code="f", study_date=date(2026, 10, 18),
        )

    def _dictamen(self, **kwargs):
        return Comment(block=self.block, doctor=self.reviewer, **kwargs)

    def test_the_four_rejection_reasons_are_the_directive_ones(self):
        self.assertEqual(
            [label for _, label in Comment.REJECTION_REASONS],
            ["Estudio fuera del plazo de la directiva",
             "Valores no aptos para realizar la actividad",
             "Documento ilegible",
             "Otros"],
        )

    def test_pre_approval_is_a_status(self):
        self.assertIn("PRE_APPROVED", dict(Comment.STATUS_CHOICES))

    def test_a_rejection_needs_a_reason(self):
        with self.assertRaises(ValidationError):
            self._dictamen(
                status="REJECTED", reviewer_role="NURSE",
                content="La foto salió cortada.", rejection_reason="",
            ).full_clean()

    def test_a_rejection_needs_a_detail_for_the_diver(self):
        with self.assertRaises(ValidationError):
            self._dictamen(
                status="REJECTED", reviewer_role="NURSE",
                content="", rejection_reason="ILLEGIBLE",
            ).full_clean()

    def test_a_valid_rejection_passes(self):
        self._dictamen(
            status="REJECTED", reviewer_role="NURSE",
            content="La fotografía está cortada.", rejection_reason="ILLEGIBLE",
        ).full_clean()

    def test_an_approval_cannot_carry_a_rejection_reason(self):
        with self.assertRaises(ValidationError):
            self._dictamen(
                status="APPROVED", reviewer_role="DOCTOR",
                rejection_reason="ILLEGIBLE",
            ).full_clean()

    def test_a_dictamen_records_who_and_with_what_role(self):
        d = self._dictamen(status="PRE_APPROVED", reviewer_role="NURSE")
        d.full_clean()
        d.save()
        self.assertEqual(d.doctor, self.reviewer)
        self.assertEqual(d.reviewer_role, "NURSE")
        self.assertIsNotNone(d.created_at)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_dictamen -v 2`
Expected: FAIL — `Comment` no tiene `REJECTION_REASONS`

- [ ] **Step 3: Implement the changes to `Comment` in `backend/api/models.py`**

Las claves de `REJECTION_REASONS` son `OUT_OF_TERM`, `UNFIT_VALUES`, `ILLEGIBLE`, `OTHER`, en ese orden, con los textos exactos de **Global Constraints**. El campo `doctor` se deja con ese nombre aunque ahora también lo use un enfermero: renombrarlo arrastra migración y todas las referencias del frontend sin cambiar nada de comportamiento. `reviewer_role` es lo que distingue quién dictaminó.

- [ ] **Step 4: Generate the migration and run it**

```bash
cd backend
./venv/Scripts/python.exe manage.py makemigrations api
./venv/Scripts/python.exe manage.py migrate
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_dictamen -v 2`
Expected: PASS, 7 tests

- [ ] **Step 6: Commit**

```bash
git add backend/api/
git commit -m "feat(api): add nurse pre-approval and closed rejection reasons to dictamenes"
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

1. **`Comment.content` pasa a `blank=True`.** Hoy es `TextField()` obligatorio.
   Tres de los tests de este brief llaman `full_clean()` sobre dictámenes que no son
   rechazos y sin `content`: dos pasarían por el motivo equivocado y
   `test_a_dictamen_records_who_and_with_what_role` fallaría directamente.

   El §6 del spec pide el detalle en texto libre **en los rechazos**. Una aprobación
   no tiene nada que comentar y no hay por qué obligarla a inventar texto. Así que la
   obligatoriedad de `content` queda sólo en `clean()`, y sólo cuando
   `status == "REJECTED"` — que es justo lo que ya pide
   `test_a_rejection_needs_a_detail_for_the_diver`.
