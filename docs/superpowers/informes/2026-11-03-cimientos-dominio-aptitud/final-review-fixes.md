# Correcciones de la revisión final — rama nicolas/primer-cambio

Veredicto: **apto para mergear con correcciones**. Sin hallazgos críticos. 12 de 13 mutaciones
fueron atrapadas por la suite; el presupuesto de consultas del listado está fijado en cero.

Cada ítem cita al revisor textualmente y después dice qué hacer. Los que dicen RULING llevan mi
decisión y el porqué. **Hacé los ítems en orden**: los primeros cuatro cambian contratos de los
que dependen los demás.

---

## 1. (Important) El estudio con fecha futura puede dejar a un buzo APTO

> `api/fitness.py:255` flags `DATE_INVALID` only when `study_date > window.end_date`. Nothing
> rejects a date after *today*. Concretely: a diver enrolled in the complementaria (12-14 July
> 2027) types `2027-01-15` for a study actually done in January 2026. `2027-01-15 <=
> 2027-07-14`, so no `DATE_INVALID`; validity runs to `2028-01-15`, so no `EXPIRED`; the doctor
> approves; the diver is **APTO on a document that really expires in January 2027, before the
> window**. The plan's own Review Focus item 4 named this hazard class ("va a tipear 2027 por
> 2026") and only half of it was built. [...] the fix is one line: `if block.study_date >
> min(today, window.end_date): return StudyState.DATE_INVALID`, plus a test.

Aplicalo. El plan nombró este peligro en su propia sección de Review Focus y se construyó la
mitad. Agregá el test con el caso concreto que el revisor describe: una fecha futura que cae
antes del fin de la ventana y que sin el arreglo produce APTO.

Verificá que el test discrimina: sacá el `min(today, ...)` y confirmá que falla.

---

## 2. (Important) El spec §15.9 — nadie dictamina sobre sus propios estudios — no existe en el código

> §15.9 — "nadie dictamina sobre sus propios estudios ... a nivel de la validación" — is
> implemented nowhere, and no task covered it. The plan never cites §15.9 [...] so no per-task
> review could have caught it. This is the "requirement every per-task review was blind to"
> case. Task 5 built `Comment.clean()` and two check constraints — the exact layer the spec
> names ("no solo de la interfaz") — and the check is two lines: `if self.doctor_id ==
> self.block.user_id`. It is reachable in production precisely as the spec warns: the unit has
> one doctor, and if the doctor is also a diver he can approve his own studies and the engine
> will report him APTO.

Implementalo en `Comment.clean()`, que es la capa que el spec nombra.

**No agregues una CheckConstraint para esto.** Una constraint de base no puede comparar
`doctor_id` contra `block.user_id` sin un join, y SQLite no lo permite dentro de un CHECK. El
`clean()` es lo que el spec pide ("a nivel de la validación, no solo de la interfaz") y es
suficiente.

Mensaje de error en el registro impersonal del proyecto. Test que asserte el error apuntando a
la condición correcta vía `message_dict`.

---

## 3. (Important) `DiverState` funde "Vencido" y "Rechazado" del §7 en un solo `PROBLEM`

> Plan line 637 defines the enum and line 839 claims "El orden de evaluación de `DiverState` es
> el que fija el spec (§7)". It is not: §7's per-diver table lists **Vencido** and **Rechazado**
> as two distinct states ("Vencido y Rechazado tienen prioridad"), §8.1 requires a summary of
> "cuántos vencidos" specifically, and §13 enumerates the roster row as "...pre-revisados,
> **vencidos, rechazados**, fecha del último dictamen, estado derivado". Nothing is lost at
> runtime [...] but the plan-3 listing endpoint will have to **re-derive the diver's displayed
> state from the slot states**, which is precisely the drift risk this review was asked to look
> for, and it will do it per row on a 150-row page. Fix cheaply now while the engine is the only
> consumer: split `PROBLEM` into `EXPIRED`/`REJECTED` (with `DATE_INVALID` folded into one of
> them and a documented precedence), and add `expired`/`rejected` counters beside `problems`.

**RULING: hacelo ahora.** El plan afirmó conformidad con el §7 para un modelo de estados que no
coincide con el §7 — un defecto del plan, no de la implementación. Se hace ahora y no después
porque hoy `fitness.py` no tiene ningún consumidor: partir `PROBLEM` más adelante significa
cambiar el motor, sus tests y el endpoint del plan 3 al mismo tiempo.

Concretamente:

- Partí `DiverState.PROBLEM` en `EXPIRED` y `REJECTED`.
- `DATE_INVALID` se pliega dentro de `EXPIRED`, **con la precedencia documentada en un
  comentario**: una fecha inválida es en la práctica un documento que no sirve para esta
  ventana, igual que uno vencido.
- Si un buzo tiene un estudio vencido y otro rechazado, **gana `REJECTED`**, porque el rechazo
  trae un motivo que el buzo tiene que leer para arreglarlo, mientras que "vencido" se explica
  solo. Documentá esa precedencia en un comentario también.
- Agregá contadores `expired` y `rejected` en `DiverSummary`, **dejando `problems`** como la
  suma de los dos: el §8.1 pide "cuántos vencidos" en particular, y el total sigue siendo útil.
- Los tests existentes (`test_fitness.py:399-401, 463, 472`) codifican la versión del plan y hay
  que cambiarlos. No los borres: adaptalos y agregá uno por cada estado nuevo, más uno para la
  precedencia rechazado-sobre-vencido.

---

## 4. (Important) La migración 0013 se aborta sobre cualquier base que ya tenga un rechazo

> `api/migrations/0013_...py` adds `rejection_has_reason_and_detail`, which requires every
> `status='REJECTED'` row to have a non-empty `rejection_reason`. `rejection_reason` was only
> introduced in `0010` as `blank=True` with no default and **no data step**, so every
> pre-existing rejection has `rejection_reason=''` and violates the constraint the moment it is
> added. Both SQLite and Postgres validate existing rows when adding a check constraint, so the
> migration fails and the deployment stops half-applied. This is **not** the already-recorded
> `0008`/`0009` risk — that one is about `StudyBlock`; this is a second, independent
> data-migration gap on `Comment`.

**RULING: escribí las dos migraciones de datos ahora.** Veníamos difiriendo esto al primer
despliegue, pero el revisor mostró que el problema no es "datos mal etiquetados" sino que **el
`migrate` se corta a mitad de camino**, y las dos reglas de relleno son deterministas, no
adivinanzas.

Una migración nueva, ubicada **antes** de las constraints que la necesitan (puede que tengas que
reordenar dependencias; si eso resulta imposible sin reescribir una migración existente, pará y
reportá NEEDS_CONTEXT en vez de reescribirla):

- **`Comment`**: para toda fila con `status='REJECTED'` y `rejection_reason=''`, poner
  `rejection_reason='OTHER'`; y si `content` está vacío, poner un texto en castellano y en
  registro impersonal que diga claramente que el motivo no quedó registrado en el sistema
  anterior.
- **`StudyBlock`**: para cada `(user, study_code)` con más de una fila en `is_current=True`,
  dejar vigente sólo la de `study_date` más reciente (desempatando por `pk` más alto) y degradar
  las demás. Eso es exactamente lo que la constraint parcial exige.

**Lo que NO hay que intentar arreglar:** que la migración 0008 haya etiquetado todo estudio
preexistente como punto "g" (odontológico). No hay manera de saber qué estudio era cada subida
de texto libre, y adivinar sería inventar datos médicos. Eso sigue necesitando triage humano.
Tu migración tiene que hacer que el `migrate` **no falle**, no que los datos queden correctos.

Hacelas idempotentes y con un `reverse_code` que no rompa. Si podés testearlas sin inventar
andamiaje raro, hacelo; si no, decilo en el informe y explicá cómo las verificaste a mano.

---

## 5. (Minor, pero lo ve el usuario) Las etiquetas de rol están a medio traducir

> `users/models.py:5-10` — `('USER','User')`, `('DOCTOR','Doctor')`, `('ADMIN','Admin')` sit
> beside `('NURSE','Enfermero auxiliar')`. The plan's own Global Constraints say §10 applies in
> this plan "a las etiquetas de `choices`", and the Django admin — the only human interface this
> branch ships — is where the unit's officer designates roles. §5 names them Buzo / Enfermero
> auxiliar / Médico / Admin. "User" does not read as "buzo" to anyone.

Poné `'Buzo'`, `'Enfermero auxiliar'`, `'Médico'`, `'Administrador'`. **No cambies los valores**
(`USER`/`NURSE`/`DOCTOR`/`ADMIN`), sólo las etiquetas. Necesita migración nueva.

---

## 6. (Minor) 150 consultas de más en la única lista que el spec pide que sea cómoda

> `users/admin.py:8-21` — `last_name`, `first_name` and `email` each dereference `obj.user`, and
> there is no `list_select_related`. §8.5 asks the admin to collate 150 people against his own
> personnel records. Fix: `list_select_related = ('user',)`.

Aplicalo.

---

## 7. (Minor) `habilitation_year` es la única regla consecuente que la suite no fija

> `api/fitness.py:134-136` — Mutating `end_date.year` to `start_date.year` leaves all 108 tests
> green, because no fixture window crosses a calendar year (the complementaria fixture is 12-14
> July 2027, same year both ends). `end_date` is the correct, conservative reading of §15.16; it
> is simply unproven. One test with a 30 Dec - 2 Jan window closes it.

Agregá ese test: una ventana del 30 de diciembre al 2 de enero y un buzo cuya edad cambia entre
los dos años. El conjunto de estudios exigidos tiene que salir del año de `end_date`.

---

## 8. (Minor) `TIME_ZONE = 'UTC'` corre un día la columna "Última vez revisado"

> `settings.py:125` — `fitness.py:272` correctly uses `timezone.localtime(...).date()` — the
> engine is right, the setting is wrong. A dictamen signed at 22:00 in Buenos Aires (UTC-3)
> records as the following day in the doctor's column. Pre-existing setting, but this branch
> introduced the first derivation of a *calendar day* from a timestamp, so it now has a visible
> consequence.

Poné `TIME_ZONE = 'America/Argentina/Buenos_Aires'`. Dejá `USE_TZ = True` como está: los
timestamps siguen guardándose en UTC y esto sólo cambia cómo se derivan los días calendario.

---

## 9. (Minor) El viewset sigue sirviendo los estudios históricos

> `api/views.py:63-91` — `StudyBlockViewSet.get_queryset` does not filter `is_current`, so every
> caller now receives the replacement *and* its history, against §6 ("no visible en la vista
> normal"). The branch created the distinction and left no consumer honouring it.

**RULING: arreglalo acá, no en el plan 2.** Es código de backend que esta rama creó y dejó sin
respetar su propia distinción.

Filtrá `is_current=True` por defecto. Dejá además una manera explícita de pedir el histórico (un
query param tipo `?historico=1`), **sin construir pantalla ninguna** — el plan 2 lo va a
necesitar y una línea ahora evita que tenga que volver sobre este archivo. Un test por cada
camino.

---

## 10. (Minor) `StudyBlock.save()` guarda un `title` vacío para un código fuera del catálogo

> `api/models.py:29-31` — silently stores an empty `title` for an off-catalog `study_code`
> instead of refusing it. The serializer validates choices, so the API is safe; the shell and
> the seed are not.

Que falle en vez de guardar vacío. Un `study_code` fuera de `catalog.CODES` es un error de
programación, no un dato del usuario, así que levantar es correcto.

---

## 11. (Minor) Un test cuyo nombre no coincide con su fixture

> `test_presented_counts_rejected_and_expired_as_presented` (`test_fitness.py:403-405`) has no
> expired study in its fixture despite the name. [...] the name/fixture mismatch [...] is the
> kind of thing that later gets trusted for a guarantee it never made.

Agregale un estudio vencido al fixture para que el nombre sea verdad.

Los otros dos tests débiles que el revisor nombró (`test_an_incomplete_cycle_is_normal` y
`test_a_single_day_window_is_valid`) **dejalos como están**: son de bajo valor pero no son
vacuos, y ya están registrados como diferidos.

---

## 12. (Minor) Borrar una ventana des-inscribe en silencio a todos sus buzos

> `UserProfile.habilitation_window` is `on_delete=SET_NULL` (`users/models.py:49-52`), so an
> admin deleting a mis-entered window silently un-enrols every diver on it, with no trace, and
> `test_habilitation_window.py:81-93` pins that as intended. `PROTECT` would make the admin fix
> the dates instead of losing 50 enrolments.

**RULING: cambialo a `PROTECT`.** El administrador acá es un oficial de la unidad, no un
desarrollador, y perder 50 inscripciones sin rastro es peor que recibir un "corregí las fechas
en vez de borrar". Además el §4.1 dice que las fechas no se conocen de antemano y se completan
después, o sea que el flujo real es **editar**, no borrar y recrear. Con `PROTECT`, borrar una
ventana recién creada por error sigue funcionando mientras no haya nadie inscripto, que es justo
cuando borrar es inofensivo.

Hay que cambiar el test que fija el comportamiento actual (`test_habilitation_window.py:81-93`):
que asserte que borrar una ventana con buzos inscriptos levanta `ProtectedError`, y que borrarla
sin nadie inscripto funciona.

---

## Lo que NO entra en esta ronda

No toques nada de esto; ya está decidido:

- **El etiquetado "g" de la migración 0008**: necesita triage humano con los datos a la vista.
- **Ítem 10 del revisor** (reemplazar un estudio borra la revisión del médico sobre el anterior):
  **RULING: se queda así.** La subida nueva genuinamente no está revisada, y que el buzo salte
  al tope de la cola de "sin revisar" es exactamente lo que el médico necesita ver.
- **Ítem 11 del revisor** (derivación duplicada de ventana y edad): diferido; ambos caminos están
  testeados y comparten `_codes_for_age`.
- **Ítem 12 del revisor** (ventanas superpuestas, ciclo con fechas contradictorias): diferido al
  plan 4, que construye la pantalla de carga de fechas y es donde vive esa validación.
- `reviewer_role` derivado del servidor, y los 500 en vez de 400: ya diferidos al plan 3.
- `DEBUG` y `/media/`: diferidos a pedido explícito del dueño.
- Todo el frontend.
