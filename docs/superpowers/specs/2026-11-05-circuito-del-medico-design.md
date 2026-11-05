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

**Se baja todo.** `frontend/src/components/Dashboard.jsx:56-58` hace tres
llamadas: `profiles/me/`, `blocks/` —todos los estudios del sistema— y
`profiles/` —todos los perfiles—, y después filtra en JavaScript. La paginación
está apagada a mano en `backend/api/views.py:422`. Con 150 buzos son más de
1.200 estudios con sus dictámenes en cada carga.

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

**Los conteos van anotados en la consulta.** Calcularlos llamando a
`diver_summary` una vez por fila es el N+1 que el §13 nombra; con 150 buzos son
150 consultas por pantalla.

**El estado derivado no se precalcula ni se guarda.** Depende de la fecha de
hoy: un estudio aprobado se vuelve vencido sin que nadie toque nada. Se calcula
en la consulta.

### El riesgo central: dos caminos para el mismo número

El listado saca los contadores de una consulta anotada. La ficha los saca de
`diver_summary`. **Son dos implementaciones de la misma regla**, y cuando se
separen nadie se va a dar cuenta: el listado va a decir 6/7 y la ficha 5/7, sin
error, sin excepción, sin nada en los registros.

Dos cosas lo sostienen, y las dos son obligatorias:

1. `diver_summary` sigue siendo la autoridad para un buzo. La consulta anotada
   es una optimización de lectura, nunca una segunda definición.
2. **Un test que, sobre el mismo conjunto de datos, compare fila por fila lo que
   devuelve el endpoint del listado contra lo que devuelve `diver_summary` para
   cada uno de esos buzos, y falle ante cualquier diferencia.** Tiene que cubrir
   los casos donde las dos reglas más fácilmente se separan: el buzo de 40 años
   justos, el que no se inscribió a ningún turno, el que tiene un estudio
   vencido y otro rechazado a la vez, y el que no subió nada.

---

## El listado (§8.1)

Se ve **todo el personal** por defecto. Arriba, tres contadores sobre el total:
aptos, a revisar, vencidos.

El turno es **una columna** —con el lugar en el ciclo y la fecha, por ejemplo
"1ra · 15/03/2027"— y **un filtro** al lado de los cuatro que ya había. Quien no
se inscribió a ningún turno aparece igual, marcado "Sin turno". *Esta fue la
opción B de dos que se compararon; la descartada hacía del turno un selector que
acotaba toda la pantalla y sus contadores.*

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

**Sólo lo que espera dictamen tiene botones**: Ver, Aprobar, Rechazar. Lo
resuelto tiene Ver y nada más. Cada dictamen dice quién y cuándo en la propia
fila, sin abrir nada, y el motivo del rechazo se muestra textual.

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
