# Al reanudar — estado al 2026-11-04

## Donde estamos

Rama `nicolas/primer-cambio`. **La re-revisión del cierre del plan 1 está hecha y sus hallazgos
están corregidos.** Los cuatro encargos que este archivo dejaba pendientes están cumplidos y
registrados en `final-review-fix-report-3.md`.

- **220 tests pasan** (188 + 32 nuevos), `makemigrations --check` limpio, sin migraciones nuevas.
- **Commiteado en seis commits temáticos**, `ccdbd2f..7d426fe`. Árbol limpio.
- La base `backend/db.sqlite3` está sembrada. No correr `migrate` ni `create_test_data.py` sobre
  ella sin motivo.
- El worktree de revisión se borró; `git worktree list` tiene sólo el checkout principal.

## Lo primero, antes de cualquier cosa nueva

**Decidir la integración de la rama.** Está 44 commits por delante de `main` y **sin pushear** (no
tiene upstream), así que nada es compartido todavía.

Antes de mergear conviene:

```bash
git tag antes-del-plan-1 main
cp backend/db.sqlite3 backend/db.sqlite3.antes-del-plan-1
git checkout main && git merge --no-ff nicolas/primer-cambio
```

El `--no-ff` agrupa los 44 commits bajo uno, así `git revert -m 1 <sha>` deshace todo de una. Sin
pushear alcanza con `git reset --hard antes-del-plan-1`.

**La copia de la base no es opcional.** `db.sqlite3` está en `.gitignore`, así que git nunca la
toca: la rama trae 16 migraciones y dos de ellas mueven datos con `RunPython.noop` como reversa
(`0014_demote_duplicate_current_studies`, `0015_backfill_rejection_reason_and_detail`). Django las
desaplica sin protestar y sin restaurar nada. El pase de hoy agregó cero migraciones.

Los seis commits:

```
1a002ea refactor(api): es_revisor pasa a su propio modulo
1a0a883 fix(api): el rol lo designa el admin, no su propio dueno
b54742e fix(api): el dictamen se firma con el rol real, no con el declarado
3ddc4b2 fix(api): dictaminar exige seguir designado, no haberlo estado
d09042a fix(api): el Anexo 27 y access_level salen del rol
7d426fe docs: registrar el segundo pase del item 4
```

Cada uno se verificó con la suite completa antes de commitearse (188, 201, 206, 209, 220, 220).

## Qué se corrigió en este pase

Detalle completo, con los controles de mutación, en `final-review-fix-report-3.md`.

- **Crítico — el rol era escribible por su dueño.** `PATCH /api/profiles/me/ {"role":"DOCTOR"}`
  daba 200 y con eso cualquiera se hacía médico, leía el legajo de los 150 buzos y firmaba la
  palabra final. El ítem 4 había convertido `role` en la única credencial de autorización del
  sistema sin cerrar su puerta de escritura. Ahora `role` e `is_instructor` son de sólo lectura.
- **Crítico — el perfil ajeno se reescribía y se borraba.** Un grantee con concesión **VIEW**
  hacía `PATCH`/`DELETE` sobre el perfil del grantor. Ahora `SoloElDuenoDelPerfil` y el queryset
  sirve sólo el perfil propio (cierra además la ruta por la que un buzo entregaba su DNI a
  cualquier usuario registrado).
- **Crítico — el dictamen declaraba su propia calidad.** `reviewer_role` lo mandaba el cliente: un
  enfermero designado posteaba `{APPROVED, DOCTOR}` y recibía 201. Ahora se deriva del perfil y el
  pareo estado/rol sale 400, no 500. Estaba asignado al plan 3 por D-2; se adelantó por el
  criterio de D-3 y D-2 quedó anotado.
- **Importante — el ex-revisor podía reescribir su dictamen** (la pregunta abierta del encargo 4,
  adjudicada con el §5: la facultad es de quien está designado, no de quien lo estuvo). La lectura
  de lo que uno firmó se conserva.
- **Importante — `Anexo27View` decidía por `is_staff`**, así que el médico designado recibía 403
  sobre el formulario que el sistema existe para producir. Ahora lo emite el revisor designado. El
  acceso del admin se conserva a propósito (D-1); es un desvío deliberado del informe de revisión,
  fundamentado en el informe 3.
- **Menor** — `get_object_or_404` en el Anexo 27 (un id inexistente daba 500 con traceback).
- **Encontrado corriendo la app, no por los tests** — `access_level` le informaba `NONE` al
  médico designado y `Dashboard.jsx:477` cuelga de ese valor el botón "Revisar Auditoría": el
  médico veía **"Solo Lectura" en los 71 estudios** y el circuito no funcionaba de punta a punta,
  aunque el backend aceptara el dictamen. Ahora el revisor designado recibe `MODIFY`. Obligó a
  mover `REVIEWER_ROLES`/`es_revisor` a `api/roles.py`, porque ahora los consultan las vistas y
  los serializadores.

## Verificado con la app corriendo

Django `:8000` + Vite `:5173` contra la base sembrada, manejado con Playwright. Sesión del
médico: 13 buzos en "Compartidos conmigo (71)", **7 botones "Revisar Auditoría" y 0 "Solo
Lectura"**, el modal de dictamen abre. **Cero errores de consola y cero respuestas ≥400** en las
sesiones del médico y de un buzo. El Anexo 27 por el médico designado devuelve 200
`application/pdf`; un id inexistente, 404. La base quedó como estaba (se revirtieron los dos
teléfonos que la prueba escribió).

Lo que se temía y no pasó: `profiles/` devolviendo sólo el perfil propio **no** rompe el
dashboard — el segundo loop reconstruye los grupos desde `study.user_details`.

## Después del cierre

`superpowers:finishing-a-development-branch`, y borrar el workspace de este plan.

## Lo que necesitaba al usuario: resuelto

**El estudio marcado `"g"` — cerrado el 2026-11-04, ver D-6.** El usuario decidió no recuperar
los datos de la instancia de prueba, así que no se escribe ninguna migración que clasifique por
título. Antes de decidirlo se verificó que la base nunca estuvo versionada, que en la máquina hay
una sola (la sembrada, con los 9 `g` siendo fichas odontológicas de verdad) y que `media/` está
vacío.

**La advertencia que queda, y es lo útil:** si la instancia de prueba todavía existe, **su base no
se migra hacia adelante, se recrea.** Medido sobre una base armada en el estado anterior a la
`0008`: el `migrate` no falla, pero deja al buzo con un solo estudio vigente —una ficha
odontológica— y los demás escondidos como historial. El título original sobrevive la migración y
**un solo `save()` lo destruye**, porque `StudyBlock.save()` reescribe `title` desde el catálogo.

## Lo diferido por decisión del usuario

`DEBUG = True` y `/media/` sin autenticar. Textual: "por ahora dejalo asi porque estamos probando
como funciona un sistema asi. en caso de que resulte vamos a mejorar la seguridad del sistema".
**No** cubre el §15.9 ni el acceso por rol — eso es integridad del circuito, no perímetro (es el
criterio de D-3, y es el que se aplicó a todos los hallazgos de la re-revisión).

## Carry-forward registrado en D-5, para los planes siguientes

1. **`access_level` dice `MODIFY` donde quiere decir "puede dictaminar".** Quedó correcto pero
   mal nombrado: `MODIFY` es el vocabulario de `Permission`, y lo que habilita es el dictamen, no
   editar el estudio (eso lo impide `SoloElDuenoDelEstudio`). El plan 3 conviene que lo reemplace
   por un campo honesto cuando construya la pantalla del médico.
2. **El listado de 150 buzos del §8.1 no tiene vía de datos.** `UserProfileViewSet` sirve sólo el
   perfil propio. No se ensanchó ahora porque le cambiaría la respuesta a `Dashboard.jsx:56` sin
   pantalla que la use. `SoloElDuenoDelPerfil` ya está puesto para cuando se ensanche.
3. **`Permissions.jsx` y su ruta en `App.jsx:43`** siguen concediendo algo que ya nadie consulta.
   Sale en el plan 2.
4. **El §15.9 en PATCH no tiene test.** Es inalcanzable por la API y sí alcanzable desde el shell
   o el admin, donde devuelve 400: defensa en profundidad viva, no código muerto.
