# Cimientos del dominio y cálculo de aptitud — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar en el backend el catálogo de los ocho estudios de la directiva, las fechas de habilitación, los roles y el motor que calcula el estado de cada estudio y la aptitud de cada buzo, todo cubierto por tests y sin tocar la interfaz.

**Architecture:** Dos módulos nuevos sin estado — `api/catalog.py` con los ocho estudios y sus reglas, y `api/fitness.py` con el cálculo derivado — más los cambios de modelo que esos módulos necesitan. El cálculo vive en funciones puras que reciben los objetos ya cargados y devuelven dataclasses, así se puede testear sin base de datos y después reutilizar tanto en el endpoint del listado como en el del buzo y en los correos. Ningún estado se guarda en la base: todo se deriva de los dictámenes y las fechas, que es lo que hace que la aptitud se caiga sola cuando algo vence.

**Tech Stack:** Django 6.0.3, `django.test.TestCase` / `SimpleTestCase` con `manage.py test` (el proyecto no usa pytest), SQLite, dataclasses y enums de la biblioteca estándar.

**Spec:** `docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md`

---

## Mapa de planes

Este plan es el primero de cuatro. Cada uno deja software funcionando.

| | Plan | Qué deja andando |
|---|---|---|
| **1** | **Cimientos del dominio y cálculo de aptitud** (este) | Catálogo, fechas, roles, motor de estados. Testeado. Administrable desde el admin de Django. |
| 2 | Pantalla del buzo y carga de estudios | Un buzo se registra, se inscribe a una fecha, sube estudios comprimidos y ve qué le falta. |
| 3 | Circuito del médico y los enfermeros | Listado con buscador, filtros y contadores; ficha; dictámenes en dos etapas. |
| 4 | Panel del admin, notificaciones y procesos programados | Alta de fechas, designación de roles, los tres correos, limpieza por retención. |

El orden importa: el §14 del spec dice que las fechas de habilitación son el cimiento del que depende todo el cálculo. Este plan registra los modelos en el admin de Django para que se puedan cargar fechas y probar el plan 2 antes de que exista el panel propio del plan 4.

---

## Global Constraints

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

## Review Focus

Clases de entrada que el spec implica, que ninguna tarea exige por sí sola, y que van a lastimar a alguien si se rompen. Cada una tiene su test agregado a la tarea dueña del código.

1. **Buzo sin fecha de habilitación elegida** — es el estado inicial de los 150 y, según §4.1, no siempre es culpa suya. El motor tiene que devolver `NO_WINDOW` y `is_apto = False` sin reventar por `None`. *(Tarea 6)*
2. **Anexo 27 que todavía no se puede presentar** — mientras falte y hoy sea anterior a `end_date − 30`, el estado es `BEFORE_WINDOW`, no `MISSING`. Tratarlo como faltante lo pinta en rojo once meses y entrena al buzo a ignorar el rojo (§15.19). *(Tarea 6)*
3. **Buzo que cumple exactamente 40 en el año de la habilitación** — es el borde de la única regla condicional del sistema, y equivocarlo deja a alguien presentándose sin el electrocardiograma de esfuerzo. *(Tareas 1 y 6)*
4. **Estudio con fecha posterior al rango de habilitación** — el buzo carga la fecha a mano (§8.3) y va a tipear 2027 por 2026. Calcular vigencia desde una fecha futura daría un estudio eternamente vigente y declararía apto a alguien que no lo está. El motor lo marca `DATE_INVALID` para que el médico lo rechace. *(Tarea 6)*
5. **Buzo sin fecha de nacimiento** — queda permitido en el modelo porque la base se recrea y el registro del plan 2 todavía no existe. El conjunto exigido no se puede calcular, así que el motor tiene que decirlo y no asumir siete. *(Tareas 2 y 6)*

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `backend/api/catalog.py` **(nuevo)** | Los ocho estudios de la directiva: código, texto, vigencia, edad mínima, texto de ayuda de carga. Sin estado y sin dependencias de Django. |
| `backend/api/fitness.py` **(nuevo)** | Cálculo derivado: conjunto exigido, estado de cada punto, resumen y aptitud del buzo. Funciones puras sobre objetos ya cargados. |
| `backend/users/models.py` **(modificar)** | `birth_date` en lugar de `age`, DNI único, grados como lista cerrada, rol de enfermero, inscripción a una fecha. |
| `backend/api/models.py` **(modificar)** | `HabilitationWindow`; `study_code` e `is_current` en `StudyBlock`; pre-aprobación, rol del revisor y motivo de rechazo en `Comment`. |
| `backend/api/admin.py`, `backend/users/admin.py` **(modificar)** | Registrar los modelos para que el admin pueda cargar fechas y designar roles antes del plan 4. |
| `backend/api/tests/` **(nuevo paquete)** | Reemplaza `api/tests.py`, que es el stub vacío de Django. Un módulo por tarea. |
| `backend/users/tests.py` **(modificar)** | Tests del perfil. |

---

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

## Task 2: Perfil del buzo — nacimiento, DNI, grado y roles

**Files:**
- Modify: `backend/users/models.py`
- Modify: `backend/users/admin.py`
- Modify: `backend/users/tests.py`
- Create: `backend/users/migrations/0003_profile_birth_date_dni_rank_roles.py` (generada)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `UserProfile.ROLE_CHOICES` — incluye `("NURSE", "Enfermero auxiliar")` además de `USER`, `DOCTOR`, `ADMIN`
  - `UserProfile.RANK_CHOICES` — agrupadas, para el desplegable
  - `UserProfile.RANK_VALUES: tuple[str, ...]` — los 17 en orden jerárquico, para ordenar listados
  - `UserProfile.birth_date: DateField(null=True)` — reemplaza `age`
  - `UserProfile.dni: CharField(unique=True)`
  - `UserProfile.age_in_year(year: int) -> int | None` — `year - birth_date.year`, o `None` sin fecha de nacimiento

- [ ] **Step 1: Write the failing tests**

```python
# backend/users/tests.py
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase
from users.models import UserProfile


def _profile(username, **kwargs):
    user = User.objects.create(username=username)
    return UserProfile.objects.create(user=user, **kwargs)


class UserProfileTests(TestCase):
    def test_age_is_a_year_subtraction_not_a_birthday(self):
        # Cumple 40 en diciembre de 2026: en 2026 ya debe los ocho estudios.
        p = _profile("a", dni="1", birth_date=date(1986, 12, 31))
        self.assertEqual(p.age_in_year(2026), 40)

    def test_age_is_none_without_a_birth_date(self):
        self.assertIsNone(_profile("b", dni="2").age_in_year(2026))

    def test_dni_is_unique(self):
        _profile("c", dni="30111222")
        with self.assertRaises(IntegrityError):
            _profile("d", dni="30111222")

    def test_nurse_is_a_role(self):
        self.assertIn("NURSE", dict(UserProfile.ROLE_CHOICES))

    def test_rank_is_the_closed_hierarchical_list(self):
        self.assertEqual(
            UserProfile.RANK_VALUES,
            ("GD", "GB", "CY", "CR", "TC", "MY", "CT", "TP", "TT", "ST",
             "SM", "SP", "SA", "SI", "SG", "CI", "CB"),
        )

    def test_ranks_are_grouped_into_officers_and_ncos(self):
        groups = [g for g, _ in UserProfile.RANK_CHOICES]
        self.assertEqual(groups, ["Oficiales", "Suboficiales"])

    def test_profile_is_registered_in_the_django_admin(self):
        from django.contrib import admin
        self.assertIn(UserProfile, admin.site._registry)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test users -v 2`
Expected: FAIL — `age_in_year` no existe y `RANK_VALUES` no está definido

- [ ] **Step 3: Implement the model changes in `backend/users/models.py`**

Quitar `age`. Agregar `birth_date = models.DateField(null=True, blank=True)` — nullable a propósito, ver Review Focus 5. `dni` pasa a `models.CharField(max_length=20, unique=True)`. `rank` pasa a `models.CharField(max_length=2, choices=RANK_CHOICES, blank=True)`. Agregar `NURSE` a `ROLE_CHOICES` con la etiqueta `"Enfermero auxiliar"`. `age_in_year` devuelve `None` si `birth_date` es `None`.

`RANK_CHOICES` usa el formato agrupado de Django (`[(grupo, [(valor, etiqueta), …]), …]`) y `RANK_VALUES` se deriva de ella, no se escribe dos veces.

- [ ] **Step 4: Register `UserProfile` in `backend/users/admin.py`**

Con `list_display` que muestre grado, apellido, nombre, DNI, correo y rol, y `search_fields` sobre DNI, apellido y nombre — es lo que el admin necesita para cotejar contra sus registros (§8.5). El panel propio llega en el plan 4; esto lo desbloquea mientras tanto.

- [ ] **Step 5: Generate the migration and recreate the dev database**

```bash
cd backend
./venv/Scripts/python.exe manage.py makemigrations users
rm -f db.sqlite3
./venv/Scripts/python.exe manage.py migrate
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test users -v 2`
Expected: PASS, 7 tests

- [ ] **Step 7: Commit**

```bash
git add backend/users/
git commit -m "feat(users): replace age with birth_date, make DNI unique, close the rank list, add nurse role"
```

---

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

## Task 7: Datos de prueba al día

Sin esto el plan 2 arranca con una base que no refleja el dominio nuevo, y nadie puede mirar nada a mano.

**Files:**
- Modify: `backend/create_test_data.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: una base de desarrollo con un médico, un enfermero, una fecha de habilitación cargada y buzos que cubren los estados interesantes.

- [ ] **Step 1: Rewrite the seed script**

Tiene que dejar: el admin; un médico; un enfermero (`SG Vera`, que es el nombre que usa el spec en los bocetos); la ventana 18–20 de noviembre de 2026 como 1.ª fecha del ciclo 2026, y **solo esa**, para que el ciclo incompleto sea lo que se ve al abrir; y al menos cuatro buzos que caigan en estados distintos — uno apto, uno con un rechazo, uno incompleto, uno sin fecha elegida. Las fechas de nacimiento tienen que incluir un buzo que cumple 40 en 2026, que es el borde de la regla.

Correrlo con `manage.py shell -c "exec(open('create_test_data.py', encoding='utf-8').read())"`: el script define variables entre bloques y `manage.py shell < archivo` las pierde, que es lo que ya pasó al probarlo.

- [ ] **Step 2: Recreate the database and run it**

```bash
cd backend
rm -f db.sqlite3
./venv/Scripts/python.exe manage.py migrate
PYTHONUTF8=1 ./venv/Scripts/python.exe manage.py shell -c "exec(open('create_test_data.py', encoding='utf-8').read())"
```

- [ ] **Step 3: Verify the engine against the seeded data**

Imprimir el `DiverSummary` de cada buzo sembrado por el shell y confirmar que los cuatro estados aparecen. Expected: un `APTO`, un `PROBLEM`, un `INCOMPLETE`, un `NO_WINDOW`.

- [ ] **Step 4: Run the whole suite one more time**

Run: `cd backend && ./venv/Scripts/python.exe manage.py test -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/create_test_data.py
git commit -m "chore: seed test data for the new fitness domain"
```

---

## Lo que este plan deliberadamente no hace

- **No toca el frontend.** `Dashboard.jsx` sigue andando porque `title` se mantiene y se llena desde el catálogo.
- **No toca `pdf_attachment` ni la compresión** (plan 2).
- **No construye endpoints.** El motor existe y está testeado, pero todavía no lo consume nadie por HTTP (planes 2 y 3).
- **No manda correos ni programa tareas** (plan 4). Por eso tampoco crea la marca de
  "aptitud ya notificada" del §14 del spec: sin el correo no tiene nada que marcar.
- **No impone quién puede dictaminar.** El modelo ya distingue el rol del revisor,
  pero la asimetría del §6 — la aprobación del enfermero no es definitiva y su
  rechazo sí — se hace cumplir en los endpoints, que son del plan 3.
- **No oculta la pantalla de Permisos** (plan 3, junto con el listado que la reemplaza).
- **No arregla la exposición de `/media/` ni `DEBUG = True`**, que el §2 del spec deja fuera de alcance a propósito.
