# Informe de las correcciones de la revisión final — rama `nicolas/primer-cambio`

**Estado: DONE_WITH_CONCERNS.** Los doce ítems están hechos. La única
preocupación es consecuencia del ítem 4 y está en la sección "Concerns": la base
de desarrollo necesita una reconciliación manual de una sola vez, de dos líneas,
que no pude aplicar yo porque el entorno me denegó el permiso para escribir en
`db.sqlite3`.

- **Tests: 154 pasan** (eran 108). Ninguno falla, ninguno se saltea.
- **`makemigrations --check --dry-run`: "No changes detected"** (ver el detalle
  en el ítem 4: hay que correrlo contra una base limpia, y por qué).
- Los tres *warnings* de `allauth` siguen ahí; son preexistentes.

## Commits

| SHA | Asunto | Ítems |
|---|---|---|
| `8319f99` | `fix(api): reject a study dated in the future, not only after the window` | 1 |
| `82b22e8` | `fix(api): nadie dictamina sobre sus propios estudios (spec 15.9)` | 2 |
| `05c7db8` | `refactor(api): partir DiverState.PROBLEM en EXPIRED y REJECTED (spec 7)` | 3 |
| `39fa770` | `fix(api): migraciones de datos antes de las constraints que las necesitan` | 4 |
| `f8248b6` | `fix(users): etiquetas de rol en castellano, list_select_related y zona horaria` | 5, 6, 8 |
| `2149be6` | `test(api): fijar habilitation_year con una ventana que cruza el año` | 7, 11 |
| `5d3b9f8` | `fix(api): la vista normal no sirve el historial, y save() rechaza un codigo fuera del catalogo` | 9, 10 |
| `37aaf4f` | `fix(users): PROTECT la ventana de habilitacion con buzos inscriptos` | 12 |
| `6cc290b` | `docs(api): corregir el docstring de DiverState y quitar PROBLEM_STATES sin uso` | autorrevisión |

---

## Ítem por ítem

### 1. (Important) El estudio con fecha futura puede dejar a un buzo APTO — HECHO

**Qué hice.** En `backend/api/fitness.py`, `_study_state()` compara la fecha del
estudio contra `min(today, window.end_date)` en lugar de sólo contra
`window.end_date`. Agregué la regla 5 al docstring del módulo, para que no
parezca contradecir la regla 1 ("la vigencia no se mide contra hoy"): `today` no
entra en la vigencia, entra como techo de la fecha que el buzo declara.

**Archivos.** `backend/api/fitness.py`, `backend/api/tests/test_fitness.py`.

**Tests que lo cubren** (todos en `test_fitness.py`):

- `test_a_study_dated_in_the_future_but_inside_the_window_is_not_trusted` — el
  caso concreto del revisor: ventana complementaria 12-14/07/2027, estudio
  fechado 15/01/2027, hoy 03/11/2026.
- `test_a_future_dated_study_cannot_leave_the_diver_apto` — el mismo peligro a
  nivel de buzo, en una variante que **sin el arreglo produce APTO**: el buzo
  cargó el ecocardiograma hecho el 15/11/2025 (vence el 15/11/2026, antes del
  cierre del 20) pero tipeó el año corriente, 15/11/2026. Esa fecha cae dentro
  del rango, su vigencia llega hasta 2027, y los otros seis puntos están
  aprobados: sin el tope de hoy el buzo sale APTO con un papel que ya no cubre
  su fecha. Elegí esta variante en lugar de la complementaria literal del
  revisor porque con la ventana de julio de 2027 el Anexo 27 todavía está en
  `BEFORE_WINDOW` el 03/11/2026, así que el buzo no podría estar APTO y el test
  no demostraría el peligro. El estado del punto sí está fijado con la ventana
  complementaria exacta, en el test anterior.
- `test_a_study_dated_today_is_trusted` — el borde por el otro lado.
- `test_a_study_dated_tomorrow_is_not_trusted`.
- `test_a_study_dated_after_a_window_that_already_passed_is_not_trusted` — fija
  la otra mitad del `min` (ver "Bordes").

**TDD.**

- **RED:** `manage.py test api.tests.test_fitness` →
  `FAILED (failures=3)`, las tres con
  `AssertionError: <StudyState.APPROVED: 'APPROVED'> != <StudyState.DATE_INVALID: 'DATE_INVALID'>`.
  Es el fallo esperado: sin el tope de hoy el punto sale aprobado.
- **GREEN:** `manage.py test` → `Ran 113 tests in 0.843s / OK`.

**Mutación (la que pidió el ítem).** `latest_trusted_date = min(today,
window.end_date)` → `= window.end_date`:
`FAILED (failures=3)` — los tres tests de fecha futura.
Mutación inversa, `= today` (quita la otra mitad del `min`):
`FAILED (failures=1)` — `test_a_study_dated_after_a_window_that_already_passed_is_not_trusted`.
Las dos mitades del borde quedan fijadas por separado.

**Test existente que hubo que adaptar.**
`test_a_study_dated_on_the_last_day_of_the_window_is_valid` usaba `study_date =
20/11/2026` con `today = 03/11/2026`, o sea una fecha futura: con el arreglo
pasaba a `DATE_INVALID`. Le puse `today = 20/11/2026`, que conserva exactamente
su intención (el borde de `end_date` es inclusivo) y además la hace medible: el
borde de `end_date` sólo se puede observar cuando ese día llegó, porque antes
manda el tope de hoy. Queda documentado en el comentario del test.

### 2. (Important) El spec §15.9 no existe en el código — HECHO

**Qué hice.** Dos líneas al principio de `Comment.clean()`
(`backend/api/models.py`): si `self.block_id` está y `self.doctor_id ==
self.block.user_id`, error en la clave `doctor`. **No** agregué CheckConstraint,
como indicaba el ítem, y el comentario del código dice por qué (haría falta un
join, que SQLite no admite dentro de un CHECK).

**Mensaje.** `'Nadie puede dictaminar sobre sus propios estudios.'` — registro
impersonal, no se dirige al lector.

**Archivos.** `backend/api/models.py`, `backend/api/tests/test_dictamen.py`.

**Tests que lo cubren.**

- `test_nobody_may_rule_on_their_own_study` — assertea `list(errors) ==
  ["doctor"]` **y** el texto exacto vía `message_dict`. La clave única es
  deliberada: el dictamen del fixture es válido en todo lo demás
  (`APPROVED`+`DOCTOR`), así que el test no puede pasar porque otro campo
  obligatorio haya levantado.
- `test_a_nurse_may_not_pre_approve_their_own_study_either`.
- `test_rejecting_ones_own_study_is_refused_too`.
- `test_ruling_on_someone_elses_study_stays_allowed` — el contrapunto: la regla
  no bloquea el caso normal.

**TDD.**

- **RED:** `manage.py test api.tests.test_dictamen` → `FAILED (failures=3)`,
  las tres con `AssertionError: ValidationError not raised`.
- **GREEN:** `manage.py test` → `Ran 117 tests in 0.854s / OK`.

**Mutación.** La condición → `if False:`: `FAILED (failures=3)`.

### 3. (Important) `DiverState` fundía "Vencido" y "Rechazado" — HECHO

**Qué hice** (`backend/api/fitness.py`):

- `DiverState.PROBLEM` partido en `REJECTED` y `EXPIRED`.
- `PROBLEM_STATES` reemplazado por dos conjuntos disjuntos, `REJECTED_STATES` y
  `EXPIRED_STATES`.
- `DiverSummary` gana `expired` y `rejected`, y **conserva** `problems`,
  calculado como `expired + rejected` para que la relación esté a la vista en el
  código y no sólo en el comentario.
- `_diver_state()` evalúa `REJECTED_STATES` y después `EXPIRED_STATES`.

**La precedencia que implementé, y dónde está documentada en el código.**

| Decisión | Dónde está el comentario |
|---|---|
| `DATE_INVALID` se pliega en `EXPIRED`, no en `REJECTED` — un papel mal fechado es, en la práctica, un documento que no cubre el rango, igual que uno vencido, y tampoco lleva un motivo que alguien tenga que leer | comentario `#:` sobre `EXPIRED_STATES`, `fitness.py` |
| Rechazado gana sobre vencido — el rechazo trae un motivo que el buzo tiene que leer para arreglarlo; "vencido" se explica solo | comentario dentro de `_diver_state()`, justo arriba de las dos guardas, `fitness.py` |
| `problems` sigue siendo el total de los dos | comentario `#:` sobre el campo `problems` de `DiverSummary`, que cita el §8.1 y el §13 |

También corregí el docstring de `_diver_state()`, que afirmaba "Orden de
evaluación del spec (§7)" para un modelo que no era el del §7 — la afirmación
falsa que el revisor señaló. Ahora dice qué fija el §7 y remite al comentario de
la precedencia.

**Tests existentes adaptados** (ninguno borrado):

- `test_a_rejection_outranks_an_incomplete_set` → `DiverState.REJECTED`.
- `test_the_counters_split_the_required_points_by_state` → `DiverState.REJECTED`
  (el fixture tiene un rechazado, un vencido y uno mal fechado), más
  `rejected == 1`, `expired == 2` y `problems == rejected + expired`.
- `test_an_expired_point_is_a_problem_even_with_everything_uploaded` →
  `DiverState.EXPIRED`, más `expired == 1` y `rejected == 0`.
- `test_a_future_dated_study_cannot_leave_the_diver_apto` (del ítem 1) →
  `DiverState.EXPIRED`.

**Tests nuevos:**

- `test_a_rejected_point_reports_rejected_not_expired` — el estado nuevo
  `REJECTED`.
- `test_an_invalid_date_alone_reports_expired` — el estado nuevo `EXPIRED` y el
  plegado de `DATE_INVALID` dentro de él.
- `test_a_rejection_outranks_an_expiry` — la precedencia rechazado-sobre-vencido,
  con un estudio de cada uno.
- `test_a_diver_with_no_problem_counts_nothing_as_a_problem` — los tres
  contadores en cero.

**TDD.**

- **RED:** `manage.py test api.tests.test_fitness` → `FAILED (errors=8)`;
  la causa, verificada en un test aislado, es
  `AttributeError: type object 'DiverState' has no attribute 'REJECTED'`.
- **GREEN:** `manage.py test` → `Ran 121 tests in 0.892s / OK`.

**Mutaciones (tres, una por decisión):**

| Mutación | Resultado |
|---|---|
| Precedencia invertida (`EXPIRED` antes de `REJECTED`) | `FAILED (failures=2)`: `test_a_rejection_outranks_an_expiry`, `test_the_counters_split_the_required_points_by_state` |
| `DATE_INVALID` movido a `REJECTED_STATES` | `FAILED (failures=3)`: `test_an_invalid_date_alone_reports_expired`, `test_a_future_dated_study_cannot_leave_the_diver_apto`, `test_the_counters_split_the_required_points_by_state` |
| `problems = expired` (deja de ser la suma) | `FAILED (failures=3)`: `test_a_rejected_point_reports_rejected_not_expired`, `test_a_rejection_outranks_an_expiry`, `test_the_counters_split_the_required_points_by_state` |

**Consecuencias en otros consumidores.** Ninguno: busqué `DiverState` y
`PROBLEM` en todo el backend y el frontend, y no hay un solo consumidor fuera de
`fitness.py` y sus tests. Era exactamente la razón del RULING. La siembra
(`create_test_data.py`) imprime `summary.state.value` y `summary.problems`, que
siguen existiendo, así que **no se rompió**; igual le agregué las dos columnas
nuevas (`venc`, `rech`) a su tabla de verificación, porque ahora los buzos
`vencido` y `rechazo` producen estados distintos y conviene verlo. **No la
corrí.**

### 4. (Important) La migración 0013 se aborta sobre cualquier base con un rechazo — HECHO

**Dónde ubiqué las migraciones de datos.** Dos migraciones nuevas, y **ninguna
migración existente tocada**. La clave es `run_before`, que es una propiedad de
la migración *nueva*: declara "yo tengo que correr antes que aquélla" sin
editarla.

| Migración nueva | `dependencies` | `run_before` | Posición real |
|---|---|---|---|
| `api/0014_demote_duplicate_current_studies.py` | `0008` (que crea `is_current` y `study_code`) | `0009` (el índice único parcial) | entre 0008 y 0009 |
| `api/0015_backfill_rejection_reason_and_detail.py` | `0010` (que crea `rejection_reason`) | `0013` (la CHECK) | entre 0010 y 0013 |

Son dos y no una porque los dos rellenos no caben en el mismo lugar del grafo:
el de `StudyBlock` tiene que correr antes de `0009`, y el de `Comment` necesita
un campo que recién aparece en `0010`, después de `0009`.

Los números de archivo son los siguientes libres, como pide la convención de
`makemigrations`; el orden real lo fijan las dependencias. `showmigrations api`
sobre una base limpia lo confirma:

```
[X] 0008_studyblock_is_current_studyblock_study_code
[X] 0014_demote_duplicate_current_studies
[X] 0009_studyblock_one_current_study_per_diver_and_point
[X] 0010_comment_rejection_reason_comment_reviewer_role_and_more
[X] 0015_backfill_rejection_reason_and_detail
[X] 0011_alter_comment_reviewer_role
[X] 0012_alter_comment_status
[X] 0013_comment_verdict_matches_reviewer_role_and_more
```

**Las dos reglas, tal cual el RULING.**

- `Comment`: `status='REJECTED'` con `rejection_reason=''` → `'OTHER'` (que es
  justamente el motivo "Otros" del catálogo de la directiva); y si `content`
  está vacío, el texto `MISSING_DETAIL`: *"El motivo de este rechazo no quedó
  registrado en el sistema anterior. Se solicita consultar en el servicio de
  sanidad antes de volver a presentar el estudio."* — castellano, registro
  impersonal, y dice que el motivo no quedó registrado en vez de inventar uno.
  Los campos que ya tenían valor no se pisan.
- `StudyBlock`: por cada `(user, study_code)` con más de una fila
  `is_current=True`, queda vigente la de `study_date` más reciente, desempatando
  por `pk` más alto, y las demás se degradan. Nada se borra.

**Idempotencia y reverso.** Las dos filtran por el valor que van a reemplazar
(`rejection_reason=''`, `content=''`, grupos con `n > 1`), así que a la segunda
corrida no encuentran nada. El `reverse_code` de las dos es
`migrations.RunPython.noop`, y el comentario dice por qué: no queda registro de
qué filas se tocaron, y deshacerlo rompería la misma constraint que la migración
existe para no romper. Revertir no falla.

**Lo que NO intenté arreglar**, como indicaba el ítem: el etiquetado "g" de
`0008`. Está dicho explícitamente en el docstring de `0014`, junto con su
consecuencia práctica (sobre datos reales, "dos cargas del mismo punto" va a ser
casi siempre "dos cargas cualesquiera del mismo buzo"), y que eso sigue
necesitando triage humano.

**Un hallazgo de paso: la otra CHECK de `0013` no necesita relleno.** Verifiqué
`verdict_matches_reviewer_role`: antes de `0010` los únicos estados que existían
eran `APPROVED` y `REJECTED` (migración `0002`), y `0010` agregó `reviewer_role`
con `default='DOCTOR'`, así que toda fila preexistente queda en
`APPROVED`+`DOCTOR` o en `REJECTED`, y las dos satisfacen la CHECK. Queda
documentado en el docstring de `0015`, para que nadie vuelva a preguntárselo.

**Sí pude testearlas, y sin andamiaje raro.**
`backend/api/tests/test_data_migrations.py`, **18 tests**. Primero intenté
probar las funciones directamente quitando las constraints con `schema_editor`
sobre el modelo vivo, y **no sirve**: en SQLite, quitar una `CheckConstraint`
rehace la tabla a partir de `model._meta`, que todavía las tiene, así que las
repone. Lo descarté y usé el ejecutor de migraciones de verdad, que además
prueba más:

- Una clase base `MigrationTestCase` lleva la base al estado anterior a la
  constraint, da los modelos históricos de ese estado, y en `tearDown` devuelve
  la base al final del grafo.
- Los modelos históricos no llevan métodos, así que crear varias filas
  `is_current=True` sale naturalmente — es exactamente el estado que dejó `0008`
  en producción.
- **El contrafactual**, que es lo que prueba que estos tests pueden fallar:
  `test_without_the_demotion_the_migrate_breaks` y
  `test_without_the_backfill_the_migrate_breaks` vacían las `operations` de la
  migración de relleno con `mock.patch.object` y corren el mismo `migrate`.
  Las dos asertean que levanta `IntegrityError`/`OperationalError`: es el
  hallazgo del revisor, reproducido.
- `MigrationOrderTests` (4 tests) lee el grafo real y fija que cada relleno corre
  antes de su constraint y después del campo que lee.

**Verificación extra a mano.** Sobre una base vacía descartable: las **60
migraciones aplican OK** en secuencia, con `0014` y `0015` en su lugar; una
segunda corrida de `migrate` no hace nada y no falla.

**La consecuencia que el documento no anticipó.** Ver "Concerns".

### 5. (Minor) Las etiquetas de rol a medio traducir — HECHO

`backend/users/models.py`: `'Buzo'`, `'Enfermero auxiliar'`, `'Médico'`,
`'Administrador'`. **Los valores no se tocaron.** Migración nueva
`users/0005_role_labels_in_spanish.py`.

Test: `users.tests.test_the_role_labels_are_the_ones_the_spec_names`, que
assertea el dict completo (así no se puede quedar a medias otra vez).
Mutación: `('USER', 'User')` → `FAILED (failures=1)`.

### 6. (Minor) 150 consultas de más en el listado del admin — HECHO

`backend/users/admin.py`: `list_select_related = ('user',)`.
Test: `users.tests.test_the_admin_list_does_not_dereference_user_row_by_row`.
Mutación: línea comentada → `FAILED (failures=1)`.

### 7. (Minor) `habilitation_year` sin fijar — HECHO

Test nuevo `test_a_window_crossing_new_year_uses_the_year_of_its_last_day`
(`test_fitness.py`): ventana del **30/12/2026 al 02/01/2027** y un buzo nacido
en 1987, que **cambia de edad entre los dos años** (39 en 2026, 40 en 2027). El
test assertea las tres cosas: `habilitation_year(crossing) == 2027`, las dos
edades, y que el conjunto exigido sale del año de `end_date` —
`tuple("abcdefgh")`, los ocho.

**Mutación (la exacta que nombró el revisor).** `return window.end_date.year` →
`window.start_date.year`: `FAILED (failures=1)`, el test nuevo. Antes de este
test esa mutación dejaba los 108 verdes.

### 8. (Minor) `TIME_ZONE = 'UTC'` corre un día la columna — HECHO

`backend/core/settings.py`: `TIME_ZONE = 'America/Argentina/Buenos_Aires'`.
`USE_TZ` queda en `True`, y el comentario dice que los timestamps se siguen
guardando en UTC y que esto cambia sólo de qué día calendario se derivan.

Test `test_last_doctor_review_is_the_calendar_day_in_buenos_aires`: un dictamen
guardado como `2026-10-28 01:00 UTC` (22:00 del 27 en Buenos Aires) tiene que
reportar `last_doctor_review == 2026-10-27`.
Mutación: `TIME_ZONE = 'UTC'` → `FAILED (failures=1)`.

### 9. (Minor) El viewset seguía sirviendo los estudios históricos — HECHO

`backend/api/views.py`, `StudyBlockViewSet.get_queryset`: filtra
`is_current=True` salvo que venga `?historico=1`. El filtro se aplica **después**
de unir lo propio con lo compartido, así que vale para los dos caminos. **Sin
pantalla ninguna**, como pedía el ítem.

Tests nuevos en `backend/api/tests/test_study_block_api.py` (7), con un fixture
de una carga vigente y su reemplazada:

- `test_the_fixture_really_has_one_current_and_one_replaced` — el fixture dice
  lo que el resto da por hecho.
- `test_the_normal_view_serves_only_the_current_upload`.
- `test_the_history_can_be_asked_for_explicitly`.
- `test_any_other_value_of_the_parameter_keeps_the_normal_view` (`historico=0`,
  vacío, `si`, y otro parámetro).
- `test_a_point_with_a_single_current_upload_is_served_either_way`.
- `test_another_divers_uploads_are_not_served`.
- `test_a_shared_history_is_filtered_the_same_way` — el filtro no se escapa por
  la rama de lo compartido.

**TDD.** RED: `FAILED (failures=6)`, el historial se filtraba por los dos
caminos. GREEN: `Ran 150 tests / OK`.
**Mutaciones (los dos sentidos):** condición → `if False:` (nunca filtra):
`FAILED (failures=6)`. Condición → `if True:` (el parámetro no hace nada):
`FAILED (failures=2)`.

### 10. (Minor) `StudyBlock.save()` guardaba un `title` vacío — HECHO

`backend/api/models.py`: `save()` levanta `ValueError` si `study_code` no está
en `catalog.CODES`, con el código y la lista de los ocho en el mensaje. El
comentario dice por qué levantar es lo correcto (error de programación de la
consola o de la siembra, no un dato del usuario).

Tests: `test_saving_an_off_catalog_code_refuses_instead_of_storing_a_blank`
(assertea el `ValueError`, que el código aparece en el mensaje, y que no quedó
ninguna fila) y `test_every_catalog_code_still_saves` como contrapunto — la
guarda no bloquea los ocho códigos reales y el `title` sigue saliendo del
catálogo.
Mutación: volver a guardar en silencio con `title=''` → `FAILED (failures=1)`.

### 11. (Minor) Un test cuyo nombre no coincidía con su fixture — HECHO

El fixture de `test_presented_counts_rejected_and_expired_as_presented` ahora
tiene de verdad un estudio vencido: el punto `c` pasa a `19/11/2025`, que vence
el 19/11/2026 y no cubre el cierre del 20. Renombré el helper a
`_summary_all_uploaded_one_rejected_and_one_expired` y el test ahora assertea
los dos estados del fixture antes de contar, así que el nombre no puede volver a
mentir.
Mutación: `presented` contando sólo aprobados → `FAILED (failures=2)`.

Los otros dos tests débiles (`test_an_incomplete_cycle_is_normal` y
`test_a_single_day_window_is_valid`) quedaron **como estaban**, según el ítem.

### 12. (Minor) Borrar una ventana des-inscribía en silencio — HECHO

`backend/users/models.py`: `on_delete=models.PROTECT`. Migración nueva
`users/0006_protect_window_with_divers.py`.

El test que fijaba el comportamiento viejo
(`test_diver_enrolment_is_optional_and_cleared_when_window_is_deleted`) quedó
reemplazado por tres, con el fixture extraído a un helper que conserva la
aserción de que la inscripción es opcional:

- `test_deleting_a_window_with_divers_on_it_is_refused` — `ProtectedError`, la
  ventana sigue existiendo y el buzo sigue inscripto.
- `test_deleting_a_window_with_nobody_on_it_still_works` — borrar una ventana
  recién creada por error sigue funcionando.
- `test_a_window_is_deletable_once_its_divers_un_enrol`.

Mutación: volver a `SET_NULL` → `FAILED (failures=1)`.

**Verificado que no rompe la siembra:** `create_test_data.py` borra *usuarios*
(que cascadean a `UserProfile`) y hace *upsert* de la ventana; nunca borra una
`HabilitationWindow`. `PROTECT` protege el objeto referenciado, no el que
referencia.

---

## Bordes: inclusivo o exclusivo (ítems 1 y 7)

| Borde | Decisión | Qué lo fija |
|---|---|---|
| Fecha del estudio contra el techo de confianza | `study_date > min(today, end_date)` → inválida. **El día del tope sirve, el siguiente no** (comparación estricta) | `test_a_study_dated_today_is_trusted` / `test_a_study_dated_tomorrow_is_not_trusted` |
| Fecha del estudio contra el fin de la ventana | `end_date` es **inclusivo**: un estudio fechado el último día del rango vale | `test_a_study_dated_on_the_last_day_of_the_window_is_valid` (con `today` en ese día) / `test_a_study_dated_one_day_after_the_window_is_already_not_trusted` |
| Fecha del estudio contra una ventana ya cerrada | manda `end_date`, no `today`: el 25/11 no sirve para una ventana que cerró el 20, aunque hoy sea el 1/12 | `test_a_study_dated_after_a_window_that_already_passed_is_not_trusted` |
| Año de la habilitación | el del **último día** del rango, y `end_date` es un día de la ventana (inclusivo). Una ventana que cruza el año se juzga por el año posterior, que es el que suma exigencia (§15.16) | `test_a_window_crossing_new_year_uses_the_year_of_its_last_day` |

Los dos topes del `min` quedan fijados **por separado**, cada uno con su propia
mutación (ver ítem 1): no hay una mitad que la suite no pruebe.

---

## Resumen de las mutaciones

Dieciséis mutaciones, dieciséis atrapadas. Ninguno de los tests nuevos resultó incapaz
de fallar.

| # | Mutación | Ítem | Resultado |
|---|---|---|---|
| 1 | `min(today, end_date)` → `end_date` | 1 | 3 fallos |
| 2 | `min(today, end_date)` → `today` | 1 | 1 fallo |
| 3 | guarda del auto-dictamen → `if False` | 2 | 3 fallos |
| 4 | precedencia invertida (`EXPIRED` primero) | 3 | 2 fallos |
| 5 | `DATE_INVALID` movido a `REJECTED_STATES` | 3 | 3 fallos |
| 6 | `problems = expired` | 3 | 3 fallos |
| 7 | `operations` de `0014` vaciadas | 4 | el `migrate` levanta (es el test) |
| 8 | `operations` de `0015` vaciadas | 4 | el `migrate` levanta (es el test) |
| 9 | `('USER', 'Buzo')` → `'User'` | 5 | 1 fallo |
| 10 | `list_select_related` quitado | 6 | 1 fallo |
| 11 | `end_date.year` → `start_date.year` | 7 | 1 fallo |
| 12 | `TIME_ZONE` → `'UTC'` | 8 | 1 fallo |
| 13 | filtro `is_current` → `if False` / `if True` | 9 | 6 y 2 fallos |
| 14 | `title=''` en silencio para código fuera del catálogo | 10 | 1 fallo |
| 15 | `presented` cuenta sólo aprobados | 11 | 2 fallos |
| 16 | `PROTECT` → `SET_NULL` | 12 | 1 fallo |

(Dieciséis en total; las dos del ítem 4 son contrafactuales que quedaron
*dentro* de la suite, así que no hay que volver a correrlas a mano.)

---

## Autorrevisión del diff

Leí el diff completo con ojos nuevos. Dos hallazgos, los dos arreglados en
`6cc290b`:

1. **El docstring de `DiverState` decía "Son los seis del §7, uno por uno"** y
   el enum tiene siete miembros. La tabla del §7 lista seis; `UNKNOWN_AGE` es
   un séptimo que el spec no lista porque da la fecha de nacimiento por
   cargada, y acá es nullable. Era la misma clase de error que el ítem 3 vino a
   corregir — una afirmación de conformidad con el §7 que no cerraba — así que
   lo corregí en vez de dejarlo pasar. Ahora el docstring nombra los seis y dice
   por qué hay un séptimo.
2. **`PROBLEM_STATES` quedó sin ningún consumidor** al pasar `problems` a
   `expired + rejected`: código muerto. Lo saqué y moví su comentario arriba de
   los dos conjuntos que lo reemplazaron, que dice que son disjuntos y que su
   total es `DiverSummary.problems`.

Otras cosas que verifiqué y no hacía falta cambiar:

- Ningún import quedó sin usar (los dos que detecta un escaneo AST son
  `from __future__ import annotations` y un `settings` preexistente en
  `views.py`, ajeno a este diff).
- Ningún consumidor de `DiverState.PROBLEM` quedó en el backend ni en el
  frontend.
- `Comment.clean()` no explota cuando falta `block` o `doctor`: la guarda
  `self.block_id and ...` lo cubre, y hay tests con el dictamen incompleto que
  siguen reportando sólo su propio campo.
- Los strings nuevos que ve el usuario están todos en registro impersonal: el
  del auto-dictamen, el `MISSING_DETAIL` de la migración (con una aserción
  explícita en su test de que no tutea) y las cuatro etiquetas de rol.
- **No toqué el frontend.** Ni un archivo.
- **No corrí `create_test_data.py`** ni definí `SEED_CONFIRM`.
- **No reescribí ninguna migración existente.** Las cuatro nuevas son 0014,
  0015 (api) y 0005, 0006 (users).

---

## Verificación final

```
$ cd backend && ./venv/Scripts/python.exe manage.py test
Ran 154 tests in 11.776s
OK
```

De 108 a 154 (+46). Los tres warnings de `allauth` siguen apareciendo y son
preexistentes.

```
$ PYTHONPATH=<scratchpad> DJANGO_SETTINGS_MODULE=check_settings \
    ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run
No changes detected
```

**Por qué con un settings aparte.** Contra la base de desarrollo, el comando no
llega a comprobar lo que comprueba: corta antes con
`InconsistentMigrationHistory: Migration api.0009 ... is applied before its
dependency api.0014 ... on database 'default'`. Es la consecuencia del ítem 4
(ver abajo), no una diferencia entre los modelos y las migraciones. El settings
descartable (`check_settings.py`, en el scratchpad de la sesión: sólo cambia
`DATABASES` a un archivo vacío) hace la comprobación sin historial, que es la
que el gate pide. Sobre esa base también verifiqué que **las 60 migraciones
aplican OK desde cero** y que una segunda corrida no hace nada.

---

## Concerns

**Uno, y es consecuencia directa del ítem 4.** Lo pongo entero porque el
documento de correcciones no lo anticipó.

Meter una migración *antes* de una que ya está aplicada deja el historial
"inconsistente" para Django, que entonces se niega a correr `migrate` **y**
`makemigrations` sobre esa base. Le pasa a cualquier base que haya aplicado
`0009` sin `0014` (o `0013` sin `0015`).

- **En producción no es un problema, y es justo lo que el RULING quería.** Las
  migraciones `0008`..`0013` son de esta misma rama y no llegaron a ningún
  servidor: el registro de riesgos pre-despliegue del plan (`progress.md`, PD-2
  agravado) dice textualmente que hace falta "un RunPython **previo**". Sobre la
  base real, que está en `0007` o antes, el `migrate` corre en el orden correcto
  de punta a punta. Lo verifiqué desde una base vacía.
- **En desarrollo sí, y hay que destrabarlo.** La base del desarrollador
  (`backend/db.sqlite3`) está en `0013`. Hasta que no se reconcilie, sus
  `manage.py migrate` y `makemigrations` fallan.

**La reconciliación es de una sola vez, de dos líneas, y es exacta**, porque
sobre esa base las dos migraciones no tendrían nada que hacer: verifiqué con una
consulta de sólo lectura que no hay ni un `(user, study_code)` duplicado vigente
ni un rechazo sin motivo o sin detalle — como tiene que ser, porque las
constraints ya están puestas y pasando. `migrate --fake` **no sirve**, porque lo
ataja el mismo chequeo de consistencia; hay que registrarlas a mano:

```python
# backend $ ./venv/Scripts/python.exe manage.py shell
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
r = MigrationRecorder(connection)
r.record_applied('api', '0014_demote_duplicate_current_studies')
r.record_applied('api', '0015_backfill_rejection_reason_and_detail')
```

**Intenté aplicarlo y el entorno me denegó el permiso** para escribir en la base
de desarrollo (`Modify Shared Resources`). Me pareció bien no insistir: es la
base del desarrollador y la decisión es suya. **No la toqué en nada** — ni esas
dos filas ni ninguna otra. Las mismas instrucciones quedan en el docstring de
`0014`, para quien se tope con el error sin tener este informe a mano.

La alternativa sería no usar `run_before` y meter el relleno en una migración al
final, entre un `RemoveConstraint` y un `AddConstraint`. La descarté porque **no
arregla el defecto que el revisor encontró**: sobre una base vieja, `migrate`
sigue muriendo en `0009`, antes de llegar a esa migración. Y la otra alternativa
—reescribir `0009` y `0013`— está prohibida, con razón.

**Nada más me preocupa.** Ningún ítem quedó sin hacer, ningún test quedó
saltado, y ninguno de los que escribí resultó incapaz de fallar.
