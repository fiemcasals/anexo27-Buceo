## Task 1: Catálogo de los ocho estudios

**Files:**
- Create: `backend/api/catalog.py`
- Create: `backend/api/tests/__init__.py` (vacío)
- Create: `backend/api/tests/test_catalog.py`
- Delete: `backend/api/tests.py` (stub vacío de Django, lo reemplaza el paquete)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `RequiredStudy` — dataclass congelada con `code: str`, `text: str`, `validity_days: int`, `min_age: int | None`, `upload_hint: str`
  - `ALL: tuple[RequiredStudy, ...]` — los ocho, en orden `a`…`h`
  - `CODES: tuple[str, ...]` — `("a", …, "h")`
  - `get(code: str) -> RequiredStudy` — levanta `KeyError` si no existe
  - `required_for_age(age: int) -> tuple[RequiredStudy, ...]`

- [ ] **Step 1: Write the failing tests**

```python
# backend/api/tests/test_catalog.py
from django.test import SimpleTestCase
from api import catalog


class CatalogTests(SimpleTestCase):
    def test_holds_the_eight_directive_points_in_order(self):
        self.assertEqual([s.code for s in catalog.ALL], list("abcdefgh"))
        self.assertEqual(catalog.CODES, tuple("abcdefgh"))

    def test_point_f_excludes_chagas_and_lasts_a_year(self):
        f = catalog.get("f")
        self.assertNotIn("CHAGAS", f.text.upper())
        self.assertEqual(f.validity_days, 365)

    def test_only_the_anexo_27_lasts_thirty_days(self):
        self.assertEqual(catalog.get("h").validity_days, 30)
        self.assertTrue(
            all(s.validity_days == 365 for s in catalog.ALL if s.code != "h")
        )

    def test_only_point_a_is_age_conditional(self):
        self.assertEqual(catalog.get("a").min_age, 40)
        self.assertTrue(
            all(s.min_age is None for s in catalog.ALL if s.code != "a")
        )

    def test_under_forty_owes_seven_points(self):
        self.assertEqual(
            [s.code for s in catalog.required_for_age(39)], list("bcdefgh")
        )

    def test_exactly_forty_owes_all_eight(self):
        self.assertEqual(
            [s.code for s in catalog.required_for_age(40)], list("abcdefgh")
        )

    def test_compound_points_carry_an_upload_hint(self):
        self.assertIn("frente y perfil", catalog.get("d").upload_hint)
        self.assertIn("cinco análisis", catalog.get("f").upload_hint)
        self.assertEqual(catalog.get("b").upload_hint, "")

    def test_unknown_code_raises(self):
        with self.assertRaises(KeyError):
            catalog.get("z")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_catalog -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.catalog'`

- [ ] **Step 3: Implement `backend/api/catalog.py`**

Los ocho `RequiredStudy` con los textos y vigencias de **Global Constraints**, textuales. `required_for_age` filtra por `min_age is None or age >= min_age`. Los textos de ayuda de `d` y `f` son los del §4 del spec:

- `d`: `"El archivo debe incluir las dos placas, frente y perfil."`
- `f`: `"El archivo debe incluir los cinco análisis: hemograma, eritrosedimentación, urea, glucosa y orina completo."`

El módulo no importa nada de Django: lo usan tanto el motor como, más adelante, los serializadores y las plantillas de correo.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_catalog -v 2`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add backend/api/catalog.py backend/api/tests/
git rm backend/api/tests.py
git commit -m "feat(api): add catalog of the eight required studies from Directiva 443/21"
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
