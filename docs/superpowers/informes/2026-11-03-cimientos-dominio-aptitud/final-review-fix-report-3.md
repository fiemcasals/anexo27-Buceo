# Informe de fixes 3 — re-revisión del cierre y segundo pase del ítem 4

Rango revisado: `96ff78d..ccdbd2f` (diff en `review-96ff78d..ccdbd2f.diff`).
Base del pase: 188 tests, árbol limpio, `makemigrations --check` limpio.
**Cierre del pase: 220 tests, todos pasan; `makemigrations --check` limpio; sin migraciones.**

Este es el informe que el agente anterior no llegó a escribir: se colgó después de correr sus
controles de mutación y antes de registrarlos. Por eso la re-revisión no verificó los controles
del implementador — los hizo propios.

---

## Los cuatro encargos de `REANUDAR.md`

### 1. Auditoría de los tests preexistentes que el ítem 4 obligó a cambiar

**Resultado: ningún debilitamiento.** Tres tests desaparecieron y treinta se agregaron (188 − 161
= 27 neto); los tres son renombres con traducción, ninguno un borrado silencioso. Caso por caso,
en `backend/api/tests/test_study_block_api.py` salvo donde se indique:

| Test viejo | Test nuevo | Veredicto |
|---|---|---|
| `test_a_shared_history_is_filtered_the_same_way` | `test_the_reviewers_wider_view_is_filtered_the_same_way` (`:95`) | Traducción fiel. La propiedad es "el filtro `is_current` del §6 no se escapa por la rama amplia del queryset"; sólo cambió de dónde sale la rama amplia (concesión VIEW/ALL → rol DOCTOR). Las dos aserciones idénticas. |
| `test_another_divers_uploads_are_not_served` | mismo nombre (`:88`) | Traducción fiel. Sólo `User.objects.create` → `_user(..., "USER")`. |
| `test_a_doctor_ruling_on_another_divers_study_still_works` | mismo nombre (`:250`) | Traducción fiel. Se quitó la concesión MODIFY y se mantuvieron las dos aserciones. La condición habilitante pasó de concesión a designación; el éxito que fija es el mismo. |
| `test_a_reviewer_without_a_grant_is_refused_with_403` | `test_someone_who_is_not_a_designated_reviewer_is_refused_with_403` (`:273`) | Traducción fiel. El escenario viejo (médico sin concesión) hoy da 201 **a propósito** — es el cambio que el ítem 4 busca. El nuevo mueve el predicado de "sin concesión" a "sin designación" y agrega `Comment.objects.count() == 0`. |
| `test_a_grant_for_another_study_does_not_cover_this_one` | `test_a_grant_does_not_let_a_plain_diver_rule_on_another_study` (`:281`) | Traducción fiel y **más fuerte**. El viejo medía granularidad de la concesión, que ya no gobierna nada. El nuevo afirma lo más exigente en la semántica nueva: una concesión **MODIFY/ALL** no habilita a dictaminar. La mitad "201" que se perdió acá vive en `:250`. |
| `CommentSelfDictamenApiTests.setUp` + `test_ruling_on_ones_own_study_is_refused_with_400_on_block` (`:239`) | mismo nombre | Traducción fiel. Al médico se le dio rol DOCTOR para que lo detenga el §15.9 y no la falta de designación. DRF corre `validate()` antes de `perform_create`, así que el 400 saldría igual sin designación: el cambio no altera el resultado, pero hace honesta la intención. |

Detalle que conviene no perder: `test_a_grant_of_a_single_study_no_longer_shows_it_either`
(`:148`) guarda el id como **entero** (`shared_items=[self.theirs.pk]`), que era justo la forma
que el viejo `get_queryset` honraba con `str(item).isdigit()`. Prueba que se ignora la forma más
permisiva del mecanismo derogado, no la más fácil.

### 2. Controles de mutación sobre los tests del pase anterior

Ocho mutaciones propias, revertidas una por una. **Ocho de ocho atrapadas; ningún test que no
pudiera fallar.** El defecto recurrente de la rama no se repitió en ese pase.

| # | Mutación | Resultado |
|---|---|---|
| M1 | `SoloQuienDictamino` → `True` | 3 fallas (el enfermero reescribe, el buzo borra 204, el buzo reescribe 400 por el §15.9 como segunda capa) |
| M2 | `CommentViewSet.get_queryset` → `Comment.objects.all()` | 2 fallas; el tercero recibía la fila completa del rechazo con motivo y detalle |
| M3 | `SoloElDuenoDelEstudio` → `True` | 2 fallas (el médico borra 204 y edita 200 el estudio ajeno) |
| M4 | `get_fields`: `if self.instance is not None` → `if False` | 1 falla: el dictamen se movió al bloque del otro buzo |
| M5 | `es_revisor` → `True` | 13 fallas en los dos módulos |
| M5b | `es_revisor` sin la defensa del perfil ausente | 2 errores `RelatedObjectDoesNotExist` → era el encargo 3, verificado |
| M7 | `reviewer_label` fijo en `'Médico'` | 3 fallas, incluida la del caso de dos roles |
| M8 | `VERDICT_PRINT` → el ternario viejo | 1 falla: reproduce el bug exacto del ítem 2 |

**Hueco de cobertura, no test falso:** el §15.9 en PATCH (`serializers.py`) ya no es alcanzable
por la API —`SoloQuienDictamino` exige `doctor == user` y el §15.9 exige `block.user == user`, y
juntos implican una fila que la API no puede crear— pero sí desde el shell o el admin
(`Comment.objects.create` no llama `clean()`), donde devuelve 400. Es defensa en profundidad
viva, no código muerto. Sigue sin test.

### 3. El acceso por rol, y el usuario sin perfil

`es_revisor` concentra la regla del §5 en una función con la defensa del perfil ausente y el
motivo al lado. La mutación M5b confirma que la defensa no es decorativa: sin ella son 500, y dos
tests lo atrapan. **Pero el ítem 4 había convertido dos de los cuatro endpoints que exponen el
legajo** — ver los hallazgos de abajo.

### 4. Dictamen sobre `SoloQuienDictamino` (la pregunta que quedó abierta)

**Era un hallazgo, no estaba correcto. Corregido en este pase.**

El §5 lo resuelve sin inferir nada: abre con "Cuatro roles. **El admin los designa.**" y
condiciona la facultad a la designación en presente ("Designado por el admin"). La tabla tiene
cuatro filas y **no tiene una para "ex-médico"**: a quien le sacan la designación, el §5 lo pone
en la fila "Buzo | Ve y gestiona sus propios estudios. **Nada más.**", la única del cuadro que
cierra con una negación. El §5 agrega que "el rol es único y excluyente", así que no hay una
condición de revisor superpuesta que sobreviva al rol.

El argumento a favor del código viejo —"que pueda corregir lo que firmó"— es legítimo **para la
lectura** y se conserva entero. Para la escritura no, y lo que habilitaba no era corregir una
errata. Verificado:

```
enfermero designado POST {PRE_APPROVED, NURSE}   -> 201
el admin le saca la designación (role = USER)
GET /api/blocks/                                 -> []          (ya no ve nada)
GET /api/comments/                               -> [su dictamen]
PATCH /api/comments/<pk>/ {APPROVED, DOCTOR}     -> 200
fila: status=APPROVED, reviewer_role=DOCTOR, doctor=enfermero
```

Una persona a la que el diseño acaba de reclasificar como buzo acuñaba la palabra final del
médico, y el motor la lee como tal. La asimetría era la pista: no podía **ver** el estudio pero sí
reescribir el dictamen sobre ese estudio.

**Arreglo:** `return es_revisor(request.user) and obj.doctor_id == request.user.pk`. El
`Q(doctor=user)` del `get_queryset` se deja como está y su comentario se ajustó.

---

## Hallazgos de la re-revisión, y qué se hizo con cada uno

### Crítico — el rol era escribible por su propio dueño

`UserProfileSerializer` no tenía `read_only_fields` y `UserProfileViewSet.me` acepta PUT/PATCH.
Verificado:

```
PATCH /api/profiles/me/ {"role": "DOCTOR"}                     -> 200, rol en la base: DOCTOR
GET  /api/blocks/                                              -> [el estudio del otro buzo]
POST /api/comments/ {APPROVED, DOCTOR}                         -> 201
```

Hasta este cierre `UserProfile.role` no se leía en ninguna parte de la API (D-5), así que un campo
escribible era cosmético. **El ítem 4 lo convirtió en la única credencial de autorización del
sistema y dejó su puerta de escritura abierta**: con el registro abierto y sin verificación de
correo, cualquiera se hacía médico, leía el legajo de los 150 buzos y firmaba la palabra final.
Contradice textualmente a D-5 y al §5.

Segunda cara: el queryset incluía los perfiles de quien te concediera `PERSONAL_DATA`/`ALL` y no
había permiso a nivel de objeto, así que un grantee con concesión **VIEW** hacía
`PATCH /api/profiles/<grantor>/ {"role":"DOCTOR","dni":"999"}` → **200** y `DELETE` → **204**.
Mismo agujero que el pase anterior tapó en `StudyBlock`, sin tapar en `UserProfile`.

**Arreglado:** `read_only_fields = ['role', 'is_instructor']`; `SoloElDuenoDelPerfil`; el queryset
sirve sólo el perfil propio.

### Crítico — el dictamen declaraba su propia calidad

`reviewer_role` lo mandaba el cliente y nada lo cotejaba contra el perfil: `perform_create`
comprobaba que el usuario fuera uno de los dos roles revisores y después confiaba en el cuerpo del
pedido. Verificado: un **enfermero designado** posteaba `{status: "APPROVED", reviewer_role:
"DOCTOR"}` → **201**, fila `APPROVED/DOCTOR`. La `CheckConstraint` no lo atrapa porque acopla el
estado con el rol **declarado**. El §5 dice del enfermero "**No puede declarar apto**" y el §6 que
es "lo único que el médico no puede delegar".

D-2 lo asignaba al plan 3 como prolijidad. Por el criterio de D-3 —integridad del circuito, no
perímetro— no se difirió. **Arreglado:** `reviewer_role` de sólo lectura y derivado del perfil en
`perform_create`, más el pareo estado/rol en `validate` para que el desajuste salga 400 y no 500
por la constraint. D-2 quedó anotado.

### Importante — `Anexo27View` quedó afuera del ítem 4

Decidía por `is_staff`. Verificado: el **médico designado** → **403**; un `is_staff` sin
designación → 200. El primero es el defecto: 403 sobre el formulario que el sistema existe para
producir, en el tercer endpoint que sirve el registro médico.

**Arreglado:** el revisor designado lo emite. **Desvío deliberado del informe de revisión:** el
acceso de `is_staff` **se conserva**. El revisor proponía sacarlo citando el §5, pero D-1 deja el
admin de Django como acceso crudo y salida de emergencia hasta que exista su pantalla propia, así
que ya ve los estudios y los dictámenes por ahí; negarle este endpoint mientras el panel sirve los
mismos datos no protegería nada. `is_staff` sólo lo otorga `promote` (`IsAdminUser`) o
`createsuperuser`, así que el registro abierto no lo alcanza. Queda fijado por
`test_the_admin_keeps_their_raw_access` y la mutación M-k.

De paso: `User.objects.get(pk=pk)` propagaba `DoesNotExist` → 500 con traceback. Ahora
`get_object_or_404`.

### Importante — `UserProfileViewSet.get_queryset` corría sobre el mecanismo derogado

Cerrada la mitad que es un agujero (un buzo le entregaba DNI, fecha de nacimiento, grado y destino
a cualquier usuario registrado — la ruta que D-5 condena). **No se ensanchó** para darle al médico
el listado de 150 buzos del §8.1: eso le cambiaría la respuesta a `Dashboard.jsx:56` sin pantalla
que la use. Registrado como carry-forward en D-5, con `SoloElDuenoDelPerfil` ya puesto para cuando
se ensanche.

### Menores

- **`access_level` le quedaba mintiendo al médico.** Clasificado Menor por la re-revisión, que
  juzgaba el diff. Al correr la app se vio la consecuencia entera y **se corrigió** — ver la
  sección de abajo.
- **Re-apuntar el dictamen devuelve 200 en silencio** (DRF ignora los campos de sólo lectura). El
  agujero está cerrado y el cliente ve la realidad en la respuesta; un 400 explícito sería más
  honesto. No se cambió: es una mejora de forma, no un defecto.
- **La etiqueta del revisor queda vacía si `reviewer_role` está en blanco**, alcanzable sólo desde
  el shell (la constraint sólo lo fija para `APPROVED` y `PRE_APPROVED`). No se cambió.
- **La línea inexacta de `final-review-fix-report-2.md`** quedó corregida con la redacción que la
  re-revisión propuso: la comparación de la vista desaparece, la de `get_access_level` deja de
  gobernar el acceso pero sigue alimentando el campo informativo.

---

## Lo que se escribió, y cómo se verificó

Siete arreglos, todos con TDD estricto: test primero, falla observada y leída, código mínimo,
verde. **32 tests nuevos** (188 → 220).

| Archivo | Qué |
|---|---|
| `api/serializers.py` | `role`/`is_instructor` de sólo lectura; `reviewer_role` de sólo lectura; pareo estado/rol en `validate` con `_rol_efectivo` |
| `api/views.py` | `SoloElDuenoDelPerfil`; queryset del perfil; `SoloQuienDictamino` + `es_revisor`; `reviewer_role` derivado en `perform_create`; `Anexo27View` por rol + `get_object_or_404` |
| `api/tests/test_profile_api.py` | nuevo, 13 tests |
| `api/tests/test_anexo27_api.py` | nuevo, 7 tests — el endpoint no tenía **ningún** test de acceso |
| `api/tests/test_comment_api.py` | +8 tests (`ExRevisorTests`, `ElRolDelDictamenEsElRealTests`) |
| `api/tests/test_study_block_api.py` | +4 tests (`AccessLevelSaleDelRolTests`) |
| `api/roles.py` | nuevo: `REVIEWER_ROLES` y `es_revisor`, que ahora consultan las vistas **y** los serializadores (`views` importa `serializers`, así que dejarlo en `views` obligaba a un import local para esquivar el ciclo) |

### Controles de mutación sobre los tests nuevos

**Catorce de catorce atrapadas.** Las tres de sobre-restricción (M-d, M-g, M-k) son las que prueban
que los tests-guarda no son decorativos.

| # | Mutación | Resultado |
|---|---|---|
| M-a | `SoloElDuenoDelPerfil` → `True` | 2 fallas |
| M-b | `read_only_fields` del perfil sin `role` | 3 fallas |
| M-c | `read_only_fields` del perfil sin `is_instructor` | 1 falla |
| M-d | el perfil de sólo lectura de punta a punta (**sobre-restricción**) | 1 falla: el buzo no puede editar lo suyo |
| M-e | el queryset del perfil vuelve a las concesiones | 3 fallas |
| M-f | `SoloQuienDictamino` sin `es_revisor` (el agujero del encargo 4) | 2 fallas |
| M-g | `get_queryset` del dictamen sin `Q(doctor=user)` (**sobre-restricción**) | 3 fallas |
| M-h | `reviewer_role` vuelve a venir del cliente | 2 fallas |
| M-i | sin el pareo estado/rol en `validate` | 2 errores (la constraint sale como 500, que es el punto) |
| M-j | el Anexo 27 vuelve a decidir por `is_staff` | 2 fallas: el médico y el enfermero designados |
| M-k | el Anexo 27 sin el acceso del admin (**sobre-restricción**) | 1 falla |
| M-l | el Anexo 27 sin ninguna comprobación | 2 fallas |
| M-m | sin `get_object_or_404` | 1 error `DoesNotExist` |
| M-n | `get_access_level` sin la rama del rol | 3 fallas |

**Un test propio pasó antes del arreglo y no debía**, y se corrigió en el acto: el `User` que
`force_authenticate` guarda cachea su `profile` en la primera lectura, así que reusar el cliente
después de cambiar el rol medía el caché y no la base. Es el defecto recurrente de la rama
apareciendo en un test nuevo. Los tres tests que cambian un rol a mitad de camino autentican con
un `User` recién leído, con el motivo escrito al lado.

---

## El séptimo arreglo, y la app corriendo

La verificación de los seis arreglos era sólo de backend (220 tests), así que se levantó la app
—Django en `:8000`, Vite en `:5173`, contra la base sembrada— y se la manejó con Playwright. Lo
que apareció no lo habría mostrado ningún test de los que había:

**El médico designado veía "Solo Lectura" en los 71 estudios.** `Dashboard.jsx:477` cuelga el
botón "Revisar Auditoría" de `s.access_level === 'MODIFY'`, y `get_access_level` seguía
resolviendo por `Permission`, así que le informaba `NONE`. El backend le aceptaba el dictamen y
la pantalla no se lo ofrecía: el circuito del médico no funcionaba de punta a punta. Es
backend-fixable sin tocar el frontend, y es el mismo campo de acceso que el ítem 4 debía
convertir, así que se corrigió acá.

De paso obligó a mover `REVIEWER_ROLES`/`es_revisor` a `api/roles.py`: los consultan las vistas y
los serializadores, y `views` importa `serializers`.

### Lo medido contra el servidor real (usuario `medico`, rol DOCTOR, **sin** `is_staff`)

| Comprobación | Antes | Ahora |
|---|---|---|
| estudios servidos | — | 71, de 12 buzos, todos `access_level: MODIFY` |
| `GET /api/anexo27/<buzo>/` | **403** | **200** `application/pdf`, 3370 bytes |
| `GET /api/anexo27/99999/` | **500** + traceback | **404** |
| buzo `PATCH me/ {role: DOCTOR, is_instructor: true}` | rol pasaba a DOCTOR | **rol USER, instructor False** |
| buzo `PATCH me/ {phone}` | guardaba | **guarda** (no se pasó de restrictivo) |
| enfermera `POST {APPROVED, DOCTOR}` | **201** | **400** `"La aprobación corresponde sólo al médico."` |
| `GET /api/profiles/` como médico | propio + grantors | 1 fila (propio) |

### Lo medido en la pantalla

Con Playwright sobre Chrome, sesión del médico: pestaña "Compartidos conmigo (71)", 13 buzos
listados, un buzo expandido → **7 botones "Revisar Auditoría", 0 "Solo Lectura"**, y el modal
abre con "DICTAMEN DEL AUDITOR · Visto Bueno / Rechazado · Guardar Dictamen".
**Cero errores de consola y cero respuestas ≥400** en las sesiones del médico y de un buzo.

Lo que se temía y **no** pasó: `GET /api/profiles/` devolviendo sólo el perfil propio no rompe el
dashboard. `sharedProfiles` sólo pre-inicializa los grupos con nombres más lindos; el segundo
loop de `Dashboard.jsx` reconstruye cualquier grupo faltante desde `study.user_details`, que
`StudyBlockSerializer` ya manda. Degrada sin romperse.

La base quedó como estaba: los dos teléfonos que la prueba escribió se revirtieron, y siguen 72
estudios, 71 dictámenes y los roles intactos.

---

## Lo que sigue abierto

1. ~~**El estudio marcado `"g"`**~~ — **cerrado el 2026-11-04 (D-6).** El usuario decidió no
   recuperar los datos de la instancia de prueba. Queda la advertencia operativa: una base con
   filas anteriores a la `0008` no se migra, se recrea.
2. **Los dos carry-forward nuevos de D-5**: `access_level` para el revisor y el listado del §8.1.
3. **Diferido por decisión del usuario:** `DEBUG = True` y `/media/` sin autenticar.
4. **`PermissionViewSet`** sigue permitiendo crear concesiones sobre estudios que ya nadie
   consulta; para los perfiles tampoco rigen más. La pantalla sale en el plan 2 (D-5).
