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
