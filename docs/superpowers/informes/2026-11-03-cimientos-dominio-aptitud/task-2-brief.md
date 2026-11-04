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

1. **El snippet de tests de `users/tests.py` olvida un import.** Agregar
   `from datetime import date`. Sin eso los tests no corren.

2. **La tarea también modifica `backend/api/serializers.py`.** El plan no lo
   menciona y es un error: `UserProfileSerializer.Meta.fields` lista `'age'`, y al
   quitar ese campo del modelo DRF revienta al resolverlo, dejando `/api/profiles/`
   roto. Quitar `'age'` de esa lista y agregar `'birth_date'`. El §14 del spec manda
   reemplazar uno por el otro, así que el serializador tiene que seguir al modelo.
   Agregar un test que confirme que el serializador expone `birth_date` y no `age`.

   Consecuencia aceptada y conocida: `frontend/src/components/Profile.jsx` muestra
   hoy un campo de edad que va a quedar vacío hasta el plan 2, donde se rehace esa
   pantalla. **No toques el frontend.**
