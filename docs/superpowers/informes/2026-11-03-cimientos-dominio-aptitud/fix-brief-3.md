# Fix brief 3 — cierre de la rama

Tres items. El primero es una falla de seguridad verificada; los otros dos son chicos.

---

## La regla que fija el dueño del producto

El dueño del producto acaba de enunciar la invariante del sistema, textual:

> "cada usuario puede borrar sus estudios si quiere, si despues vuelve a subir otro de todas
> maneras tiene que aprobarlo el medico para quedar apto. no hay forma de que queda apto si el
> medico no da la palabra final"

Eso es la regla. Tiene dos mitades y las dos son vinculantes:

1. **Un buzo puede borrar sus propios estudios cuando quiera.** Es diseño, no un agujero. Si
   borra uno, el punto queda faltante y el buzo queda incompleto; si sube otro, arranca sin
   dictamen y vuelve a revisión. **No restrinjas esto.**
2. **Nadie queda apto sin la palabra final del médico.** Esta es la que hay que proteger, y es
   la que el item 1 rompe.

---

## Item 1 (CRITICO) — Se puede fabricar la aprobación del médico por PATCH

El pase anterior cerró el §15.9 ("nadie dictamina sobre sus propios estudios") en la
**creación** de un dictamen. `CommentViewSet` no tiene **ningún** control de permisos en
`update` ni en `destroy`, así que la regla se elude por otra puerta.

Un revisor lo verificó contra una base desechable. Los tres agujeros, textual:

> - un tercero `PATCH /api/comments/<pk>/ {status: "APPROVED", reviewer_role: "DOCTOR",
>   rejection_reason: ""}` sobre el comentario de un buzo -> **200**, y la fila pasa de
>   `REJECTED` a `APPROVED` con `doctor` todavía apuntando al médico real -- que `fitness`
>   después lee como aprobación del médico.
> - el buzo puede `DELETE` un rechazo sobre su propio estudio (**204**).
> - el buzo puede `PATCH` el comentario de su propio estudio hacia el bloque de **otro** buzo
>   (**200**; la validación del serializador no se dispara porque el bloque destino no es suyo).

Y "cualquier usuario autenticado" no es un conjunto cerrado:

> `backend/core/urls.py:26` expone `dj_rest_auth.registration`,
> `backend/core/settings.py:191` pone `ACCOUNT_EMAIL_VERIFICATION = 'none'`, y
> `backend/users/adapters.py` no sobrescribe `is_open_for_signup`.

**Por qué el primero y el tercero rompen la regla del dueño del producto, y el segundo no:**

- El **primero** escribe una fila que dice `status=APPROVED`, `reviewer_role=DOCTOR` y `doctor`
  = el médico real. El motor de aptitud la lee como la palabra final del médico. **Queda apto
  sin que el médico haya dicho nada.** Es exactamente lo que la regla prohíbe.
- El **tercero** mueve una aprobación que el médico sí firmó al estudio de otro buzo. Ese otro
  buzo recibe una palabra final que nadie le dio. Misma violación, otra puerta.
- El **segundo** no produce aptitud: borrar el rechazo deja el estudio sin dictamen, o sea "a
  revisar", no apto. Pero destruye lo que el médico escribió —el motivo y el detalle, que el §9
  manda por correo y que el plan 2 tiene que mostrar— y le permite a un buzo ocultar que fue
  rechazado. Se cierra igual, por una razón distinta: es manipulación del registro, no fraude de
  aptitud.

**La regla a implementar, derivada de lo que dijo el dueño del producto:**

- **`Comment`: sólo quien dictaminó puede editar o borrar su propio dictamen. Nadie más, nunca.**
- **`block` queda de sólo lectura después de la creación.** Un dictamen pertenece al estudio
  sobre el que se emitió. Esto cierra el agujero 3 de raíz en vez de validarlo.
- **`StudyBlock`: el dueño sigue pudiendo borrar sus propios estudios, sin restricción.** Al
  borrarse el estudio, sus dictámenes se van en cascada (`Comment.block` es `CASCADE`) — y eso
  es correcto y es el diseño: el punto queda faltante y, si sube otro, vuelve a revisión. **Un
  buzo no puede alcanzar el dictamen por separado para borrarlo dejando el estudio en pie.**

Leé el spec (`docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md`, §6 y §15)
antes de escribir. Si algo del spec contradice esta regla, **detenete y reportá NEEDS_CONTEXT**
en vez de elegir por tu cuenta — la regla viene del dueño del producto y el spec es la autoridad
escrita; si chocan, lo resuelvo yo.

**Verificá además algo que nadie miró todavía:** que `StudyBlockViewSet` efectivamente permita
al dueño borrar su propio estudio y **no** permita borrar el de otro. El dueño del producto
acaba de afirmar la primera mitad como un hecho del sistema; confirmá que es verdad y que la
segunda mitad está cerrada. Si encontrás que un buzo puede borrar el estudio de otro, eso es un
hallazgo nuevo y crítico: reportalo y cerralo.

**Tests requeridos, cada uno afirmando el código de estado Y que la fila no cambió en la base:**
- un tercero intentando PATCH sobre el dictamen de otro -> 403 (o 404 si elegís esconderlo), y
  `status` sigue siendo `REJECTED` en la base
- el buzo intentando DELETE el rechazo de su propio estudio -> 403, y el dictamen sigue existiendo
- el intento de re-apuntar un dictamen a otro bloque -> rechazado, y `block_id` no cambió
- quien dictaminó sí puede corregir su propio dictamen -> 200
- **el buzo sí puede borrar su propio estudio -> 204, y su dictamen se fue en cascada**
- un buzo no puede borrar el estudio de otro

Afirmá **siempre el estado en la base después**, no sólo el código HTTP. Un 403 con la fila ya
modificada sería un test que pasa por la razón equivocada.

---

## Item 2 (IMPORTANTE) — El Anexo 27 imprime la pre-aprobación del enfermero como "RECHAZADO"

`backend/api/report_pdf.py:50-52`:

> `status_text = "APROBADO" if comment.status == "APPROVED" else "RECHAZADO"` no tiene rama para
> `PRE_APPROVED`, y la línea 52 escribe `Médico (...)` sin mirar `reviewer_role`.

`PRE_APPROVED` y el rol `NURSE` los **introdujo esta rama**. O sea: la rama creó un dictamen que
su propio formulario oficial imprime como su opuesto, en rojo, en el documento que firma un
oficial. Y atribuye al médico lo que dictaminó un enfermero.

**Arreglalo:** una rama para `PRE_APPROVED` con su texto y su color propios, y la etiqueta de
quien dictaminó derivada de `reviewer_role` en vez de fija. El texto visible va en **registro
formal e impersonal** — este proyecto lo exige en todo texto que ve una persona. Las etiquetas
de los roles ya están en castellano en `UserProfile.ROLE_CHOICES` y en `Comment.REVIEWER_ROLES`;
usá esas, no inventes términos nuevos.

**Test:** extendé `backend/api/tests/test_report_pdf.py`. Afirmá las dos direcciones: que el
texto de la pre-aprobación aparece y que "RECHAZADO" **no** aparece para ese caso. El test que
ya existe ahí usa `patch` sobre `report_pdf.canvas.Canvas` y lee `c.args[2]` de los
`drawString`; seguí ese patrón.

---

## Item 3 (MENOR) — Dos comparaciones del mismo permiso no coinciden

> `get_access_level` (`backend/api/serializers.py:79`): `if "ALL" in p.shared_items or
> str(obj.id) in p.shared_items:`
> el chequeo nuevo (`backend/api/views.py:146`): `"ALL" in g.shared_items or str(block.id) in
> map(str, g.shared_items)`
>
> No son la misma comparación. `map(str, ...)` convierte los items guardados, así que la vista
> honra una concesión que lista el id como **entero** JSON; `get_access_level` no.
> Efecto neto: para una concesión guardada como entero, `GET /api/blocks/` devuelve el bloque
> pero informa `access_level: "NONE"`, mientras `POST /api/comments/` acepta el dictamen.

El revisor juzga que el lado correcto es el de la vista, porque `StudyBlockViewSet.get_queryset`
(`views.py:85-90`) ya acepta las dos formas con `str(item).isdigit()`. **Reconciliá hacia esa
semántica** y dejá un comentario de una línea diciendo por qué se aceptan las dos formas. No es
un ensanchamiento de privilegio: el filtro `access_level='MODIFY'` sigue intacto.

También corregí una línea inexacta del informe anterior:
`.superpowers/sdd/2026-11-03-cimientos-dominio-aptitud/final-review-fix-report-2.md` afirma que
el chequeo nuevo usa "la misma comparación que `get_access_level`". Es falso, y el revisor lo
probó. Corregila.

---

## Entorno

- Trabajá desde `C:\Users\nicol\Documents\Proyectos\anexo27-Buceo`
- Python es el venv del proyecto: `./venv/Scripts/python.exe`, desde `backend/`. No hay pytest.
- Suite completa: `cd backend && ./venv/Scripts/python.exe manage.py test`
- **Hoy pasan 161 tests y tienen que seguir pasando**, más los que agregues.
- Tres advertencias de deprecación de `allauth` aparecen siempre y no son hallazgos. **Ninguna
  otra advertencia es aceptable** — la salida de los tests de este proyecto está limpia y se
  mantiene así.
- `makemigrations --check --dry-run` tiene que decir "No changes detected" al terminar. **Nada de
  esto debería necesitar una migración.** Si creés que sí, detenete y reportá NEEDS_CONTEXT.

## Reglas que no podés violar

1. **NO corras `backend/create_test_data.py`.** Borra filas; está detrás de `SEED_CONFIRM=1`. No
   pongas esa variable.
2. **NO corras `migrate` contra `backend/db.sqlite3`.** Está recién construida y correcta. El
   corredor de tests arma su propia base.
3. **NO toques el frontend.** Las pantallas son de planes posteriores.
4. **Nunca reescribas una migración existente.**
5. **No cambies la configuración de registro de usuarios** (`ACCOUNT_EMAIL_VERIFICATION`,
   `is_open_for_signup`). El dueño del producto difirió el endurecimiento del perímetro a
   propósito. El registro abierto es el contexto que hace crítico al item 1, no algo que
   arregles acá.
6. **No restrinjas la capacidad de un buzo de borrar sus propios estudios.** Es diseño expreso.

## Antes de empezar

Si algo no está claro, pregunta antes de escribir código.

## Dos controles que este proyecto exige

Cada uno ya atrapó un defecto real en esta rama:

- **Ningún test puede pasar por la razón equivocada.** Afirmá el campo y el código específicos, y
  en el item 1 afirmá también el estado de la fila después.
- **Todo test tiene que poder fallar.** Por cada test que agregues, quitá la regla que cubre y
  confirmá que falla. Esta rama produjo tres tests que no podían fallar. **Reportá el resultado
  de cada control.**

## No dispachés subagentes

Hacé todo vos. Nunca dispachés un subagente, y menos un revisor. La revisión la dispacho yo
después de tu informe.

## Si te excede

Está bien detenerse y decirlo. Reportá BLOCKED o NEEDS_CONTEXT con lo que intentaste y lo que
necesitás. Trabajo parcial honesto es mejor que una suposición.

## Formato del informe

Escribí el informe en
`.superpowers/sdd/2026-11-03-cimientos-dominio-aptitud/final-review-fix-report-3.md`:
- Item 1: la regla que implementaste, los tres agujeros con su código de estado y el estado de
  la fila después, y **qué encontraste al verificar el borrado de estudios propios y ajenos**
- Item 2: el texto y la etiqueta que elegiste y de dónde salen
- Item 3: hacia qué semántica reconciliaste y por qué
- Por cada test agregado: la mutación que corriste y el resultado
- El conteo final de tests, la salida de `makemigrations --check`, y la confirmación de que las
  únicas advertencias son las tres de allauth
- Lo que no hiciste, y por qué

Después respondé SÓLO con (menos de 15 líneas):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits (SHA corto + asunto, uno por línea)
- Una línea con el resumen de tests y el conteo final
- Una línea confirmando que los tres agujeros del item 1 están cerrados, con sus códigos
- Una línea confirmando que el buzo sigue pudiendo borrar sus propios estudios
- Dudas, si hay
- La ruta del informe
