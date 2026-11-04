# SDD ledger — plan: docs/superpowers/plans/2026-11-03-cimientos-dominio-aptitud.md

Spec: docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md (leído)
Repo: C:\Users\nicol\Documents\Proyectos\anexo27-Buceo
Branch: nicolas/primer-cambio
Workspace: .superpowers/sdd/2026-11-03-cimientos-dominio-aptitud

## Setup

Ruling: trabajar en el directorio actual sobre la rama `nicolas/primer-cambio`, sin
worktree aislado — El usuario pidió explícitamente al inicio de la sesión que este
directorio fuera su entorno de pruebas; el venv (`backend/venv`) y la base SQLite
sembrada viven acá, y los pasos de verificación del plan dependen de ambos. La rama
no es `main`, así que el aislamiento respecto de la rama principal está satisfecho.
— Si está mal: los commits de implementación se mezclan con los dos commits de
documentación en la misma rama y no hay aislamiento para trabajo paralelo;
recuperable creando una rama nueva desde el commit del plan.

---

## Pre-flight conflict scan

### Pares de tareas que comparten archivo o interfaz

| Par | Produce → consume | Hallazgo |
|---|---|---|
| T1 → T4 | `catalog.CODES`, `catalog.get` → `study_code` choices y `title` | OK |
| T1 → T6 | `required_for_age(age) -> tuple[RequiredStudy,…]` → `required_codes(profile) -> tuple[str,…]` | OK, tipos distintos a propósito; T6 mapea a códigos |
| T1 → T3,T4,T5,T6 | paquete `api/tests/` (T1 borra `api/tests.py`) → todos los módulos de test de api | OK, T1 va primero |
| T2 → T3 | ambas modifican `users/models.py`; T3 agrega la FK al perfil | OK, secuencial; la migración de T3 depende de la de T2 |
| T2 → T6 | `age_in_year(year)` → cálculo del conjunto exigido | OK |
| T3 → T4,T5 | ambas modifican `api/models.py` | OK, secuencial |
| T3 → T6 | `anexo27_earliest_date`, `end_date` → vigencia y `BEFORE_WINDOW` | OK |
| T4 → T5 | `StudyBlock.study_code` → los tests de dictamen crean bloques | OK, T4 va primero |
| T4 → T6 | `study_code`, `is_current` → sólo el bloque vigente cuenta | OK |
| T5 → T6 | `status` (`PRE_APPROVED`), `reviewer_role` → `PRE_REVIEWED` y `last_doctor_review` | OK |
| T1..T6 → T7 | todo el dominio → script de datos de prueba | OK |

### Consistencia interna de cada tarea

| Tarea | Hallazgo |
|---|---|
| T1 | Consistente. |
| T2 | **Defecto:** el snippet de `users/tests.py` usa `date(…)` sin `from datetime import date`. |
| T2 | **Defecto:** la tarea quita `UserProfile.age` pero no menciona `backend/api/serializers.py`, que lista `'age'` en `UserProfileSerializer.Meta.fields`. DRF revienta al resolver el campo → `/api/profiles/` queda roto. |
| T3 | Consistente. |
| T4 | **Defecto:** `test_study_code_must_be_one_of_the_eight` llama `full_clean()` sobre un `StudyBlock` sin `title` ni `pdf_attachment`, que también son obligatorios. El test pasaría por el motivo equivocado. |
| T4 | **Defecto:** `study_code` obligatorio rompe `POST /api/blocks/`, porque `StudyBlockSerializer` no lo incluye y el frontend actual no lo manda. La sección "Lo que este plan no hace" afirma que el frontend sigue andando, lo cual es cierto sólo para lectura. |
| T5 | **Defecto:** `Comment.content` es `TextField()` obligatorio. Tres tests llaman `full_clean()` sin `content` en dictámenes que no son rechazos; dos pasarían por el motivo equivocado y `test_a_dictamen_records_who_and_with_what_role` fallaría directamente. |
| T6 | Consistente (ayudantes fijados en la auto-revisión del plan). |
| T7 | Consistente. |

### Rulings del escaneo

Ruling: agregar `from datetime import date` al snippet de tests de T2 — Es un olvido
de transcripción, no una decisión de diseño. — Si está mal: nada, el implementador lo
habría agregado solo.

Ruling: T2 también actualiza `backend/api/serializers.py` quitando `'age'` y
agregando `'birth_date'` a `UserProfileSerializer` — Sin esto el endpoint de perfiles
queda roto en cuanto se corre la migración, y el plan declara explícitamente que no
rompe lo existente. El spec §14 manda reemplazar `age` por `birth_date`, así que el
serializador tiene que seguirlo. — Si está mal: el frontend `Profile.jsx` muestra
vacío el campo de edad hasta el plan 2, que es donde se rehace esa pantalla.

Ruling: en T4, `test_study_code_must_be_one_of_the_eight` tiene que afirmar que el
error es **de `study_code`**, no sólo que se levanta un `ValidationError` — Un test
que pasa por el motivo equivocado es peor que no tenerlo: no protege nada y da
confianza falsa. Se verifica con `cm.exception.error_dict` o
`cm.exception.message_dict`. — Si está mal: nada, es un test más estricto.

Ruling: `Comment.content` pasa a `blank=True` y su obligatoriedad queda sólo en
`clean()` para los rechazos — El spec §6 pide detalle en texto libre **en los
rechazos**; una aprobación no tiene nada que comentar y hoy el modelo la obliga a
inventar texto. Sin este cambio tres tests de T5 no sirven y uno falla. — Si está
mal: se podrían guardar aprobaciones sin comentario, que es exactamente lo que el
spec describe, así que el riesgo es bajo.

Ruling: aceptar que `POST /api/blocks/` queda roto al terminar T4, y agregar
`study_code` a `StudyBlockSerializer` para que la API quede coherente — El flujo de
carga se reescribe completo en el plan 2 (carga por slot, sin desplegable), así que
arreglar el formulario viejo es trabajo que se tira. La afirmación del plan de que el
frontend sigue andando se corrige: **la lectura sigue andando, la carga no.** — Si
está mal: durante el plan 1 nadie puede subir un estudio desde la interfaz; se puede
sembrar por el script de datos de prueba y por el admin de Django.

---

## Progress

Task 1: dispatched (haiku, base 13b4391) — catálogo de los ocho estudios
Task 1: implementer DONE (commit 6c88518, 8/8 tests, full suite OK)
Task 1: task review dispatched (sonnet, diff 13b4391..6c88518)
Task 1: review clean (spec OK, quality Approved, 0 critical/important)
Task 1: warning resuelto por el controlador — los nombres de interfaz que el reviewer no
  pudo verificar (ALL, CODES, get, required_for_age, RequiredStudy) son exactamente los
  que el brief declara y los que T4 (CODES, get) y T6 (required_for_age) consumen. OK.
Task 1: warning resuelto por el controlador — `int | None` exige Python 3.10+; el venv
  del proyecto corre Python 3.14.4, verificado al armar el entorno. OK.
Task 1: minor (deferred): los tests no fijan los textos exactos de los ocho estudios ni
  los hints completos de d y f (usan assertIn y la ausencia de "CHAGAS"); un typo futuro
  en un texto pasaría. **Vale arreglarlo antes del merge** — esos strings son el spec
  hecho ejecutable (§14) y el motivo de haber movido la lista al backend.
Task 1: minor (deferred): catalog.py:76,79 líneas largas (cosmético).
Task 1: complete (commits 13b4391..6c88518, review clean, 2 minors deferidos)
Task 2: dispatched (sonnet, base 6c88518) — perfil: nacimiento, DNI, grado, roles
Task 2: implementer DONE_WITH_CONCERNS (commit a416007, 16/16 tests) — dos reservas, ambas reales
Task 2: Ruling: `dni` pasa a `unique=True, null=True, blank=True` — Con unique y default de
  cadena vacía, `UserProfileViewSet.me` (que hace get_or_create sin DNI) revienta con
  IntegrityError para el segundo usuario que abra su perfil: /api/profiles/me/ queda roto
  para todos menos el primero. El índice único ignora NULLs, así que convivien los perfiles
  sin DNI y siguen colisionando los DNI reales repetidos. La obligatoriedad del spec §5 se
  mueve al formulario de registro, que es del plan 2. — Si está mal: se puede guardar un
  perfil sin DNI hasta que el plan 2 lo exija en el registro; el admin lo ve vacío al cotejar.
Task 2: Ruling: las etiquetas de los grados pasan a ser el propio código ('SG','SG'), no
  nombres en castellano — El material de origen dio sólo los códigos y el implementador
  inventó los nombres completos; dos están casi seguro mal (SA y SI son *Sargento* Ayudante y
  *Sargento* Primero en el Ejército Argentino, no "Suboficial", y los bocetos aprobados del
  propio proyecto muestran "Sgto. Ayud." y "Sgto. 1º"). Inventar nomenclatura militar es fácil
  de errar y visible de inmediato para quien tiene ese grado. — Si está mal: el desplegable
  muestra códigos en vez de nombres completos; cambiarlo es una línea por grado cuando la
  unidad dé la redacción exacta. **Hay que preguntarle al usuario.**
Task 2: fix round 1/5 dispatched (resume, 2 rulings)
Task 2: fix round 1/5 (2 addressed, 0 open — dni nullable+unique con test del camino
  get_or_create; etiquetas de grado = código; commits a416007..2d429e3, 17/17 tests)
Task 2: nota — el implementador regeneró la migración 0003 en el lugar en vez de agregar una
  0004. Es aceptable acá porque la base de desarrollo se recrea y nada está desplegado, pero
  deja de serlo en cuanto esto corra en un servidor: a partir de ahí, migración nueva siempre.
Task 2: task review dispatched (sonnet, diff 6c88518..2d429e3, 2 commits)
Task 2: task review -> spec OK, calidad "Needs fixes", 1 Important, 3 minors
Task 2: Ruling: la normalización de DNI vacío va en `UserProfile.save()`, no en
  `validate_dni` del serializador — El reviewer encontró que `Profile.jsx` manda `dni: ''` y
  DRF no convierte '' a None en un CharField null=True, así que el primer guardado almacena ''
  y el segundo recibe 400 "already exists": mi ruling anterior sólo tapaba el camino
  get_or_create. Normalizar en el serializador cierra ese endpoint; normalizar en save() cierra
  además el admin de Django, el shell, el script de siembra y cualquier endpoint que agregue un
  plan posterior. La garantía que afirmé fue "los perfiles sin DNI conviven", y tiene que valer
  en toda escritura. — Si está mal: un DNI que alguien quiso guardar como cadena vacía queda
  NULL en vez de ''; no hay pérdida, '' nunca fue un DNI válido.
Task 2: minor (deferred): la migración 0003 no trae paso de datos de '' a NULL ni de rangos de
  texto libre a 2 caracteres. **Esto importa si alguna vez se corre sobre una base con datos
  reales** — hoy no, porque la de desarrollo se recrea. Revisar antes del primer despliegue.
Task 2: minor (deferred): el admin no ordena por jerarquía de grado (usa el orden de choices).
Task 2: Ruling: se acepta que `Profile.jsx` quede sin poder guardar durante el plan 1 — ya no
  tenía el campo de edad y ahora el grado de texto libre devuelve 400 contra la lista cerrada.
  Esa pantalla se rehace en el plan 2 y arreglar la vieja es trabajo que se tira. — Si está
  mal: entre el plan 1 y el plan 2 nadie puede editar su perfil desde la interfaz; se puede
  hacer desde el admin de Django.
Task 2: fix round 2/5 dispatched (resume, 1 Important)
Task 2: fix round 2/5 (1 addressed, 0 open — normalización en save(), cubre API+admin+shell+
  siembra; DNI real nunca se convierte a None; corre en create y en update; commits
  2d429e3..951be16, 19/19 tests). Re-review limpia.
Task 2: minor (deferred): `save(update_fields=[...])` sin 'dni', `QuerySet.update()` y
  `bulk_create` esquivan save() y por ende la normalización. Ningún llamador lo hace hoy, pero
  **los planes 2 y 3 van a hacer operaciones masivas** — tenerlo presente ahí.
Task 2: complete (commits 6c88518..951be16, review clean tras 2 rondas, 3 minors deferidos)
Task 3: dispatched (sonnet, base 951be16) — fechas de habilitación
Task 3: implementer DONE (commit 441db91, 27/27 tests; migraciones api/0006 y users/0004
  nuevas, ninguna reescrita; test de end<start acotado a __all__ para no pasar por otro campo)
Task 3: task review dispatched (sonnet, diff 951be16..441db91)
Task 3: task review -> spec OK, calidad Approved, 0 critical/important, 4 minors + 1 warning
Task 3: warning resuelto por el controlador — `UserProfileSerializer.Meta.fields` es una lista
  explícita (serializers.py:18), no `__all__`, así que `habilitation_window` NO queda expuesto
  ni escribible por la API. Verificado. El plan 2 lo agregará a propósito cuando el buzo se
  inscriba desde su pantalla.
Task 3: Ruling: promuevo dos minors a corrección — CheckConstraint de end_date >= start_date, y
  mensajes de violación en castellano — El reviewer los calificó Minor porque hoy el admin es
  la única puerta de entrada y pasa por full_clean. Eso es cierto ahora y deja de serlo ya: T7
  siembra con objects.create() y el plan 4 construye la pantalla de carga de fechas. Y sobre
  todo, **la tarea 6 construye todo el cálculo de vigencia asumiendo que el rango está bien
  formado** ("vigente todos los días del rango", "ventana del Anexo 27 = end_date - 30"): si
  end_date puede preceder a start_date, esas dos reglas no significan nada. Un invariante del
  que depende el motor lo tiene que garantizar la base, no el acordarse de llamar full_clean.
  — Si está mal: una constraint y un test de más, costo despreciable.
Task 3: minor (deferred): `cycle` acepta cualquier entero positivo (0, 99999) sin relación con
  el año de las fechas.
Task 3: minor (deferred): test_an_incomplete_cycle_is_normal sólo cuenta filas; no fallaría si
  alguien agregara validación de completitud del ciclo.
Task 3: fix round 1/5 dispatched (resume, 2 minors promovidos)
Task 3: fix round 1/5 (3 addressed, 0 open — CheckConstraint con condition= y __gte (acepta
  fecha de un solo día), mensajes en castellano exactos, migración api/0007 nueva con 0006
  intacta; commits 441db91..c30cf10, 29/29 tests). Re-review limpia.
Task 3: minor (deferred): ningún test prueba a nivel de base que una fecha de un solo día se
  acepte — `test_a_single_day_window_is_valid` sólo llama full_clean() sin guardar. El `__gte`
  está verificado por lectura, pero un test lo protegería de una edición futura. Arreglo barato:
  que ese test haga .save() en vez de sólo full_clean().
Task 3: complete (commits 951be16..c30cf10, review clean tras 1 ronda, 3 minors deferidos)
Task 4: dispatched (sonnet, base c30cf10) — estudios atados a su punto de la directiva
Task 4: implementer DONE_WITH_CONCERNS (commit acfd92c, 37/37 tests). Concerns: (1) la
  migración 0008 usa "g" como default de una sola vez para filas existentes; (2) POST
  /api/blocks/ sigue roto por `title` obligatorio — ruptura ya aceptada en el pre-flight.
Task 4: task review dispatched (sonnet, diff c30cf10..acfd92c)
Task 4: task review -> spec OK, calidad "Needs fixes", 2 Important, 2 minors, 1 warning
Task 4: warning resuelto por el controlador — ATOMIC_REQUESTS no está configurado en los
  settings del proyecto (sólo el default False de Django), así que no hay transaccion implicita
  por request: el transaction.atomic() explicito en save() hace falta de verdad.
Task 4: Ruling: promuevo el minor del UniqueConstraint parcial (user, study_code) condicionado
  a is_current=True — Mismo razonamiento que la constraint de fechas en T3: **la tarea 6
  construye el motor de aptitud sobre este invariante.** Va a preguntar "cual es el estudio
  vigente del punto d" y espera exactamente una respuesta; si puede haber dos filas vigentes
  esa pregunta no tiene respuesta definida y el motor queda indefinido. Lo unico que hoy lo
  impide es acordarse de pasar por save(). El reviewer notó que choca con el orden de la
  degradación, pero con el fix de atomicidad aplicado primero (degradar e insertar en una sola
  transacción) nunca hay dos filas vigentes a la vez, así que no chocan.
  — Si está mal: una constraint, una migración y un test de más.
Task 4: minor (deferred): `title` se reescribe en cada save, incluso en ediciones. Inofensivo
  hoy; un study_code desconocido deja title en blanco y full_clean lo atrapa.

=== RIESGOS PRE-DESPLIEGUE (consolidado — revisar antes del primer servidor real) ===
PD-1 (T3): las migraciones de perfil no traen paso de conversión de datos: DNI '' -> NULL, ni
  grados de texto libre -> lista cerrada de 2 caracteres. Sobre una base con datos reales la
  migración falla o trunca.
PD-2 (T4): la migración 0008 pone "g" (odontológico, un punto real de la directiva) como
  default de una sola vez en `study_code`. Sobre una base con estudios ya subidos: (a) cada
  estudio existente queda reetiquetado en silencio como punto g, datos equivocados presentados
  como un estudio real; (b) `is_current` default True deja a cada buzo con varias filas "g
  vigente", rompiendo el invariante, y nada lo repara hasta la próxima subida de ese buzo.
  Un despliegue real necesita migración de datos, o study_code nullable con triage manual.
PD-3 (sesión previa): DEBUG=True hardcodeado y /media/ sin autenticación. Diferido a pedido
  explícito del usuario mientras se prueba el sistema; apagar DEBUG es la parte barata.
=== fin riesgos pre-despliegue ===

Task 4: fix round 1/5 dispatched (resume, 2 Important + 1 minor promovido)
Task 4: fix round 1/5 (3 addressed, 0 open — test reescrito y verificado que discrimina
  (quitar el gate lo hace fallar), transaction.atomic() sobre degradación+insert,
  UniqueConstraint parcial en migración 0009 nueva con 0008 intacta; commits acfd92c..a4123a5,
  38/38 tests). Re-review limpia.
Task 4: el desvío del implementador (update_fields en el test) quedó justificado: la
  degradación corre antes de super().save() y es independiente de qué columnas se escriben,
  así que update_fields no tapa el defecto. Guardar un objeto rancio que todavía cree que está
  vigente ahora falla ruidosamente en vez de crear dos filas vigentes; un objeto recién leído
  de la base trae is_current=False y no lo toca. Ninguna ruta real de request lo alcanza.
*** PD-2 AGRAVADO (T4): la re-revisión encontró que el AddConstraint de la migración 0009 NO
  SÓLO deja datos equivocados: **falla directamente** en cualquier base donde un buzo ya tenga
  dos o más StudyBlock, porque 0008 los dejó todos con study_code="g" e is_current=True. O sea
  que sobre datos reales la migración no se puede aplicar, no es que se aplique mal. Necesita un
  RunPython previo que degrade todas las filas menos la última por buzo. ***
Task 4: complete (commits c30cf10..a4123a5, review clean tras 1 ronda, 1 minor deferido)
Task 5: dispatched (sonnet, base a4123a5) — dictámenes del enfermero y del médico
Task 5: implementer DONE_WITH_CONCERNS (commit 285a3c2, 48/48 tests). Concern: le puso
  default='DOCTOR' a reviewer_role para no romper código existente.
Task 5: Ruling: `reviewer_role` sin default, obligatorio, toda ruta de escritura lo tiene que
  declarar — Ese campo es lo único que distingue una preaprobación del enfermero (que el médico
  todavía tiene que confirmar) de una aprobación del médico (que cierra el asunto). Un default
  significa que cualquier ruta que se olvide de setearlo produce en silencio un dictamen con
  autoridad que nadie otorgó, y el default elegido era justamente el MÁS autoritativo: una
  preaprobación de enfermero sería indistinguible de la firma del médico, y al buzo se le diría
  que está en condiciones de presentarse. Es exactamente la falla que el circuito de dos etapas
  existe para evitar. Mejor que rompa ruidosamente. — Si está mal: POST /api/comments/ deja de
  funcionar hasta el plan 3, misma ruptura aceptada que POST /api/blocks/.
*** CARRY-FORWARD AL PLAN 3 (permisos y vistas): `reviewer_role` NO se puede aceptar como input
  del cliente. Hoy queda expuesto en CommentSerializer para que sea seteable, pero el plan 3
  tiene que DERIVARLO del rol del usuario autenticado en el servidor. Si se confía en el
  cliente, un enfermero puede mandar reviewer_role='DOCTOR' y firmar como el médico — se saltea
  todo el circuito de dos etapas. Esto es una regla de autorización, no una de presentación. ***
Task 5: fix round 1/5 dispatched (resume, 1 concern de correctitud)
Task 5: fix round 1/5 (1 addressed — reviewer_role sin default, migración 0011 nueva con 0010
  intacta, reviewer_role y rejection_reason en CommentSerializer, test con message_dict acotado
  y verificado que falla si se repone el default; commit 7de41b4, 49/49 tests)
Task 5: task review dispatched (sonnet, diff a4123a5..7de41b4, 2 commits)
Task 5: task review -> spec ❌ parcial, calidad "Needs fixes", 3 Important, 3 minors
Task 5: Ruling: la asimetría de autoridad va a la base como CheckConstraint, no como convención
  — El reviewer mostró que status='APPROVED' con reviewer_role='NURSE' pasa full_clean() y
  create(). Verifiqué contra el spec §6, que zanja los tres casos: "lo único que el médico no
  puede delegar es decir que alguien está apto" (APPROVED exige DOCTOR); "El médico puede
  aprobar sin abrir... o abrirlo y decidir él" (el médico aprueba o rechaza, nunca prerevisa, así
  que PRE_APPROVED exige NURSE); "los enfermeros le sacan al médico el trabajo de descartar
  documentos ilegibles o fuera de plazo" (REJECTED vale para ambos roles). La tarea 6 va a
  preguntar "¿está aprobado y por quién?" y hoy la respuesta la sostiene sólo la convención.
  — Si está mal: una constraint de más; el circuito de dos etapas no se puede eludir.
Task 5: Ruling: el detalle del rechazo es obligatorio en TODO rechazo, no sólo en "Otros", y se
  hace cumplir en la base — **Esta regresión la introdujo mi propia corrección** (poner content
  blank=True). Dudé si el spec pedía detalle sólo para "Otros", pero §6 es explícito: "Lista
  cerrada, más un campo de detalle en texto libre QUE SE COMPLETA SIEMPRE", y "El detalle va al
  correo del buzo y se muestra textual en su pantalla, porque es lo que le dice qué tiene que
  hacer para arreglarlo". La regla original era correcta; lo que faltaba era hacerla cumplir
  donde el serializador esquiva clean(). Va a la base porque también cubre create() y escrituras
  masivas, que es por donde entra la tarea 6. — Si está mal: el médico tiene que tipear un
  detalle incluso en un rechazo obvio; el usuario fue explícito en no querer trabajo extra para
  el médico, pero el spec fue explícito en que el detalle se completa siempre.
Task 5: Ruling: `status` sin default, obligatorio — Mismo error que reviewer_role un campo más
  allá: el default era 'APPROVED', el valor más autoritativo. — Si está mal: otra ruta de
  escritura que rompe ruidosamente hasta el plan 3.
Task 5: minor (deferred): clean() hace .strip() en content pero ningún test cubre un detalle de
  sólo espacios; borrar el .strip() no haría fallar nada.
Task 5: minor (deferred): las migraciones 0010 y 0011 podrían haberse unificado (0010 rellena
  DOCTOR y 0011 saca el default). Inofensivo: la base de desarrollo se recrea y la historia no
  está mergeada.
Task 5: fix round 2/5 dispatched (resume, 3 Important)
Task 5: fix round 2/5 (3 addressed, 0 open — constraint de autoridad verificada rama por rama
  (admite exactamente las 4 combinaciones legítimas, rechaza APPROVED+NURSE y PRE_APPROVED+
  DOCTOR), constraint de motivo+detalle en rechazos, status sin default; migraciones 0012 y 0013
  nuevas con 0010/0011 intactas; condition= no check=, mensajes impersonales; commit 45f3ccf,
  59/59 tests). Re-review limpia.
*** CARRY-FORWARD AL PLAN 3 (permisos y vistas): las constraints de base ahora salen por la API
  como IntegrityError / 500, no como 400 con mensaje legible. El plan 3 tiene que hacer que los
  serializadores validen las constraints (validate_constraints o validación explícita) para que
  el médico vea el mensaje en castellano en vez de un error de servidor. ***
Task 5: complete (commits a4123a5..45f3ccf, review clean tras 2 rondas, 2 minors deferidos)
Task 6: dispatched (opus, base 45f3ccf) — motor de aptitud derivada
Task 6: implementer DONE (commit b430a52, 105/105 tests: 59 previos + 46 nuevos, sin migración)
*** DEFECTO DEL PLAN encontrado por el implementador mediante mutation testing (27 mutaciones de
  una regla cada una): `test_only_the_current_block_of_a_slot_is_considered`, **test que escribí
  yo en el plan**, PASABA con el filtro is_current borrado — el bloque de reemplazo tenía el pk
  más alto y ganaba por orden de fila, así que el test no probaba nada sobre is_current. El
  implementador lo dejó textual y agregó test_a_demoted_block_is_ignored_even_if_it_was_saved_
  last, que pone el bloque degradado último en orden de pk y falla sin el filtro. Esta es la
  segunda vez que un test del plan no podía fallar; la primera la encontró el reviewer de T4. ***
Task 6: Ruling: "rechazado Y vencido" reporta EXPIRED (las fechas gobiernan sobre el dictamen) —
  Mantiene una sola regla uniforme, igual que el caso aprobado-y-vencido que el brief ya fija, y
  `last_dictamen` sigue cargando el rechazo, así que la pantalla puede mostrar el motivo al lado
  del estado. Invertirlo después cuesta dos líneas. — Si está mal: el buzo ve "vencido" cuando
  además había un motivo de rechazo; el motivo no se pierde, sólo no es el estado principal.
Task 6: Ruling: `last_doctor_review` abarca los ocho bloques vigentes, no sólo el conjunto
  exigido — La columna del listado es "última vez revisado", o sea cuándo miró el médico a este
  buzo; si revisó un estudio que ese buzo no estaba obligado a presentar, igual lo miró. — Si
  está mal: la fecha refleja una revisión de un estudio no exigido. PIDO TEST que lo fije: una
  decisión deliberada sin test es indistinguible de un accidente seis meses después.
Task 6: Ruling: BEFORE_WINDOW cuenta como INCOMPLETE — Sin eso la escalera cae en APTO para un
  buzo cuya única falta es un Anexo 27 que todavía no puede presentar. El estado por estudio
  sigue siendo BEFORE_WINDOW, así que el buzo ve por qué. — Si está mal: nada; es lo correcto.
*** CARRY-FORWARD AL PLAN 2 (pantalla del buzo): cuando un estudio está rechazado Y vencido el
  estado principal es "vencido", pero el motivo del rechazo sigue en last_dictamen. La pantalla
  tiene que mostrar los dos, porque el motivo es lo que le dice al buzo qué arreglar. ***
Task 6: task review dispatched (opus, diff 45f3ccf..b430a52)
Task 6: task review -> spec ✅, calidad Approved, 0 critical, 1 Important, 4 minors.
  El reviewer verificó las reglas de mayor riesgo POR MUTACIÓN, no por lectura: reemplazó
  _study_state por una variante basada en start_date (6 tests fallan), tomó el año del cycle en
  vez de end_date.year (1 falla), mapeó PRE_APPROVED->APPROVED (3 fallan), y confirmó de forma
  independiente que el test vacuo del plan sigue pasando sin el filtro is_current mientras el
  agregado falla. También verificó assertNumQueries(0) con las dos formas de prefetch.
  Fronteras todas inclusivas y correctas: edad 40, estudio que vence exacto en end_date, Anexo
  27 exacto en end_date-30, ventana de un día, estudio fechado exacto en end_date, y el día en
  que se abre la ventana del Anexo 27 cuenta como abierta.
Task 6: Ruling: promuevo tres minors a corrección — (a) el test de pinning de last_doctor_review
  que yo había exigido falta de verdad (el reviewer lo probó mutando a una variante
  required-only: 45 tests siguen en verde); (b) el ruling de rechazado-y-vencido también está
  sin pinning (mover un corto de REJECTED antes de las compuertas de fecha deja todo verde);
  (c) el test nuevo de is_current discrimina sólo por el orden natural de filas de SQLite, la
  MISMA propiedad incidental que hizo vacuo mi test original, apuntando al otro lado — pedí una
  variante independiente del orden (un punto cuyo único bloque está degradado -> MISSING), que
  sigue siendo válida si alguien le agrega Meta.ordering a StudyBlock. Tercera vez en este plan
  que el orden de filas decide si un test prueba algo. — Si está mal: tres tests y un rename.
Task 6: Ruling: renombrar la función `expires_on` a `validity_ends_on` y dejar el campo
  SlotStatus.expires_on como está — el campo es el que van a leer los serializadores y las
  plantillas de los planes siguientes, y ahí `expires_on` es la palabra correcta; la línea
  `expires_on=... expires_on(...)` se lee como si el campo se llamara a sí mismo.
Task 6: fix round 1/5 dispatched (resume, 1 Important + 3 minors promovidos)
Task 6: fix round 1/5 (4 addressed + corrección de conteo, 0 open — los tres tests nuevos
  juzgados por el re-reviewer como capaces de fallar, razonando la mutación de cada uno en vez
  de aceptar la palabra del implementador; el de is_current ahora tiene un solo bloque en el
  punto, así que no hay orden de filas del cual depender; rename completo sin call sites
  huérfanos y el campo SlotStatus.expires_on intacto; commits b430a52..7430bfa).
Task 6: conteo verificado por el controlador con una corrida propia: 49 tests en
  api.tests.test_fitness, 108 en la suite completa. Queda zanjada la discrepancia 45/46 que
  arrastraban los informes.
Task 6: complete (commits 45f3ccf..7430bfa, review Approved tras 1 ronda, 1 minor deferido:
  el nombre del campo `expires_on` vs la función ya renombrada — resuelto, no queda deferido)
Task 7: dispatched (sonnet, base 7430bfa) — datos de prueba del dominio nuevo
Task 7: implementer DONE (commit c4b0fe5, 108/108 tests; corrió el script dos veces con salida
  idéntica y verificó con fitness.py que cada buzo sembrado da el estado pretendido: APTO,
  APTO con 8 estudios, INCOMPLETE, PROBLEM vencido, PROBLEM con 2 problemas, TO_REVIEW con
  preaprobación de enfermero, INCOMPLETE con 8, NO_WINDOW, UNKNOWN_AGE)
Task 7: Ruling: exijo la corrida desde base vacía (paso 2 del brief que el implementador
  saltó) — **Nada en este plan probó todavía que las migraciones 0001 a 0013 se apliquen limpias
  en secuencia sobre una base vacía.** Cada tarea aplicó una o dos migraciones nuevas sobre una
  base ya migrada. Importa en particular acá porque PD-1 y PD-2 son justamente riesgos de que
  una constraint agregada tarde en la cadena falle contra datos que una migración anterior
  rellenó: una corrida desde cero es la evidencia más barata de que la cadena en sí es sana.
  — Si está mal: un minuto de corrida.
Task 7: Ruling: restaurar el usuario instructor y la siembra de bitácoras de buceo — El
  implementador las borró por estar "fuera del dominio nuevo". El razonamiento se entiende pero
  la decisión no era suya: este plan rehizo el dominio de aptitud médica y nada en él autorizó
  quitar cobertura de siembra que funcionaba para otra funcionalidad existente. DiveActivity y
  DiveLog no los tocó ninguna de las siete tareas y UserProfile.is_instructor sigue existiendo.
  — Si está mal: si algún campo que usaban ya no existe, se deja afuera con el campo nombrado.
Task 7: Ruling: sembrar también un caso DATE_INVALID (estudio fechado después de la ventana) —
  Omisión mía en la lista original. Un plan posterior tiene que renderizar ese estado en la
  pantalla del médico, y un estado que nadie puede ver en la base de desarrollo es un estado
  cuyo renderizado nadie va a revisar.
Task 7: aceptado sin cambios: BEFORE_WINDOW es inalcanzable en este ciclo (hoy 2026-11-03, la
  ventana del Anexo 27 abrió el 2026-10-21), y médico/enfermero/admin sin ventana porque el
  personal no sube sus propios estudios.
Task 7: fix round 1/5 dispatched (resume, 3 items)
Task 7: fix round 1/5 (3 addressed — corrida desde base vacía: migraciones api 0001-0013 y
  users 0001-0004 todas OK, seed dos veces con salida idéntica y sin duplicados (1 ventana, 57
  bloques, 57 dictámenes, 1 actividad, 1 bitácora, 14 usuarios); instructor + DiveActivity +
  DiveLog restaurados sin que ningún campo se rompiera; DATE_INVALID sembrado (buzo
  'fechaerronea', punto f fechado 2027-03-10, el motor reporta DATE_INVALID / PROBLEM);
  commits c4b0fe5..376a631, 108/108 tests)
*** DISTINCIÓN IMPORTANTE que planteó el implementador y que acepto tal cual: la corrida desde
  cero **prueba sólo la cadena de esquema**. En una base vacía no hay filas durante la
  migración, así que el riesgo de que una constraint tardía falle contra datos rellenados por
  una migración anterior (PD-2) SIGUE SIN PROBAR y sigue perteneciendo al primer despliegue
  real. No pedí testearlo: construir una base pre-migración falsa sería adivinar datos que
  todavía no existen. ***
Task 7: fix round 1 addendum: restaurar también el grant de Permission, por el mismo ruling que
  las bitácoras — cobertura de siembra que funcionaba para una funcionalidad que ninguna de las
  siete tareas tocó.
Task 7: addendum aplicado (commit a80060c — grant de Permission restaurado; el grantor pasó de
  buzo1, que ya no existe en la siembra, a 'apto'; ningún campo del modelo faltaba)
Task 7: task review dispatched (sonnet, diff 7430bfa..a80060c, 3 commits)
Task 7: task review -> spec OK, 0 critical, 0 important, 5 minors. El reviewer rederivó a mano
  cada estado sembrado desde las fechas y dictámenes contra fitness.py y catalog.py, y todos
  coinciden con la tabla del informe. Verificó además que todos los grados, motivos y roles
  usados son choices válidos, lo que importa porque create() y update_or_create() no validan
  choices.
Task 7: Ruling: promuevo el minor del borrado destructivo a corrección — El script borra
  cualquier User llamado admin/medico/apto/instructor y TODO lo que cascadea desde ahí. **El
  dueño de la app va a correr este script él mismo, sobre una base que puede ya tener su
  superusuario real y cuentas de buzos reales**, y 'admin' es el nombre más probable para ese
  superusuario. Un aviso en el docstring no es una guarda. Rechacé la sugerencia del reviewer de
  gatear por DEBUG: **DEBUG está hardcodeado en True en este proyecto (ver PD-3), así que el
  chequeo pasaría siempre y daría falsa seguridad.** Pedí opt-in explícito por variable de
  entorno más impresión de los usuarios que existen y van a morir, antes de tocar nada.
  — Si está mal: un paso más para correr el script en desarrollo.
Task 7: Ruling: sembrar IN_REVIEW y una subida reemplazada — El reviewer los marcó como no
  requeridos y no lo eran, pero los necesitan los planes siguientes: IN_REVIEW es uno de los
  tres estados que el usuario nombró textualmente ("Falta subir", "En revisión", "Revisados"),
  y hoy ningún buzo sembrado lo produce; y la subida reemplazada importa porque el spec dice que
  el estudio superado se conserva pero NO se muestra en la vista normal — un plan posterior tiene
  que implementar ese ocultamiento y no se puede verificar contra una base sin filas superadas.
Task 7: minors diferidos: no se siembra un Anexo 27 vencido (la regla ya está cubierta por el
  caso vencido genérico).
Task 7: fix round 2/5 dispatched (resume, 2 promovidos + 2 cosmeticos)
Task 7: fix round 2/5 (4 addressed + on_delete reportado, 0 open — guarda verificada: imprime
  los usuarios que existen y hace SystemExit antes del delete si falta SEED_CONFIRM, sin gate de
  DEBUG, mensajes impersonales, docstring actualizado; 'enrevision' da IN_REVIEW/TO_REVIEW y
  'reemplazo' da APTO con el conjunto completo aprobado y la fila superada en is_current=False
  con su rechazo intacto, sin violar la unique parcial; default_date(code) reemplaza el swap
  oculto; commits a80060c..c7086a5, 108/108 tests). Re-review limpia.
Task 7: minor (deferred): el rechazo de 'reemplazo' usa motivo OUT_OF_TERM pero la fecha
  2026-08-01 está dentro de la vigencia; es narrativa de la siembra, sin efecto en el motor.
Task 7: complete (commits 7430bfa..c7086a5, review Approved tras 2 rondas, 2 minors deferidos)

=== LAS 7 TAREAS DEL PLAN 1 ESTÁN COMPLETAS ===
Rama: 17 commits de código (6c88518..c7086a5) + 2 de documentos (e8d9f26 design, 13b4391 plan).
Suite: 108 tests, verificados por el controlador. Cadena de migraciones probada desde base vacía.
Final whole-branch review dispatched (opus, base 13b4391)
