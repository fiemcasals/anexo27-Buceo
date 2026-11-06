# Circuito del médico y los enfermeros auxiliares — diseño

**5 de noviembre de 2026.** Es el plan 3 del mapa que abre
`docs/superpowers/plans/2026-11-03-cimientos-dominio-aptitud.md`. Argumenta
desde `2026-11-03-control-aptitud-medica-design.md`, al que este documento
llama "el spec" y cuyas secciones cita por número. **Donde los dos se
contradigan, manda éste**, y cada contradicción está marcada abajo con por qué.

---

## Qué es y por qué ahora

El buzo ya puede presentar sus estudios: eso lo dejó andando el plan 2. Lo que
falta es el otro lado del mostrador — que alguien los mire y diga sí o no.

Hoy esa pantalla existe pero es la vieja, anterior a todo este trabajo, y tiene
dos problemas que no son de estética.

**Se baja todo.** `frontend/src/components/Dashboard.jsx:56-58` pide `blocks/`
—todos los estudios del sistema, sin paginar— y después filtra en JavaScript.
Con 150 buzos son más de 1.200 estudios con sus dictámenes en cada carga.

DRF no tiene `DEFAULT_PAGINATION_CLASS` configurado, así que **la paginación
nunca estuvo prendida**: el endpoint nuevo tiene que traer la suya. (El
`pagination_class = None` de `views.py:422` es de `FechasView`, que sirve las
fechas de habilitación, y no tiene que ver con esto.) La llamada a `profiles/`
ya no baja el plantel: `UserProfileViewSet.get_queryset` filtra por el usuario
autenticado desde la decisión D-5.

**No distingue al médico del enfermero.** El backend sí: `api/models.py:141-143`
y `api/serializers.py:162-165` hacen cumplir que el enfermero pre-aprueba y no
aprueba. La pantalla no menciona los roles en ningún lado, así que la diferencia
sólo aparece como un rechazo del servidor cuando alguien intenta algo que no
puede.

El §13 del spec lo dice sin vueltas: **esto es un cambio de arquitectura, no una
optimización.** No se puede hacer una versión liviana que filtre en el navegador
y agregarle filtros después, porque filtrar en el navegador es justamente lo que
se rompe.

---

## Objetivos

1. El médico entra y ve, sin abrir a nadie, quién tiene algo esperando dictamen.
2. Puede buscar, filtrar —incluido **por turno**— y ordenar sobre el plantel
   entero sin que el navegador se baje el plantel entero.
3. Desde la ficha de un buzo aprueba o rechaza cada punto de la directiva, y al
   rechazar el buzo se entera por correo.
4. El enfermero auxiliar usa las mismas dos pantallas, con la misma información,
   y su aprobación deja el estudio pre-revisado esperando la firma del médico.

## No objetivos

- El recordatorio de los 30 días y el correo de "queda completo" (§9). Quedan
  para el plan 4. **Sale únicamente el correo de rechazo** — decisión tomada en
  la conversación del 5/11.
- Los procesos programados y la limpieza por retención (§12).
- El resto del panel del admin (§8.5). Lo ya hecho —designar revisores y cargar
  fechas— se queda como está.
- Rehacer la pantalla del buzo (§8.3), que anda.

## Anti-objetivos

Cosas que harían fracasar esto aunque funcione:

- **Que el listado y la ficha muestren números distintos para el mismo buzo.**
  Es la falla más probable de este plan y tiene sección propia más abajo.
- **Que los contadores se calculen buzo por buzo.** Una consulta por fila es la
  forma más fácil de arruinar el §13; el remedio tiene que ser visible en el
  código, no una intención.
- **Que el enfermero pueda aprobar de verdad.** La separación de firmas es la
  razón de ser del circuito en dos etapas.
- **Que un fallo del correo impida registrar un dictamen.**

---

## Lo que ya existe y hay que reusar

Esto no se vuelve a escribir. El plan 1 lo construyó para este plan.

**`api/fitness.py`** — el motor de estados, con tests. `diver_summary(profile,
today) -> DiverSummary` devuelve, para un buzo, exactamente los números que el
listado pide: `presented`, `approved`, `pending_review`, `pre_reviewed`,
`problems`, `expired`, `rejected`, `last_doctor_review`, más `required_codes` y
los `slots` con el estado de cada punto. Los comentarios del propio archivo
citan el §8.1 y el §13.

**El estado de la columna "Estado" tampoco se inventa.** `fitness.DiverState`
es el estado global de un buzo frente a su turno: los seis del §7 más
`UNKNOWN_AGE` para el caso de la fecha de nacimiento sin cargar. Su docstring
dice textualmente que *"el listado del médico muestra esta fila tal cual, sin
volver a derivarla de los estados de cada punto"*. Lo calcula `_diver_state`,
que ya resuelve la precedencia que anota el boceto: **Vencido y Rechazado le
ganan a los demás**, porque son los dos que necesitan que alguien haga algo ya.

**`api/estado.py`** — `armar_estado(profile, today, request)` arma los ocho
puntos con texto, estado, vigencia, motivo de rechazo y archivo. Es casi
exactamente lo que la ficha del §8.2 necesita mostrar; hoy lo consume la
pantalla del buzo.

**`api/roles.py`** — `REVIEWER_ROLES = ('DOCTOR', 'NURSE')` y `es_revisor()`.

**`Comment`** (`api/models.py:59`) — `STATUS_CHOICES` con `PRE_APPROVED`,
`APPROVED`, `REJECTED`; `REJECTION_REASONS` con los cuatro motivos del diálogo
ya escritos: *fuera del plazo de la directiva*, *valores no aptos*, *documento
ilegible*, *otros*; y `reviewer_role`. Las reglas de quién puede qué están en
`models.py:141-143` y `serializers.py:162-165`.

**`UserProfile.habilitation_window`** (`backend/users/models.py:71`) — clave
foránea al turno al que se inscribió el buzo. **El filtro por turno no necesita
tocar la base.**

**Los bocetos aprobados**, en `docs/superpowers/specs/2026-11-03-bocetos/`:
`1-listado-medico.html` y `2-ficha-buzo.html`. Son la referencia visual. Dos
salvedades que el propio spec anota: ninguno muestra la fecha de habilitación,
porque se definió después de aprobarlos, y **los textos de `2-ficha-buzo.html`
llevan el tono personal viejo y hay que pasarlos a impersonal (§10)**.

---

## El cambio de arquitectura

Hace falta un endpoint que devuelva **una fila por buzo, ya contada, de a
páginas**. El navegador pide sólo lo que muestra.

Cada fila lleva: grado, apellido y nombre, unidad, DNI, edad, el turno al que se
inscribió con su fecha, presentados sobre exigidos según la edad, pendientes de
revisar, pre-revisados, vencidos, rechazados, la fecha del último dictamen **del
médico**, y el estado derivado.

El buscador —nombre, apellido, DNI y grado en un solo campo—, los cuatro
filtros, el filtro por turno, el orden y los contadores del encabezado se
resuelven todos en el servidor.

### Los conteos NO se reimplementan en SQL

Esto es lo más importante del documento y es fácil equivocarse al revés.

**`diver_summary` es la única implementación de la regla.** El listado la llama
una vez por buzo, igual que la ficha.

Parece un N+1 y no lo es. `api/fitness.py:24` dice que las funciones **no
consultan la base**, y el propio archivo trae escrito el `select_related` /
`prefetch_related` con el que el llamador baja *"el plantel entero (unos 150
buzos) de una sola vez"*; el motor filtra `is_current` y ordena los dictámenes
**en memoria** para aprovechar ese cache. Con ese prefetch, evaluar los 150
buzos son **unas tres consultas en total**, no 150. El plan 1 lo construyó así a
propósito, y tanto su plan como `2026-11-03-decisiones-posteriores.md` lo dejan
dicho: *"el mismo prefetch sirve acá"*.

La alternativa —anotar los conteos en el ORM— obligaría a reescribir en SQL,
sobre SQLite, la vigencia contra `end_date` con días distintos por punto (365,
y 30 para el Anexo 27), el último dictamen por bloque, el conjunto exigido según
la edad, y la precedencia de `DiverState`. Eso es **exactamente la "segunda
definición de la misma regla" que este documento declara su anti-objetivo**. No
se hace.

**El estado derivado tampoco se precalcula ni se guarda.** Depende de la fecha
de hoy: un estudio aprobado se vuelve vencido sin que nadie toque nada. Sale de
`DiverState` en cada pedido.

**Lo que esto cuesta, y hay que aceptarlo:** el buscador, los filtros, el orden,
los contadores y la paginación se resuelven **en el servidor pero en Python**,
sobre los 150 perfiles ya traídos. La paginación de DRF y el `order_by` del ORM
no sirven tal cual. Es deliberado: es el precio de tener una sola definición de
la regla, y con 150 filas se paga sin que se note.

Además, los tres contadores del encabezado y los conteos de los cuatro filtros
son sobre el plantel, así que hay que evaluar a todos igual, pagine o no pagine
la tabla.

### El riesgo que queda

Alguien va a mirar esto más adelante, va a ver un bucle sobre 150 perfiles, va a
pensar "esto se arregla con un `annotate`", y va a crear la segunda definición
sin darse cuenta. A partir de ahí el listado va a decir 6/7 y la ficha 5/7: sin
error, sin excepción, sin nada en los registros.

Dos cosas lo sostienen:

1. Una prueba de consultas: evaluar el plantel entero tiene que costar un número
   fijo y chico de consultas, **y el test falla si ese número crece**. Es lo que
   impide que una optimización ingenua pase inadvertida, y también lo que
   detecta que alguien rompió el prefetch.
2. **Un test que compare, sobre los mismos datos, lo que devuelve el endpoint
   del listado contra `diver_summary` para cada uno de esos buzos**, y falle
   ante cualquier diferencia. Tiene que cubrir los casos donde más fácil se
   separan: el buzo de 40 años justos, el que no se inscribió a ningún turno, el
   que no tiene fecha de nacimiento, el que tiene un vencido y un rechazado a la
   vez, y el que no subió nada.

---

## El listado (§8.1)

Se ve **todo el personal** por defecto — o sea los perfiles con rol `USER`: el
§5 dice que el médico, los enfermeros y el admin no aparecen en "Personal a
controlar".

### Qué cuentan los contadores

Arriba van tres: aptos, a revisar, vencidos. El boceto aprobado se contradice
acá —dice "Aptos 2" contando buzos y "A revisar 6" sumando estudios— así que
queda decidido en este documento:

**Cuentan buzos, no estudios.** "A revisar 3" quiere decir que hay tres
personas con algo esperando, no seis estudios en la pila. Es gente, que es lo
que el médico va a ir a buscar, y hace juego con "Aptos", que ya contaba buzos.

**"A revisar" incluye lo pre-revisado.** Todo lo que no tiene la firma final del
médico cuenta como pendiente: el apto sale sólo de sus aprobaciones, así que
mientras no firme el trabajo no está terminado. El enfermero ve el mismo
número, que por lo tanto incluye trabajo que él ya hizo; la columna "A revisar"
de cada fila igual muestra las dos pilas separadas.

**Un buzo cae en un solo contador**, el que manda `DiverState` con su
precedencia: vencido y rechazado le ganan a los demás. Por eso un buzo con un
vencido *y* un rechazado sale como rechazado y no aparece en "Vencidos".

**Los tres se recalculan con el buscador y el filtro de turno.** Si la tabla
muestra cuatro buzos y arriba dice seis, se lee como un error aunque no lo sea.
Los números describen siempre lo que se está mirando. Lo mismo vale para el
conteo que lleva cada uno de los cuatro filtros.

Esto no contradice haber descartado la opción del turno como selector: aquella
hacía que hubiera que elegir un turno para ver algo, y escondía a los que no se
anotaron. Acá se sigue entrando al plantel completo.

El turno es **una columna** —con el lugar en el ciclo y la fecha, por ejemplo
"1ra · 15/03/2027"— y **un filtro** al lado de los cuatro que ya había. Quien no
se inscribió a ningún turno aparece igual, marcado "Sin turno". *Esta fue la
opción B de dos que se compararon; la descartada hacía del turno un selector que
acotaba toda la pantalla y sus contadores.*

### El buzo sin turno, y el que no tiene fecha de nacimiento

Sin turno no hay contra qué medir la vigencia, así que `required_codes` devuelve
vacío y `DiverSummary` sale con todo en cero. **Un buzo que subió los ocho
estudios mostraría "0/0" y guiones en todo**: el test de consistencia pasaría,
porque es lo que devuelve la autoridad, y la pantalla estaría mintiendo.

La fila no dice "0/0". Dice **cuántos estudios tiene subidos y que el exigido no
se puede determinar** — "8 subidos · sin turno" —, y el estado es el que ya
existe para eso, `DiverState.NO_WINDOW`. Lo mismo con la fecha de nacimiento sin
cargar (`UNKNOWN_AGE`): se muestra lo que hay y se dice qué falta para poder
calcular, en lugar de un cero que se lee como "no presentó nada".

En la columna de edad va **la edad de la regla** —año del turno menos año de
nacimiento, que es la que decide si corresponden siete estudios u ocho, y puede
ser un año más que la real— y un guion cuando no hay turno contra el cual
calcularla. *Decisión mía: lo que importa en esta pantalla es por qué el
denominador es 7 u 8, no cuántos años cumplió la persona.*

Los cuatro filtros existentes, con su conteo cada uno: Todos · Documentación
completa · Documentación incompleta · Pendientes de revisar. **"Documentación
completa" significa que están subidos todos los estudios exigidos, con
independencia del dictamen**: un buzo con un estudio rechazado cuenta como
completo, porque el papel está presentado.

Orden por apellido, por última vez revisado, o por cantidad de pendientes.

**La columna "A revisar" distingue lo que nadie tocó de lo que viene
pre-revisado** esperando la firma del médico (§8.1). Esa segunda pila es la que
el médico puede despachar rápido, y por eso es el orden con el que entra. Los
dos números ya vienen separados en `DiverSummary`: `pending_review` y
`pre_reviewed`.

**A estas dos pantallas entran sólo el médico y los enfermeros**, o sea los
roles de `roles.REVIEWER_ROLES`, comprobado con `es_revisor()`. Un buzo que
llegue a la dirección por su cuenta no tiene que ver el plantel. Esto es
control de acceso por rol, que es lo único de seguridad que este plan **no**
puede diferir.

Dos detalles que el spec marca como no cosméticos:

- **El denominador cambia con la edad** (7 u 8). Es la señal más visible de que
  la regla de los 40 está funcionando.
- La columna de fecha es **"Última vez revisado", no "último estudio subido"**,
  y **cuenta sólo los dictámenes del médico**. Si las pre-aprobaciones del
  enfermero sellaran esa columna, un enfermero despachando la cola un día
  ocupado le arruinaría el orden al médico y le taparía la señal que fue a
  buscar. Un buzo sin ningún dictamen del médico muestra "Sin revisar".

**Los filtros viven en la dirección de la página**, no en estado de React: así
anda el botón de atrás, se puede recargar sin perder nada, y el médico puede
mandarle un enlace a alguien.

## La ficha (§8.2)

Encabezado con grado, apellido, nombre, DNI, edad, unidad, cuántos estudios le
corresponden y **el turno al que se inscribió**.

Cuatro contadores: Presentados, **Aprobados**, A revisar, Con problema.
*Aprobados es el número que importa*, porque el apto sale de ahí.

**Los ocho puntos de la directiva, siempre los ocho, en orden a–h**, cada uno
con su estado del §7. El médico controla contra la lista, así que la ve en el
orden de la directiva.

**Sólo lo que espera dictamen tiene botones de dictamen**: Ver, Aprobar,
Rechazar. Cada dictamen dice quién y cuándo en la propia fila, sin abrir nada, y
el motivo del rechazo se muestra textual.

**Lo aprobado por el médico lleva además un botón para revertir**, y esto
corrige un agujero del spec. Hoy una aprobación equivocada no tiene salida: el
buzo no puede reemplazar lo que el médico aprobó (`fitness.puede_reemplazarse`)
y la ficha no le ofrece acciones a lo resuelto, así que **un error de un clic
deja a alguien apto hasta que el estudio venza**. El rechazo sí tiene salida —el
buzo vuelve a subir— y el pre-revisado también.

Revertir devuelve el punto a "En revisión" y queda asentado quién revirtió y
cuándo, como cualquier otro dictamen: el §6 pide que el historial diga quién,
con qué rol, cuándo y qué decidió. El backend ya lo permite —`SoloQuienDictamino`
deja que el autor edite su dictamen— así que lo que falta es la regla explícita
y el botón. Sólo el médico revierte lo que él aprobó.

Volver al listado conserva los filtros.

**Rechazar abre un diálogo** con los cuatro motivos, el campo de detalle, y el
aviso de que al confirmar se le manda un correo al buzo, con la dirección a la
vista.

## El enfermero auxiliar (§8.4)

**Son las mismas dos pantallas. No se construye una interfaz aparte.**

> **Cambio respecto del spec.** El §8.4 punto 1 decía que el enfermero no veía
> nada de la aptitud —ni el contador de Aptos, ni el estado Apto, ni "Aprobados
> 2/7"— con este argumento: *"no es su decisión, y mostrárselo invita a que
> alguien la tome"*. **Queda sin efecto.** El enfermero ve la misma información
> que el médico, incluido quién ya está apto. La intención, en palabras del
> responsable del producto el 5/11: *que vean la misma información, pero que el
> médico sea el que finalmente da el apto completo.* La separación está en la
> firma, no en lo que se muestra.

Quedan en pie las otras dos diferencias:

- **Entra ordenado al revés que el médico**: primero lo que nadie tocó, lo más
  viejo arriba — la pila cruda. El médico entra viendo la pila rápida, lo
  pre-revisado esperando su firma.

  "Lo más viejo" no existe como campo. **Es la fecha de subida (`created_at`)
  del estudio sin dictamen más antiguo que tenga ese buzo**; un buzo sin nada
  esperando va al fondo. No sirve "Última vez revisado", que cuenta sólo
  dictámenes del médico y por eso está vacía justo en la pila cruda.

  **Los dos órdenes son opciones del desplegable, no sólo valores iniciales.**
  Si fueran sólo el arranque, el médico que ordena por apellido pierde para
  siempre la pila rápida, que es la razón por la que entra así.
- **Sus botones son Aprobar y Rechazar**, iguales a los del médico, pero su
  aprobación deja el estudio en **Pre-revisado**. El apto sale únicamente de las
  aprobaciones del médico. Esto el backend ya lo hace cumplir; la pantalla tiene
  que decirlo, no descubrirlo con un error.

---

## El correo de rechazo

Sale **un solo correo** en todo este plan: cuando se rechaza un estudio, lo
rechace el enfermero o el médico (§9). Dice qué estudio fue, el motivo y el
detalle escrito por quien lo rechazó. Va a la dirección con la que el buzo creó
su usuario.

**Si el correo falla, el rechazo se guarda igual.** El dictamen es lo
importante; que el servidor de correo esté caído no puede impedir que el médico
trabaje. Que el correo no salió tiene que quedar registrado en algún lado que
alguien pueda mirar después.

### Un 500 en el camino del diálogo

`Comment` tiene una `CheckConstraint` llamada `rejection_has_reason_and_detail`
que exige que todo rechazo lleve motivo y detalle. **`CommentSerializer.validate`
no la cubre**: valida el §15.9 y el pareo rol/estado, pero `rejection_reason` y
`content` son `blank=True` y nadie los exige. Un `POST comments/` con
`status: "REJECTED"` y motivo vacío pasa el serializador y revienta en la base
como `IntegrityError` — **500 con traceback, porque `DEBUG = True`**.

Ese es exactamente el POST que manda el diálogo de rechazo que este plan
construye. Se arregla acá, con su test: el serializador exige motivo y detalle
en un rechazo y devuelve 400 con el mensaje. El mismo archivo ya trata así el
pareo rol/estado, y su comentario explica por qué: *"la CheckConstraint lo
atrapa igual, pero sale como IntegrityError —500— y no como un 400 con el
motivo"*. Es la deuda que `2026-11-03-decisiones-posteriores.md` (D-2) ya le
había asignado a este plan.

---

## El cableado del correo

El cableado ya está hecho y commiteado (`8494c47`): las credenciales salen de
`backend/.env`, que no va a git, y `backend/.env.example` está versionado con
los nombres. **Mientras `EMAIL_HOST_PASSWORD` esté vacío el sistema usa el
backend de consola**, que imprime el correo en la terminal en lugar de mandarlo
— así se construye y se prueba el circuito sin credenciales y sin que nadie
reciba un correo de prueba por accidente. La casilla de la división ya está
configurada y la autenticación contra Gmail fue verificada.

---

## Lo que se borra

El generador de Anexo 27 en PDF. **El Anexo 27 es un documento más de los que se
piden** —el punto h de la directiva— y el buzo lo sube ya hecho y firmado; el
sistema no lo emite. Hoy el generador existe pero ningún botón lo llama:
`handleGenerateAnexo` está definido en `Dashboard.jsx:107` y nunca se usa.

Se va todo junto: `backend/api/report_pdf.py`, sus tests
(`api/tests/test_report_pdf.py`), `Anexo27View` (`views.py:167`), su registro en
`urls.py:17`, el import de `views.py:27`, y la función muerta del frontend.

### La red de seguridad del ruteo

`frontend/src/App.jsx` usa hoy `Dashboard` como **fallback cuando falla la
consulta del perfil**, con un comentario que dice que una falla de red no tiene
que mostrarle a nadie la pantalla del rol equivocado. Si `/dashboard` pasa a ser
el listado del revisor y sigue siendo el fallback, **un buzo cuya consulta de
perfil falló aterriza en una pantalla que le va a dar 403**.

El fallback deja de ser una pantalla y pasa a ser **un cartel que dice que no se
pudo determinar el rol, con un botón para reintentar**. Sin rol confirmado no se
muestra ninguna de las tres pantallas.

Al borrar `Dashboard.jsx` se pierde además su pestaña "Mis estudios", con carga
y borrado. Es a propósito: según el §5, el médico, los enfermeros y el admin no
presentan estudios.

---

## Decisiones que tomé yo

Van marcadas porque nadie las pidió: son mías y se pueden revertir sin discutir
con nadie.

- **El listado pagina de a 50 filas.** Con 150 buzos son tres páginas; menos
  obliga a paginar de más en una pantalla pensada para barrer.
- **El orden por defecto** sale del §8.4 punto 2, que sigue vigente: el médico
  entra viendo primero lo pre-revisado esperando su firma; el enfermero, primero
  lo que nadie tocó, lo más viejo arriba.
- **Un rol desconocido** en la barra lateral cae en el rótulo neutro en lugar de
  dejar el enlace sin nombre.

## Lo que queda al constructor

- El nombre y la forma exacta del endpoint, y si es uno o dos.
- Cómo se anotan los conteos en la consulta —la técnica, no el resultado— y si
  algún campo conviene que salga de una subconsulta.
- La disposición fina de las dos pantallas, dentro de lo que fijan los bocetos.
- Dónde y cómo se registra que un correo no pudo salir.
- Si la ficha reusa `armar_estado` tal cual o necesita una variante para el
  revisor.

## Restricciones

- Sin dependencias nuevas sin justificarlo: el backend es Django 6.0.3 con DRF
  3.16.1 sobre SQLite; el frontend, React 19 con Vite 7 y Bootstrap 5.
- Todo lo que se escriba va con tests, y los tests tienen que poder fallar.
- Los textos de la interfaz van **en impersonal** (§10).
- Las fechas que la persona escribe o lee van en **dd/mm/aaaa**; hay un
  componente `CampoFecha` y una biblioteca `fecha-dd-mm-yyyy` para eso.
- `backend/db.sqlite3` está sembrada y en uso: no se corre `migrate` ni
  `create_test_data.py` contra ella, y no se tocan los usuarios sembrados.
- `DEBUG = True` y `/media/` sin autenticar están diferidos por decisión
  explícita mientras se prueba el sistema. **El diferimiento no alcanza al
  control de acceso por rol**, que es integridad del circuito y es justamente lo
  que este plan construye.
