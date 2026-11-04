# Decisiones posteriores al diseño aprobado

Registro de decisiones que el diseño
(`2026-11-03-control-aptitud-medica-design.md`) dejó explícitamente abiertas en su §16, o que
surgieron al construir. Cada una dice quién la tomó y cuándo.

---

## D-1. El panel del admin se construye como pantalla propia, no sobre el admin de Django

**Pregunta abierta del §16:** "Si el panel del admin se construye como pantalla propia o sobre
el admin de Django. Hay que tener en cuenta que el admin tiene que poder cotejar una lista de
150 personas cómodamente."

**Decisión (usuario, 2026-11-03):** pantalla propia. El admin ingresa por el login normal de la
aplicación, igual que cualquier usuario, y la aplicación lo lleva a su propio tablero según su
rol. Las funciones son las que ya fija el §8.5.

**Alcance:** plan 4.

**Consecuencias registradas:**

- **El admin de Django se conserva como acceso crudo.** No se desactiva. Es la única interfaz
  disponible hasta que el plan 4 esté construido, y después queda como salida de emergencia para
  lo que la pantalla propia no cubra. Por eso se le pusieron los nombres en castellano
  (commit 69a4488).
- **El mecanismo de login ya existe y no hay que inventarlo.** `UserProfile.role` ya tiene el
  valor `ADMIN`, y el ruteo por rol es el mismo que necesitan las pantallas del médico y de los
  enfermeros. El admin no necesita `is_staff` para su pantalla propia; lo necesita sólo para
  entrar al admin de Django.
- **Eliminar un usuario arrastra su historia clínica.** `StudyBlock.user` y `Comment.doctor` son
  CASCADE, así que borrar un usuario borra sus estudios subidos y los dictámenes. Es un registro
  médico militar. La pantalla tiene que mostrar qué se va a destruir **antes** de hacerlo, con
  los números concretos. Misma lección que la guarda del script de siembra.
- **Borrar una fecha de habilitación con buzos inscriptos falla a propósito.**
  `UserProfile.habilitation_window` es `PROTECT` desde la corrección 12 de la revisión final. La
  pantalla tiene que mostrar ese `ProtectedError` de forma legible ("hay N buzos inscriptos en
  esta fecha"), no una pantalla de error del servidor. Esto se suma al punto ya registrado de
  que las violaciones de constraint hoy salen por la API como 500 y el plan 3 tiene que
  convertirlas en 400 con mensaje.
- **La lista de 150 personas tiene que ser cómoda de leer en orden y de exportar o copiar**
  (§8.5). El motor de aptitud ya está construido para alimentar un listado de 150 filas sin
  N+1; el mismo prefetch sirve acá.

---

## D-2. El orden de los planes se mantiene: 2, 3, 4

**Decisión (usuario, 2026-11-03):** se ofreció adelantar el panel del admin (plan 4) por delante
del circuito del médico (plan 3), dado que reordenar no tiraba trabajo hecho. El usuario eligió
mantener el orden original.

**Orden en firme:**

1. **Plan 1 — Cimientos del dominio de aptitud.** Completo (commits `6c88518..6cc290b`, 154
   tests).
2. **Plan 2 — Pantalla del buzo y subida de estudios.** Incluye la compresión de imágenes y el
   soporte HEIC del §11, y rehace `Profile.jsx`, que el plan 1 dejó sin poder guardar.
3. **Plan 3 — Circuito del médico y los enfermeros auxiliares.** Incluye convertir las
   violaciones de constraint en 400 con mensaje legible.

   > **Adelantado al cierre del plan 1 (2026-11-04):** derivar `reviewer_role` del usuario
   > autenticado ya está hecho. Esta línea lo enunciaba como prolijidad, y la re-revisión midió lo
   > que en realidad habilitaba: `reviewer_role` lo mandaba el cliente y nada lo cotejaba contra el
   > perfil, así que un **enfermero designado** posteaba
   > `{status: "APPROVED", reviewer_role: "DOCTOR"}` y recibía 201 — la fila quedaba indistinguible
   > de la palabra final del médico, que el §6 declara "lo único que el médico no puede delegar", y
   > `fitness.py` la lee como tal contando `reviewer_role == DOCTOR`. La `CheckConstraint` no lo
   > atrapaba porque acopla el estado con el rol **declarado**, no con el real. Por D-3 eso es
   > integridad del circuito, no perímetro, así que no se difirió. De paso quedó el pareo
   > estado/rol en `CommentSerializer.validate` para que el desajuste salga 400 y no 500, que es
   > un primer caso de lo que esta línea sí sigue debiendo.
4. **Plan 4 — Panel del admin (D-1), los tres correos del §9 y los procesos programados.**

---

## D-3. Riesgo abierto: el dictamen no tiene control de permisos al editar ni al borrar

**Hallazgo (implementador del cierre, 2026-11-03), fuera del alcance del plan 1:**
`CommentViewSet` controla quién puede *crear* un dictamen, pero no controla nada en `update` ni
en `destroy`. Cualquier usuario autenticado puede editar o borrar cualquier dictamen, incluido
el rechazo que el médico escribió sobre sus propios estudios.

**Decisión (controlador):** no se corrige en el plan 1. Es trabajo de vistas y permisos, que es
lo que el plan 3 tiene a cargo, y el plan 1 es la capa de dominio. **Queda registrado como
riesgo abierto, no como punto cerrado.**

**Por qué igual importa, y no es lo mismo que el diferimiento de seguridad ya acordado:** el
usuario difirió el endurecimiento del perímetro (`DEBUG = True`, `/media/` sin autenticar)
porque el sistema está en prueba. Esto es distinto: es la integridad del circuito mismo. Un buzo
podría borrar el rechazo de su propio estudio y quedar apto. **El plan 3 no puede cerrarse sin
esto.**

**Lo que el plan 3 tiene que cubrir:** `update` y `destroy` de `Comment` restringidos a quien
dictaminó, o a nadie si el dictamen es definitivo. El §15.9 ya está cubierto en la creación.

> **Cerrado en el cierre del plan 1, no diferido al plan 3 (2026-11-04).** `SoloQuienDictamino`
> restringe `update` y `destroy` a quien emitió el dictamen, y el §15.9 también se aplica sobre el
> bloque destino. La re-revisión ajustó después el borde que faltaba: hace falta **seguir**
> designado, no haberlo estado. Sin eso, el enfermero al que el admin le sacaba la designación
> convertía su pre-aprobación en la aprobación del médico (`PATCH {status: "APPROVED"}` → 200,
> verificado), que es el mismo riesgo de falsificación con un paso previo; y la asimetría lo
> delataba — ya no podía **ver** el estudio pero sí reescribir el dictamen sobre ese estudio. El
> §5 condiciona la facultad a la designación en presente y su tabla no tiene una fila para
> "ex-médico". La **lectura** de lo que uno firmó se conserva (`Q(doctor=user)` en el
> `get_queryset`): es parte del registro y ocultárselo no protege a nadie.
>
> El criterio de este D-3 —integridad del circuito, no perímetro— es el que se aplicó a todo lo
> demás que la re-revisión encontró. Ver D-2 y D-5.

---

## D-4. El circuito de revisión nunca funcionó: la consulta de permisos fallaba en SQLite

**Hallazgo (implementador del cierre, 2026-11-03):** `CommentViewSet.perform_create` resolvía el
permiso con `shared_items__contains` sobre un `JSONField`. **SQLite no soporta ese lookup, así
que todo dictamen de un no-propietario devolvía 500.** En la práctica el único camino que
funcionaba era el del propietario sobre sus propios estudios — es decir, justamente el que el
§15.9 prohíbe.

Eso explica por qué el defecto del §15.9 pasó inadvertido tanto tiempo: el camino legítimo
estaba roto y el ilegítimo era el único que respondía. Nadie lo notó porque esta rama es la
primera que prueba el circuito.

**Corrección:** la comparación se movió a Python, reutilizando la de `get_access_level`, de modo
que una concesión para ALL o para ese estudio pasa. Quién está autorizado no cambia.

**Lección registrada:** un lookup de `JSONField` que el motor no soporta no falla al escribir el
código ni al migrar — falla en tiempo de ejecución, con 500, sólo en el camino que nadie probó
todavía. Los planes 2 a 4 agregan más consultas sobre `profile_data` y `shared_items`, que son
los dos `JSONField` del proyecto. **Cada una necesita un test que la ejercite de verdad contra
SQLite, no sólo que el código exista.**

---

## D-5. El acceso a los estudios viene del rol, no de concesiones entre usuarios

**Regla (usuario, 2026-11-03), textual:**

> "es que los unicos que deberian tener acceso de revisar los estudios medicos son los medico
> y/o enfermeros que yo designe como admin. nadie mas deberia poder verlos"

Coincide con el §5 del diseno, que ya lo decia: el buzo "ve y gestiona sus propios estudios.
**Nada mas.**", el enfermero "ve los estudios de **todos** los buzos", el medico "ve los
estudios de todos".

**El codigo no implementaba nada de eso.** Verificado el 2026-11-03: `grep "DOCTOR\|NURSE"`
sobre `api/views.py` y `api/serializers.py` daba **cero apariciones**. `UserProfile.role` no se
leia en ninguna parte de la API. Todo el acceso salia del modelo `Permission`: un buzo le
concedia acceso a otro usuario sobre sus propios estudios.

Consecuencias que eso tenia, las dos al reves de lo pedido:

1. **El medico designado no veia nada.** No es dueno de estudios y no tiene concesiones, asi que
   su queryset era vacio. La pantalla del medico del plan 3 habria mostrado un listado en blanco.
2. **Un buzo podia compartir su legajo medico con cualquier usuario registrado**, por una ruta
   que ya existe (`frontend/src/App.jsx:43`), con el registro abierto y sin verificacion de
   correo.

Es herencia de cuando la aplicacion era una bitacora de buceo, donde compartir inmersiones con
un companero tenia sentido. Para un legajo medico no.

**Implementado en el cierre del plan 1:** el acceso a `StudyBlock` y la facultad de dictaminar
vienen del rol. Buzo ve solo lo suyo; `DOCTOR` y `NURSE` ven los estudios de todos; nadie mas ve
nada. El §15.9 sigue aplicando encima. Un usuario sin perfil cargado no es revisor.

**El modelo `Permission` queda en pie** (el §5 dice dejarlo) pero deja de gobernar el acceso a
los estudios.

**Carry-forward para el plan 2:** la pantalla `frontend/src/components/Permissions.jsx` y su ruta
en `App.jsx:43` quedan concediendo algo que ya nadie consulta. El plan 2, que rehace las
pantallas del buzo, tiene que sacarla. No se toco ahora porque el frontend es de planes
posteriores.

**`access_level` le quedaba mintiendo al medico. Corregido en el mismo cierre.**
`StudyBlockSerializer.get_access_level` seguia resolviendo por `Permission`, asi que al revisor
designado le informaba `"NONE"` sobre los estudios que la misma respuesta le estaba sirviendo.
`frontend/src/components/Dashboard.jsx:477` abre el cuadro de dictamen con
`s.access_level === 'MODIFY'`, de modo que **el unico camino de interfaz existente para escribir
un dictamen quedaba oculto justo para el medico designado**: el backend le aceptaba el dictamen y
la pantalla no se lo ofrecia. Verificado en la app corriendo — el medico veia "Solo Lectura" en
los 71 estudios.

Ahora el revisor designado recibe `MODIFY`, que es lo que en el vocabulario de este codigo
significa "puede dictaminar" (`Permissions.jsx:262` lo rotula "Medico"), no "puede editar el
estudio": eso lo sigue impidiendo `SoloElDuenoDelEstudio`. Sale antes de consultar `Permission`,
asi que de paso le ahorra al revisor una consulta por fila — eran N+1 y el listado del medico
paso de 0 a ~1.200 filas, que es lo que el §13 marca como la cosa a vigilar.

**Carry-forward para el plan 3:** cuando construya la pantalla del medico conviene reemplazar
este campo por uno honesto —`MODIFY` dice "modificar" y lo que habilita es dictaminar—, y el §13
ya preve reemplazar ese listado por un endpoint contado.

**Completado despues, en el mismo cierre (segundo pase del item 4):** la re-revision encontro que
el item 4 habia convertido dos de los cuatro endpoints que exponen el legajo. Se cerraron los
otros dos:

- **`UserProfileViewSet`**. El rol era **escribible por su propio dueno**: un
  `PATCH /api/profiles/me/ {"role": "DOCTOR"}` devolvia 200, y con el registro abierto y sin
  verificacion de correo cualquiera se hacia medico, leia el legajo de los 150 buzos y firmaba la
  palabra final. El item 4 habia convertido `role` en la **unica credencial de autorizacion del
  sistema** sin cerrar su puerta de escritura — hasta entonces el campo no se leia en ninguna
  parte (es lo que dice el parrafo de arriba), asi que escribirlo era cosmetico. Ahora `role` y
  `is_instructor` son de solo lectura en el serializador y los designa el admin. Ademas el
  queryset servia los perfiles de quien te concediera `PERSONAL_DATA`/`ALL` y no habia control a
  nivel de objeto, asi que un grantee de **solo lectura** reescribia y borraba el perfil del
  grantor: mismo agujero que el cierre tapo en `StudyBlock`. Hoy sirve solo el perfil propio, con
  `SoloElDuenoDelPerfil` encima.
- **`Anexo27View`**. Decidia por `is_staff`, que es la llave del admin de Django y no tiene nada
  que ver con el §5: **el medico designado recibia 403** sobre el formulario que el sistema existe
  para producir. Ahora el revisor designado lo emite. El acceso del admin se conserva a proposito
  (ver D-1: el admin de Django queda como acceso crudo, asi que ya ve los estudios y los
  dictamenes; negarle este endpoint mientras el panel sirve los mismos datos no protegeria nada).

**Carry-forward para el plan 3 — el listado de 150 buzos del §8.1 no tiene via de datos.**
`UserProfileViewSet` sirve solo el perfil propio, asi que el medico no tiene de donde sacar el
listado con grado, nombre y unidad que el §8.1 le pide. Es el mismo sintoma que este D-5 describe
para los estudios, ahora para los perfiles. No se ensancho el queryset en el cierre porque le
cambiaria la respuesta a `Dashboard.jsx:56` sin pantalla que la use: lo construye, con el rol como
base, el plan que haga la pantalla del medico. Cuando lo haga, `SoloElDuenoDelPerfil` ya esta
puesto para que ver 150 perfiles no se vuelva poder reescribirlos.

**Lo que esto explica:** el 500 del circuito de revision (D-4) no era el unico problema. Incluso
sin ese error, el medico no tenia acceso a ningun estudio. El mecanismo de concesiones nunca iba
a hacer funcionar su pantalla.
