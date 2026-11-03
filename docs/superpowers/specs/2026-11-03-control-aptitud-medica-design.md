# Control de aptitud médica para buceo — rediseño del circuito de estudios

**Fecha:** 2026-11-03
**Proyecto:** anexo27-Buceo
**Estado:** diseño aprobado, pendiente de plan de implementación

---

## 1. Intención y por qué

La unidad exige a cada buzo presentar un conjunto de estudios médicos para
habilitarse a bucear. Hoy ese control se hace fuera del sistema: el buzo junta
papeles, los lleva en un sobre, y el médico de la unidad los mira una vez y no
tiene registro de qué presentó quién ni de qué sigue vigente.

Esta aplicación pasa ese circuito a una herramienta. Cada buzo se registra, carga
sus datos de identificación y sube sus estudios con anticipación, desde el
celular. El médico de la unidad entra, ve de un vistazo cómo viene cada uno,
revisa los documentos y dictamina. La aplicación calcula sola quién está apto y
quién no, y le avisa al buzo cuando algo le falta o cuando ya está en condiciones
de presentarse.

El valor está en dos cosas que hoy no existen: **el médico deja de abrir buzo por
buzo para saber qué le falta a quién**, y **el buzo deja de depender de que
alguien se acuerde de avisarle** que tiene un estudio vencido o rechazado.

La aplicación ya existe y tiene parte de esto construido de forma incompleta.
Este documento describe el circuito completo tal como debe quedar, no un delta
sobre lo que hay.

### Contexto operativo que condiciona todo

- **Son aproximadamente 150 buzos.** No es una demo. Las decisiones de carga y
  paginación tienen que aguantar eso.
- **Hay un solo médico**, y mira a los 150.
- **Hay enfermeros auxiliares** que lo ayudan a revisar, pero no pueden declarar
  apto a nadie.
- **Muchos buzos manejan lo mínimo de computación.** No es un detalle de
  cortesía: es la restricción de diseño más fuerte del proyecto. Si la carga de un
  estudio tiene un paso ambiguo, se va a cargar mal.
- **Lo van a usar del celular**, con datos móviles, muchas veces desde la base.

---

## 2. Objetivos, no objetivos, anti-objetivos

### Objetivos

1. El médico ve en una pantalla, sin abrir a nadie, cómo viene cada buzo: cuántos
   estudios presentó de los que le corresponden, cuántos le quedan por revisar, y
   si hay algo vencido o rechazado.
2. El médico puede buscar, filtrar y ordenar esos 150 registros, y al volver del
   detalle encuentra la lista como la dejó.
3. Al entrar a un buzo, el médico ve **los ocho estudios de la directiva**, no solo
   los subidos, y distingue a simple vista lo que falta de lo que no corresponde.
4. Cada dictamen queda registrado con quién lo hizo y cuándo.
5. Los enfermeros auxiliares pueden descargar trabajo del médico sin poder
   habilitar a nadie.
6. El buzo sabe en todo momento qué le falta, qué está en revisión y qué está en
   orden, sin tener que preguntarle a nadie.
7. La aptitud se calcula, no se declara.

### No objetivos (fuera de alcance, no se tocan)

- **La Bitácora de Buceo completa**: actividades de buceo, registros de inmersión,
  escaneo de QR, rol de instructor. Queda exactamente como está.
- **La generación del PDF del Anexo 27**: hoy el botón está deshabilitado con el
  cartel "implementación futura". Sigue deshabilitado.
- **Avisos por correo de estudios próximos a vencer.** Se discutió y se dejó
  explícitamente para una etapa posterior.
- **La pantalla de Permisos.** Se oculta de la navegación. El acceso del médico y
  de los enfermeros ya no pasa por ahí.
- **La protección de los archivos subidos.** Decisión explícita, tomada sabiendo
  qué implica, porque esta etapa es una prueba de si el sistema sirve; si resulta,
  se mejora la seguridad antes de usarlo en serio. Lo que queda expuesto, para que
  quede escrito: `nginx.conf` proxea `/media/` sin autenticación y `core/urls.py`
  sirve `MEDIA_ROOT` bajo `DEBUG`, que además está fijo en `True` en
  `core/settings.py` sin forma de apagarlo por entorno. **Con la dirección de un
  archivo, cualquiera abre el estudio médico de cualquier buzo sin estar
  logueado**, y `DEBUG = True` en producción además expone trazas de error y
  configuración. Mientras esto siga así conviene no cargar estudios de personas
  reales más allá de lo necesario para probar. Apagar `DEBUG` por variable de
  entorno es la parte barata y se puede hacer sola, cuando se quiera, sin tocar
  nada de lo demás.

### Anti-objetivos (qué haría fracasar esto aunque funcione)

- **Que el buzo tenga que entender el circuito interno.** Si en su pantalla
  aparece la diferencia entre "revisado por el enfermero" y "aprobado por el
  médico", fracasó. Para él es "En revisión" y nada más.
- **Que cargar un estudio requiera elegir correctamente de una lista.** Hoy el
  buzo abre un desplegable con ocho renglones larguísimos y tiene que acertar.
  Eso se elimina.
- **Que el médico tenga que cargar datos.** Su trabajo es mirar y dictaminar. Si
  el rediseño le agrega tipeo, fracasó. (Por esto la fecha del estudio la carga el
  buzo, no él.)
- **Que la aptitud dependa de que alguien se acuerde de algo.** Ningún vencimiento
  se marca a mano.
- **Que el listado del médico se vuelva lento** por bajar todo al navegador.

---

## 3. Restricciones

- **Stack existente**, sobre el que hay que construir: Django 6.0.3 +
  Django REST Framework 3.16.1 + dj-rest-auth + django-allauth en el backend,
  SQLite como base, React 19 + Bootstrap 5 + react-router 7 + axios en el
  frontend. Despliegue con docker-compose, nginx sirviendo el frontend y
  proxyando `/api/` y `/media/`.
- **Los archivos van al disco**, no a la base. Django guarda el archivo en
  `MEDIA_ROOT` y en la base queda la ruta. 1.200 filas no son un problema para
  SQLite; el disco sí es un recurso finito.
- **El envío de correos hoy no funciona.** `core/settings.py` tiene configuración
  SMTP apuntando a Gmail con credenciales de ejemplo
  (`tu_correo@gmail.com` / `tu_contraseña_de_aplicacion`). Hay que mover eso a
  variables de entorno y conseguir una cuenta real con contraseña de aplicación.
  **En desarrollo se usa el backend de consola** para poder ver el texto exacto de
  los correos sin mandar nada.
- **Idioma: castellano rioplatense, registro formal e impersonal.** Ver §10.
- **Pillow 12.1.1 ya está instalado** y alcanza para el procesamiento de imágenes.
  Falta soporte HEIC (ver §9).

---

## 4. El dominio: los ocho estudios y sus reglas

La fuente es la **Directiva Técnica del DGS Nro 443/21**. El texto literal de los
puntos a. al h. es la lista de estudios exigidos:

| | Estudio | Vigencia | ¿A quién? |
|---|---|---|---|
| a | Electrocardiograma de esfuerzo | 1 año | **Solo a partir de los 40 años** |
| b | Ecocardiograma con informe (sin excepción) | 1 año | Todos |
| c | Electroencefalograma | 1 año | Todos |
| d | Radiografía de tórax, frente y perfil | 1 año | Todos |
| e | Radiografía de senos frontales y paranasales | 1 año | Todos |
| f | Hemograma, eritrosedimentación, dosaje de urea, dosaje de glucosa y orina completo | 1 año | Todos |
| g | Ficha de control odontológico (actualizada) | 1 año | Todos |
| h | Anexo 27 ORIGINAL, firmado por el médico militar y Jefe de Elemento | **30 días** | Todos |

**Sobre el punto f., atención:** la constante `STUDY_OPTIONS` del frontend lo
transcribe hoy como *"Hemograma, eritrosedimentación, urea, glucosa, orina,
**CHAGAS (máx 30 días)**"*. Esa versión es incorrecta y queda derogada por la tabla
de arriba. El CHAGAS no figura en la directiva y se quitó de forma explícita, y la
vigencia del punto f. es de **un año** como el resto de a. al g. — los 30 días son
exclusivos del Anexo 27. La tabla de esta sección es la fuente de verdad; la
constante del frontend no lo es y desaparece (§14).

**Los puntos i. y j. de la directiva no son estudios** y no van en la lista:

- **i.** describe la entrega física (los estudios a. al g. se presentan en un sobre
  identificado con grado, nombre y apellido). Es un procedimiento fuera del
  sistema.
- **j.** es la regla general de vigencia: ningún estudio puede superar el año. De
  ahí sale la columna "Vigencia" de la tabla.

El texto completo del punto h. incluye la condición de validez — no vale sin las
firmas correspondientes, incompleto, tachado o con errores. Eso no se modela como
estado: es exactamente para lo que existe el motivo de rechazo.

### Reglas derivadas

**Vigencia.** Se calcula desde la **fecha del estudio** (la fecha impresa en el
documento, que carga el buzo), no desde la fecha de subida. Un año para a–g,
30 días para h. **Y se evalúa contra la fecha de habilitación que eligió el buzo,
no contra el día de hoy** — ver §4.1, que es lo que vuelve coherente todo este
cálculo.

**Edad.** El criterio de la unidad es **la edad que el buzo va a tener a fin de
año**, no la que tiene el día que se consulta. O sea:

```
edad = año de la habilitación − año de nacimiento
```

El que cumple 40 en cualquier momento del año ya debe el punto a. para ese año, aun
si se presenta en marzo y todavía tiene 39. Es un criterio por año calendario, no
por cumpleaños, y conviene implementarlo literalmente así — una resta de años, no
un cálculo de edad cumplida — porque cualquier intento de ser más preciso va a dar
distinto de lo que espera la unidad.

Por eso la edad **no puede ser un número que el buzo escriba**: hoy
`UserProfile.age` es un entero cargado a mano que se desactualiza solo, y con eso la
regla falla en silencio. Se reemplaza por **fecha de nacimiento**, de la que sale el
año.

Nota de borde que queda como lectura mía: el año que se usa es el de la fecha de
habilitación elegida. Para la fecha complementaria, que cae en julio del año
siguiente, eso significa un año más y por lo tanto más exigencia, nunca menos.

**Unicidad del slot.** Cada buzo tiene a lo sumo un estudio vigente por punto de
la directiva. Subir un reemplazo no agrega una fila nueva a la vista: ocupa el
lugar del anterior.

**Un solo archivo por punto, y el punto se dictamina completo o nada.** Esto es
una decisión tomada, no una limitación a resolver. Dos puntos de la directiva
abarcan varios documentos físicos — el **d.** son dos placas (frente y perfil) y el
**f.** son cinco análisis distintos — y aun así cada punto se presenta como **un
único archivo**. Es responsabilidad del buzo consolidarlo: las dos placas en una
misma foto, o los cinco análisis en un solo PDF o una sola imagen. Si falta algo o
hay algo mal, **el punto entero queda rechazado**; no existe el estado de punto
parcialmente presentado.

La consecuencia de diseño es que la pantalla de carga tiene que **advertirlo antes
de que el buzo saque la foto**, no después. Cada punto lleva su propio texto de
ayuda en la pantalla de carga, y en d. y f. ese texto es obligatorio:

- **d.** "El archivo debe incluir las dos placas, frente y perfil."
- **f.** "El archivo debe incluir los cinco análisis: hemograma,
  eritrosedimentación, urea, glucosa y orina completo."

Sin esa advertencia, el rechazo por documentación incompleta va a ser el motivo
más frecuente del sistema, y es el más evitable de todos. Los rechazos de este
tipo caen en el motivo "Otros", con el detalle indicando qué faltó.

---

## 4.1 Las tres fechas de habilitación

Los buzos **no se habilitan de forma continua**. Se presentan en **tres
oportunidades por año**, cuyas fechas exactas cambian todos los años pero suelen
caer una en noviembre, una en diciembre y una en julio del año siguiente. **Cada
buzo elige una de las tres** y a esa fecha se presenta con sus estudios.

Esto no es un detalle administrativo: **es lo que le da sentido a toda la vigencia
del sistema.**

**La aptitud se evalúa contra la fecha elegida, no contra el día de hoy.** Un
estudio que hoy está vigente pero vence antes de la fecha de presentación no
sirve, y el sistema tiene que decirlo con tiempo en lugar de dejar que el buzo se
entere el día que se presenta. Al revés, un estudio que hoy figura vencido pero se
va a renovar antes de la fecha no es una urgencia.

**Esto resuelve el problema del Anexo 27.** Como vale 30 días, no se puede
presentar con anticipación: tiene que estar fechado **dentro de los 30 días previos
a la fecha elegida**. Por eso el sistema tiene que avisarle al buzo **desde cuándo**
puede presentarlo, en lugar de pedírselo todo el año y marcárselo vencido una y
otra vez. Evaluado contra la fecha de presentación, el listado del médico deja de
estar permanentemente en rojo y los contadores de arriba vuelven a significar algo.

**Qué es el Anexo 27 y por qué igual cuenta para el apto.** Certifica otra serie de
estudios médicos más básicos, los que se exigen en cualquier actividad de las
Fuerzas Armadas; los otros siete puntos son específicos de buceo. Es decir: es un
requisito previo que el buzo trae, no un producto de esta habilitación. Cuenta para
el apto como los demás.

**Prácticamente todos los años hay que traer estudios nuevos**, porque las
vigencias son anuales y las presentaciones también.

### Las fechas son rangos, y se publican de a una

Dos características que condicionan la implementación:

**Cada fecha es un rango de días, no un día.** La primera del ciclo actual es el
**18 al 20 de noviembre**. Tres días. El modelo tiene que ser un rango con inicio y
fin, y la regla de vigencia es la conservadora: **un estudio tiene que estar vigente
todos los días del rango**, no solo el primero. Si no, la aplicación podría declarar
apto a alguien cuyo estudio vence el día 2 de los 3.

De ahí sale la ventana del Anexo 27: tiene que estar fechado dentro de los 30 días
previos al **último** día del rango, que es el día más exigente. Esa resta es la
fecha de "desde cuándo lo puede presentar" que se le muestra al buzo.

**Las tres fechas no se conocen al mismo tiempo.** Hoy está confirmada la primera
(18–20 de noviembre) y todavía no se saben la segunda ni la complementaria. El admin
las va cargando a medida que se definen, así que el sistema tiene que funcionar con
un ciclo incompleto. Las tres se identifican por su lugar en el ciclo: **1.ª fecha,
2.ª fecha y complementaria**.

Esto tiene una consecuencia que es fácil pasar por alto: **un buzo sin fecha elegida
no siempre es un buzo que no hizo su parte.** Puede querer anotarse en la
complementaria y esa fecha todavía no existe. La aplicación no debe reprenderlo por
no haber elegido cuando no hay nada que elegir; debe decirle que la fecha todavía no
está publicada y avisarle cuando se publique.

### Consecuencias de diseño

- **El admin carga las fechas de habilitación**, de a una, con su rango y su lugar
  en el ciclo. Cambian todos los años y se definen en momentos distintos, así que no
  pueden estar en el código.
- **El buzo se inscribe a una** desde su pantalla, y puede cambiarla mientras esa
  fecha no haya pasado. Cambiarla recalcula todos sus vencimientos.
- **La fecha elegida se muestra en el listado del médico y en la ficha**, porque
  cambia el significado de todos los vencimientos de esa fila. Dos buzos con los
  mismos estudios y fechas distintas no están en la misma situación.
- **Un buzo que todavía no eligió fecha es un caso real** y hay que mostrarlo como
  tal, no asumirle una.
- **El Anexo 27 tiene una ventana de presentación**, no solo un vencimiento. Antes
  de esa ventana la pantalla del buzo no debe pedírselo como si fuera un faltante:
  debe decir desde cuándo lo puede subir.

---

## 5. Roles y accesos

Cuatro roles. El admin los designa.

| Rol | Quién | Qué puede hacer |
|---|---|---|
| **Buzo** | Todos por defecto al registrarse | Ve y gestiona sus propios estudios. Nada más. |
| **Enfermero auxiliar** | Designado por el admin, varios | Ve los estudios de **todos** los buzos. Puede aprobar (pre-aprobación) y rechazar. **No puede declarar apto.** |
| **Médico** | Designado por el admin, se espera uno | Ve los estudios de todos. Aprueba y rechaza. Su aprobación es la que cuenta. |
| **Admin** | Superusuario | Ve la lista de usuarios, designa médico y enfermeros, elimina duplicados. |

**El médico, los enfermeros y el admin no presentan estudios en esta aplicación.**
No suben nada y **no aparecen en "Personal a controlar"**. Esto simplifica el
modelo: el rol es único y excluyente, no hace falta una condición de "es buzo"
superpuesta a los demás roles. El que es designado médico o enfermero deja de ser
un registro a controlar.

**El acceso no se otorga por buzo.** El médico y los enfermeros ven a todos por su
rol. Esto reemplaza el circuito actual, donde cada buzo tenía que otorgarle
permiso al médico sobre sus propios estudios desde la pantalla de Permisos.

El modelo `Permission` que existe hoy **no se elimina** — se deja de usar como vía
de acceso y la pantalla sale de la navegación. Borrarlo es trabajo innecesario y
riesgoso; dejarlo huérfano no cuesta nada.

### Registro

**Abierto, sin habilitación previa.** Cualquiera puede crearse el usuario y
empezar a subir. El admin controla después, comparando la lista de usuarios
contra sus propios registros de personal para detectar novedades.

**Pero no se permiten duplicados de correo ni de DNI.** Esto es lo que hace
viable ese control manual: si la misma persona puede registrarse dos veces, la
comparación contra los registros propios no sirve. Hoy el correo ya es único
(`ACCOUNT_UNIQUE_EMAIL = True`) pero **el DNI es un campo opcional que se carga
después del registro y sin control de duplicados**. Pasa a ser obligatorio en el
registro y único en la base.

Datos que se piden al registrarse: grado, nombre, apellido, DNI, unidad, fecha de
nacimiento, correo electrónico (pedido dos veces, §15.11).

### El grado es una lista cerrada

Hoy `UserProfile.rank` es texto libre. Con 150 personas escribiendo su propio
grado se terminaría con "Sgto", "Sgto.", "Sargento" y "SG" conviviendo en la misma
base, lo que rompe el buscador del médico y arruina el cotejo manual del admin
contra sus registros de personal. Pasa a ser un desplegable con estos valores,
agrupados en dos categorías:

**Oficiales:** GD · GB · CY · CR · TC · MY · CT · TP · TT · ST

**Suboficiales:** SM · SP · SA · SI · SG · CI · CB

El orden de cada grupo es jerárquico, de mayor a menor, y conviene conservarlo tal
cual en el desplegable y en el orden del listado. La agrupación también se muestra
en el desplegable, para que elegir sea rápido.

---

## 6. El circuito de revisión

```
                         ┌──────────────────────────┐
  El buzo sube  ───────▶ │  EN REVISIÓN             │
  (archivo + fecha)      │  nadie lo tocó todavía   │
                         └──────┬──────────┬────────┘
                                │          │
          enfermero aprueba     │          │   médico aprueba directo
                                ▼          │
                   ┌─────────────────────┐ │
                   │  PRE-REVISADO       │ │
                   │  "Revisado por      │ │
                   │   SG Vera el 3/11"  │ │
                   └──────────┬──────────┘ │
                              │            │
             médico aprueba   │            │
                              ▼            ▼
                         ┌──────────────────────────┐
                         │  APROBADO                │  ◀── el único estado
                         │  cuenta para el apto     │      que habilita
                         └──────────────────────────┘
                                      │
                           pasa la vigencia
                                      ▼
                         ┌──────────────────────────┐
                         │  VENCIDO                 │
                         └──────────────────────────┘

  Desde EN REVISIÓN o PRE-REVISADO, el enfermero **o** el médico pueden rechazar:

                         ┌──────────────────────────┐
                         │  RECHAZADO               │ ──▶ correo al buzo
                         │  con motivo y detalle    │     y vuelve a "Falta subir"
                         └──────────────────────────┘
```

### La asimetría, que es deliberada

**La aprobación del enfermero no es definitiva. Su rechazo sí.**

El motivo: rechazar un estudio no habilita a nadie, solo pide un documento mejor.
Si un enfermero rechaza de más, el costo es que el buzo suba la foto de nuevo. Lo
único que el médico no puede delegar es decir que alguien está apto.

La consecuencia práctica es que los enfermeros le sacan al médico el trabajo de
descartar documentos ilegibles o fuera de plazo, que es el grueso del volumen,
y le dejan solo la firma sobre lo que efectivamente sirve.

### El médico puede aprobar sin abrir

Cuando un estudio llega pre-revisado, el médico puede aprobarlo directamente
confiando en el enfermero, o abrirlo y decidir él. Las dos cosas tienen que estar
a un clic en la fila, sin pasos intermedios. También puede aprobar directo un
estudio que ningún enfermero tocó, para los días en que está solo.

### Qué registra cada dictamen

Quién (usuario), con qué rol, cuándo, qué decidió, y en los rechazos el motivo y
el detalle. **El historial no se sobrescribe**: si un enfermero pre-aprueba y el
médico después rechaza, quedan los dos dictámenes.

### Motivos de rechazo

Lista cerrada, más un campo de detalle en texto libre que se completa siempre:

1. Estudio fuera del plazo de la directiva
2. Valores no aptos para realizar la actividad
3. Documento ilegible
4. Otros

El detalle va al correo del buzo y se muestra textual en su pantalla, porque es
lo que le dice qué tiene que hacer para arreglarlo.

### Reemplazo e historial

Cuando el buzo sube el reemplazo de un estudio rechazado o vencido, el nuevo ocupa
el slot y el anterior queda como histórico, **no visible en la vista normal**. Se
conserva porque es un registro médico militar y conviene que quede rastro de qué
se presentó y por qué se rechazó.

---

## 7. Estados derivados

**Ningún estado se tipea ni se guarda como campo de texto.** Todos salen de los
dictámenes y las fechas. Esto es lo que hace que la aptitud se caiga sola el día
que algo vence.

### Por estudio (lo que ve el médico en la ficha)

| Estado | Cuándo | Cómo se ve |
|---|---|---|
| **No corresponde** | No exigido por edad | Gris y tachado |
| **Sin presentar** | Exigido y no subido | Gris |
| **En revisión** | Subido, sin dictamen | Resaltado, con botones de acción |
| **Pre-revisado** | Aprobado por enfermero, sin aprobación del médico | Resaltado, "Revisado por …", con botones |
| **Aprobado** | Aprobado por el médico y dentro de vigencia | Verde, con quién y cuándo |
| **Rechazado** | Último dictamen es un rechazo | Rojo, con motivo y detalle a la vista |
| **Vencido** | Aprobado pero pasada la vigencia | Rojo |

**Los dos grises son distintos a propósito.** "Sin presentar" significa que alguien
tiene que hacer algo; "No corresponde" significa que nadie tiene que hacer nada.
Pintarlos igual haría parecer que a un buzo de 31 años le faltan dos estudios
cuando le falta uno.

### Por buzo (lo que ve el médico en el listado)

| Estado | Cuándo |
|---|---|
| **Sin fecha** | No se inscribió a ninguna fecha de habilitación, así que no hay contra qué medirlo |
| **Apto** | Todos los estudios exigidos por su edad, aprobados por el médico y vigentes en toda su fecha |
| **Vencido** | Hay al menos un estudio vencido |
| **Rechazado** | Hay al menos un estudio rechazado |
| **Incompleto** | Falta subir al menos uno |
| **A revisar** | Está todo subido y hay dictámenes pendientes |

**Vencido y Rechazado tienen prioridad** sobre los demás en la fila, porque son los
dos que necesitan que alguien actúe ya.

### La definición de apto

> Un buzo está apto cuando, para **cada** estudio que le corresponde según su edad,
> existe una **aprobación del médico** y el estudio estará **dentro de su vigencia
> en la fecha de habilitación que el buzo eligió**.

Nadie la firma. Las aprobaciones de los enfermeros no cuentan para esto.

Tres precisiones que se siguen de §4.1:

- **La vigencia se mide contra el rango de la fecha elegida, no contra hoy**, y el
  estudio tiene que estar vigente todos los días de ese rango. Un estudio que vence
  entre hoy y esa fecha no sirve, y hay que decírselo ahora.
- **La edad es la del año de la habilitación** (§4, una resta de años), no la
  cumplida al día de hoy. El que cumple 40 en cualquier momento de ese año debe los
  ocho estudios.
- **Un buzo sin fecha elegida no puede estar apto**, porque no hay contra qué
  medirlo. Su estado es "Sin fecha de habilitación", y es lo primero que tiene que
  resolver.

---

## 8. Las pantallas

Hay **bocetos aprobados** de las tres primeras, versionados junto a este documento
en `docs/superpowers/specs/2026-11-03-bocetos/`:

| Archivo | Pantalla |
|---|---|
| `1-listado-medico.html` | §8.1 Listado del médico |
| `2-ficha-buzo.html` | §8.2 Ficha de un buzo |
| `3-pantalla-buzo.html` | §8.3 Pantalla del buzo (celular + carga) |

**Son la referencia visual de este diseño** y conviene abrirlos en el navegador
antes de planificar. Dos advertencias sobre ellos:

- Son fragmentos HTML sacados del asistente visual de la sesión de diseño, sin
  `<html>` ni hojas de estilo propias, así que sueltos se ven sin formato de página.
  El contenido y la disposición son lo que importa.
- **Los textos de `2-ficha-buzo.html` llevan todavía el tono anterior** y deben
  pasarse a impersonal (§10). El de la pantalla del buzo ya está corregido.
- **Ninguno de los tres muestra la fecha de habilitación** (§4.1), porque se definió
  después de aprobarlos. Esa parte hay que agregarla a las tres pantallas.

### 8.1 Listado del médico

Es la herramienta de trabajo diaria. Una fila por buzo.

- **Resumen arriba**: cuántos aptos, cuántos a revisar, cuántos vencidos.
- **Buscador** por nombre, apellido, DNI y grado, en un solo campo.
- **Filtros** (los que pidió el médico): Todos · Documentación completa ·
  Documentación incompleta · Pendientes de revisar. Con el conteo en cada uno.
  **"Documentación completa" significa que están subidos todos los estudios
  exigidos, con independencia del dictamen.** Un buzo con un estudio rechazado
  cuenta como completo, porque el papel está presentado. No es sinónimo de Apto, y
  no tiene que serlo: Apto ya tiene su propio contador arriba.
- **Orden** por apellido, por última vez revisado, o por cantidad de pendientes.
- **Columnas**: grado y nombre (con unidad debajo), DNI, edad, **Presentados
  (6/7 u 6/8 según la edad)**, **A revisar**, **Última vez revisado**, estado.

Dos detalles que no son cosméticos:

- **El denominador del contador cambia con la edad.** Es la señal más visible de
  que la regla de los 40 está funcionando.
- **La columna de fecha es "Última vez revisado", no "Último estudio subido".**
  Con 150 buzos, lo que el médico necesita es encontrar a quién hace más tiempo
  que no mira, no quién subió último. El orden por fecha sigue a esta columna.
  Un buzo sin ningún dictamen muestra "Sin revisar". **Cuenta solo los dictámenes
  del médico, no los de los enfermeros**: si las pre-aprobaciones de los enfermeros
  sellaran esta columna, un enfermero despachando la cola un día ocupado le
  arruinaría el orden al médico y le taparía justo la señal que vino a buscar.
- **La columna "A revisar" distingue lo que nadie tocó de lo que viene
  pre-revisado** esperando la firma del médico. Esa segunda pila es la que puede
  despachar rápido.

**Los filtros se conservan al volver del detalle.** Van en la query string de la
URL, no en estado de React: así funciona el botón de atrás del navegador, se puede
recargar la página sin perder nada, y el médico puede mandarle un enlace a alguien.

### 8.2 Ficha de un buzo (vista del médico)

- **Encabezado** con grado, apellido, nombre, DNI, edad, unidad y cuántos estudios
  le corresponden.
- **Cuatro contadores**: Presentados (6/7), **Aprobados (2/7)**, A revisar,
  Con problema. *Aprobados es el número que importa*, porque el apto sale de ahí;
  Presentados solo dice cuánto papel juntó.
- **Los ocho puntos de la directiva en orden a–h**, siempre los ocho, cada uno con
  su estado de §7. El médico controla contra la lista, así que la ve en el orden de
  la directiva.
- **Solo lo que espera dictamen tiene botones**: Ver, Aprobar, Rechazar. Lo
  resuelto no tiene acciones más que Ver.
- **Cada dictamen dice quién y cuándo en la fila**, sin abrir nada. El motivo del
  rechazo se muestra textual.
- **Volver al listado** conserva los filtros.
- **Rechazar abre un diálogo** con los cuatro motivos, el campo de detalle, y el
  aviso explícito de que al confirmar se le manda un correo al buzo, con la
  dirección a la vista.

### 8.3 Pantalla del buzo

La pantalla que más cuidado necesita. Mobile-first.

- **Una sola pantalla.** Sin pestañas, sin "Mis estudios" contra "Compartidos", sin
  sección de permisos. Abre y ve lo que importa.
- **Lo primero es la fecha de habilitación.** Arriba de todo, a qué fecha está
  inscripto, con la opción de cambiarla. Si no eligió ninguna y hay fechas
  publicadas, elegir es la acción principal de la pantalla, por encima de los
  estudios: sin fecha, lo demás no se puede calcular. Si no eligió porque todavía no
  se publicó la que le interesa, el texto lo dice así y no como un reproche (§4.1).
- **Arriba, en grande, cuántos estudios faltan.** Es la única pregunta que el buzo
  se hace. Al llegar a cero, ese bloque pasa a verde.
- **Barra de progreso** con "2 de 7 revisados".
- **Cuatro grupos, en orden de urgencia, con estos títulos exactos**:
  **Falta subir** → **En revisión** → **Revisados** → **No corresponde**.
  El médico ve los ocho puntos en orden alfabético porque controla la lista; el
  buzo ve primero su tarea.
- **Un botón grande por estudio** en "Falta subir", que abre la cámara o los
  archivos.
- **El motivo del rechazo, textual**, en la misma tarjeta donde está el botón para
  arreglarlo.
- **Lo que no corresponde se muestra igual**, apagado y explicado ("Se exige a
  partir de los 40 años de edad"). Si se escondiera, el que cumple 40 se
  encontraría de golpe con un estudio nuevo sin entender de dónde salió.
- **Fechas escritas en castellano**: "Vence el 12 de octubre de 2027", no
  "12/10/2027" ni "vigencia 365 días".

#### La carga de un estudio

**El buzo no elige el tipo de estudio de una lista.** Entra apretando el botón de
ese estudio, así que el slot ya está determinado. Esto elimina el desplegable de
ocho renglones largos que hay hoy y es el cambio que más errores de carga evita.

Quedan **dos campos**:

1. **Fecha que figura en el documento**, con la aclaración de que es la fecha
   impresa en el estudio y no la de hoy.
2. **Archivo**: tomar foto o elegir archivo.

La fecha la carga el buzo a propósito, aunque sea el dato más fácil de equivocar.
Se evaluó que la cargara el médico al revisar (tiene el documento delante) y se
descartó: **le agrega trabajo al médico, que es el recurso escaso**. El control
queda del lado del médico, que compara la fecha cargada contra el documento y, si
no coincide, ya tiene el motivo "Estudio fuera del plazo de la directiva".

Debajo, el aviso de que la imagen se reduce automáticamente y no hace falta hacer
nada.

### 8.4 Pantalla de los enfermeros auxiliares

**Son las mismas dos pantallas del médico (8.1 y 8.2), con tres diferencias.** No
se construye una interfaz aparte.

1. **No ven nada de la aptitud.** Ni el estado Apto en el listado, ni el contador
   de aptos arriba, ni el contador "Aprobados 2/7" en la ficha. No es su decisión y
   mostrárselo invita a que alguien la tome.
2. **Entran ordenados al revés que el médico**: primero lo que nadie tocó, lo más
   viejo arriba. El médico quiere la pila rápida (lo pre-revisado esperando su
   firma); el enfermero quiere la pila cruda.
3. **Sus botones son Aprobar y Rechazar** igual que los del médico, pero su
   aprobación deja el estudio en Pre-revisado (§6).

### 8.5 Panel del admin

Pantalla nueva, no existe hoy.

- **Lista de usuarios registrados** con grado, apellido, nombre, DNI, correo,
  fecha de registro y rol. Pensada para cotejarse contra los registros propios de
  personal del admin, así que tiene que ser fácil de leer en orden y de exportar o
  copiar.
- **Designar médico** y **designar enfermeros auxiliares**.
- **Eliminar** un usuario duplicado o que no corresponde.
- **Cargar las fechas de habilitación** (§4.1): el rango de días y su lugar en el
  ciclo. Se cargan de a una, cuando se definen. La pantalla tiene que mostrar qué
  fechas del ciclo todavía faltan definir, porque eso es lo que les está bloqueando
  la inscripción a los buzos que esperan la complementaria.

---

## 9. Notificaciones

**Exactamente tres correos. No hay más.** Todos van al correo con el que el buzo
creó su usuario.

| Cuándo | Qué dice |
|---|---|
| **30 días antes de la fecha de habilitación a la que se inscribió** | Que ya puede cargar sus estudios médicos en la plataforma, qué le falta y cuántos días quedan |
| **Se rechaza un estudio** (lo rechace el enfermero o el médico) | Qué estudio fue, el motivo y el detalle escrito por quien lo rechazó |
| **Queda completo** | Que los estudios están sin novedad para presentarse a la habilitación |

### El recordatorio de los 30 días

Sale 30 días antes de la fecha, a los buzos inscriptos a esa fecha. Es el correo
que, en palabras de la unidad, hace que "no tengan excusas".

Tiene dos propiedades que lo hacen más útil que un recordatorio genérico:

- **Cae justo cuando se abre la ventana del Anexo 27** (§4.1), que es el documento
  que no se puede conseguir con anticipación. El momento no es arbitrario.
- **Puede decir qué le falta**, no solo que la fecha se acerca, porque el sistema ya
  lo sabe.

**Esto necesita algo que el proyecto no tiene: un proceso programado.** Hoy no hay
tareas periódicas en ningún lado — `docker-compose.yml` levanta solo backend y
frontend. Hace falta decidir cómo se dispara (ver §16), y lo mismo sirve para la
limpieza por retención de §12.

**Un hueco conocido, que queda anotado a propósito:** el buzo que todavía no se
inscribió a ninguna fecha no recibe este recordatorio, porque no hay fecha contra la
que contar los 30 días. Es justamente el que más necesitaría un empujón. No se
resuelve en esta etapa para no inventar un cuarto correo sin acordarlo, pero es la
primera cosa a revisar cuando el sistema esté en uso.

El correo de aptitud **se manda una sola vez**, en la transición a apto — cuando se
aprueba el último estudio que faltaba. No se vuelve a mandar cada vez que se
aprueba algo. Si después se le vence un estudio y más adelante vuelve a completar,
ahí sí se manda de nuevo, porque es una habilitación nueva. Esto requiere
**guardar que ya se notificó** y limpiar esa marca cuando el buzo sale del estado
apto; si no, un recálculo cualquiera dispara correos repetidos.

**No hay aviso de vencimiento próximo.** Se discutió, se reconoció que es el aviso
que más le serviría al buzo, y se dejó para una etapa posterior.

---

## 10. Tono y vocabulario

**Registro formal e impersonal. No se tutea y no se habla a la persona.**

| En lugar de | Va |
|---|---|
| "Te faltan 3 estudios" | **"Faltan 3 estudios"** |
| "Subí de nuevo el análisis" | **"Debe subirse nuevamente el análisis"** |
| "La doctora los está mirando" | **"En revisión"** |
| "Estos ya están bien" | **"Revisados"** |
| "Todavía no lo subiste" | **"Sin presentar"** |
| "No te corresponde" | **"No corresponde"** |
| "esperando tu revisión" | **"En revisión"** |

Vocabulario fijo, el mismo en toda la aplicación: **Falta subir · En revisión ·
Revisados · Sin presentar · No corresponde · Vencido el … · Faltan N estudios**.
Son las palabras con las que se habla del tema en la unidad, así que el buzo lee
en la pantalla lo mismo que escucha.

Esto aplica también a los correos y a las pantallas del médico.

---

## 11. Archivos: compresión y almacenamiento

El riesgo real no es la base de datos — 1.200 filas no son nada para SQLite — es
**el disco**. Una foto de celular pesa entre 3 y 8 MB; 1.200 fotos sin procesar son
unos 6 GB. Comprimidas quedan en unos 400 KB cada una, menos de medio GB en total,
sin perder legibilidad para leer un análisis de laboratorio.

**El buzo no se entera de nada. No hay ninguna opción ni ningún paso extra.**

- **En el navegador, antes de enviar**: se reduce la imagen. Además de ahorrar
  disco, hace que la subida sea rápida con datos móviles, que es la situación real
  de uso.
- **En el servidor, al recibir**: se vuelve a comprimir. Nunca hay que confiar en
  que el navegador hizo su parte — un cliente puede mandar cualquier cosa.
- **Resultado**: JPEG de 2.000 píxeles en el lado mayor, calidad 75, sin metadatos
  EXIF de la cámara.
- **Los PDF se dejan como están.** Los de laboratorio ya vienen livianos, y
  recomprimirlos arriesga que una radiografía quede ilegible, que es justo lo que el
  médico necesita poder leer.
- **Tope de tamaño** con un mensaje claro y en castellano si se pasa.

**Soporte HEIC, que hoy no existe y va a morder.** Los iPhone sacan fotos en HEIC
y el servidor no sabe abrirlo. El buzo va a apretar "tomar foto" y no tiene por qué
saber qué formato usa su teléfono. Hace falta agregar el soporte (p. ej.
`pillow-heif`) y convertir a JPEG en el servidor.

---

## 12. Retención

**Se conserva el año en curso y el anterior. Lo más viejo se borra**, archivo y
registro.

Cada año se vencen ocho estudios por buzo y se suben ocho nuevos, así que sin
política de retención el disco crece para siempre. Con esta regla se estabiliza en
el orden de 1 GB.

Esto necesita un proceso de limpieza que se pueda correr solo y que borre tanto la
fila como el archivo del disco — borrar la fila y dejar el archivo huérfano es el
error clásico acá.

**Dos salvaguardas que no son opcionales:**

1. **La limpieza nunca toca el estudio vigente de un slot**, por viejo que sea. Si
   se midiera la antigüedad contra `study_date` a secas, a un buzo cuya última
   ficha odontológica es de hace dos años se le borraría el documento que el médico
   está mirando en pantalla. Solo se borran las **versiones reemplazadas**, y la
   antigüedad se mide desde que fueron reemplazadas, no desde la fecha del estudio.
2. **Un estudio que todavía cuenta para el apto no se borra nunca**, cualquiera sea
   su fecha.

---

## 13. Escala y rendimiento

**Esto es un cambio de arquitectura, no una optimización.**

Hoy el dashboard se baja **todos** los estudios y **todos** los perfiles al
navegador y filtra en JavaScript. Con 150 buzos eso son más de 1.200 estudios con
sus dictámenes en cada carga: lento en la oficina y peor en un celular con datos
móviles.

**El buscador, los filtros, el orden, los contadores y la paginación van del lado
del servidor.** Hace falta un endpoint que devuelva **una fila por buzo, ya
contada** — presentados, exigidos según edad, pendientes de revisar, pre-revisados,
vencidos, rechazados, fecha del último dictamen, estado derivado — y de a páginas.
El navegador pide solo lo que muestra.

Es más trabajo que filtrar en el navegador. Es la diferencia entre que funcione y
que no.

Dos cosas a vigilar:

- **Las consultas N+1.** Calcular los contadores buzo por buzo con una consulta
  por fila es la forma más fácil de arruinar esto. Los conteos tienen que salir
  anotados en la consulta.
- **El estado derivado depende de la fecha de hoy**, así que no se puede
  precalcular y guardar sin un proceso que lo refresque. Conviene calcularlo en la
  consulta.

---

## 14. Modelo de datos: qué cambia

No es el esquema final, es el inventario de lo que este diseño exige que cambie.

**`users.UserProfile`**
- `birth_date` **reemplaza** a `age`. Sin esto la regla de los 40 falla en
  silencio. Hay que migrar los valores existentes (ver §16).
- `dni` pasa a **obligatorio y único**, y se pide en el registro.
- Agregar el rol **enfermero auxiliar** a `ROLE_CHOICES`, que hoy tiene
  `USER / DOCTOR / ADMIN`.
- `is_instructor` queda como está: es de la Bitácora y no se toca.

**`api.StudyBlock`**
- Necesita identificar **a qué punto de la directiva corresponde** (a–h) con un
  código, no por coincidencia de texto del título. Hoy el título es texto libre que
  el frontend llena desde una constante `STUDY_OPTIONS` hardcodeada en
  `Dashboard.jsx`; el script de datos de prueba ya crea estudios con títulos que no
  están en esa lista ("Audiometría Anual", "Electrocardiograma"), así que la
  coincidencia por texto no es confiable.
- **La lista de los ocho estudios tiene que vivir en el backend**, no en el
  frontend. Es la fuente de verdad del denominador del contador, de qué se exige
  por edad y de la vigencia de cada punto.
- Marcar cuál es el **vigente del slot** y cuáles son históricos.
- `study_date` ya existe y es la base del cálculo de vigencia.

**`api.Comment`** (el dictamen)
- Agregar el estado **pre-aprobado** a `STATUS_CHOICES`, que hoy tiene
  `APPROVED / REJECTED`.
- Guardar **con qué rol** dictaminó quien dictaminó: es lo que distingue la
  pre-aprobación del enfermero de la aprobación del médico, y lo que permite
  mostrar "Revisado por SG Vera".
- Agregar el **motivo de rechazo** como lista cerrada (§6), además del detalle en
  texto libre que ya existe en `content`.
- `doctor` y `created_at` ya dan el quién y el cuándo.

**Nuevo: fechas de habilitación** (§4.1). Hacen falta dos cosas:

1. Una tabla que administre el admin, donde cada fila es **un rango de días**
   (inicio y fin, p. ej. 18 al 20 de noviembre) más **su lugar en el ciclo**
   (1.ª, 2.ª, complementaria). Se cargan de a una, a medida que se definen, así que
   el ciclo incompleto es el estado normal y no un error.
2. En `UserProfile`, **a cuál se inscribió el buzo**, que puede estar vacío.

Las fechas cambian todos los años, así que no pueden ser una constante en el
código. **Prácticamente todo el cálculo de estados depende de este dato** —
vigencias, edad exigida, ventana del Anexo 27, apto y el recordatorio por correo —
así que conviene resolverlo primero: es el cimiento, no un agregado.

**Nuevo: marca de notificación de aptitud.** Para que el correo de apto se mande
una sola vez (§9).

**`api.Permission`**: se deja como está, sin usar.

---

## 15. Decisiones que tomé yo

Estas son mías, no acordadas. Están acá para que se puedan revisar.

1. **Los filtros se conservan en la query string de la URL**, no en estado de
   React. Hace funcionar el botón de atrás y la recarga, y permite compartir el
   enlace.
2. **El orden por fecha sigue a "última vez revisado"** en lugar de a la fecha de
   subida, que es lo que decía el pedido original. Con 150 buzos, lo útil es
   encontrar a quién hace más tiempo que no se mira.
3. ~~La regla de los 40 se evalúa con la edad cumplida al momento de consultar.~~
   **Derogada por la unidad: el criterio es la edad a fin de año. Ver el punto 16.**
4. **El historial de estudios reemplazados se conserva** (acotado por la política
   de retención de §12), aunque el pedido decía "reemplaza".
5. **"Unidad" se implementa sobre el campo `destination`** que ya existe en
   `UserProfile` (etiquetado "Destino"), renombrando la etiqueta, en lugar de
   agregar un campo nuevo.
6. **En desarrollo los correos van a la consola.** Sin esto no se puede trabajar
   en los textos de los correos, porque el SMTP real no está configurado.
7. **El modelo no prohíbe más de un médico** aunque hoy haya uno solo. Cerrarlo a
   uno es trabajo extra que no compra nada.
8. **Las credenciales SMTP van a variables de entorno.** Hoy están escritas en
   `core/settings.py`, que está en el repositorio.

Estas salieron de la revisión técnica del documento:

9. **Nadie dictamina sobre sus propios estudios.** Un enfermero que además es buzo
   podría pre-aprobarse solo, y el médico podría declararse apto. Queda prohibido a
   nivel de la validación, no solo de la interfaz. Si el médico además es buzo,
   hace falta que el admin designe un segundo médico para sus estudios.
10. **El buzo puede reemplazar un estudio que está En revisión o Pre-revisado**, no
    uno ya aprobado por el médico. El primero es el caso frecuente — sacó la foto
    cortada, se equivocó la fecha — y hacerlo esperar un rechazo para arreglarlo es
    cruel en una pantalla pensada para gente sin práctica. El segundo permitiría
    cambiar un documento a espaldas del médico, que en un registro médico militar
    es inaceptable. Al reemplazar, el estudio vuelve a En revisión y el dictamen
    anterior queda en el historial.
11. **No se verifica la dirección de correo.** Verificar agrega un paso bloqueante
    en el registro, justo donde los usuarios tienen menos práctica, y además hoy no
    hay SMTP funcionando. En cambio: el correo **se pide dos veces** en el registro
    para atajar el error de tipeo, y la pantalla del buzo muestra siempre a qué
    dirección se le mandan los avisos, con la opción de corregirla. El riesgo que
    queda es que un correo mal escrito deje a alguien sin enterarse de un rechazo;
    se mitiga con que el estado también se ve en la pantalla.
12. **Ni el correo de rechazo ni la pantalla del buzo nombran a quién lo rechazó.**
    Llevan el motivo y el detalle, nada más. Nombrarlo violaría el anti-objetivo de
    §2: el buzo no tiene que ver la diferencia entre un enfermero y el médico.
13. **"Última vez revisado" cuenta solo los dictámenes del médico** (§8.1).
14. **"Documentación completa" significa todo subido, no todo aprobado** (§8.1).
15. **La limpieza por retención nunca borra el estudio vigente de un slot** (§12).
16. **La edad se calcula como año de la habilitación menos año de nacimiento**, una
    resta de años y no una edad cumplida, porque el criterio de la unidad es la edad
    que el buzo va a tener a fin de año (§4). Para la fecha complementaria, que cae
    en julio del año siguiente, el año que se usa es el de esa fecha — lo que suma
    exigencia, nunca la resta.
17. **Un estudio tiene que estar vigente todos los días del rango** de la fecha de
    habilitación, no solo el primero, y la ventana del Anexo 27 se calcula contra el
    último día del rango. Es la lectura conservadora: la otra podría declarar apto a
    alguien cuyo estudio vence a mitad de la presentación.
18. **El buzo puede cambiar la fecha elegida mientras no haya pasado.** Cambiarla
    recalcula todos sus vencimientos, así que la pantalla tiene que mostrar el
    efecto, no cambiarlo en silencio.
19. **Antes de su ventana, el Anexo 27 no se muestra como faltante.** Dice desde
    cuándo se puede presentar. Mostrarlo en rojo durante once meses entrena al buzo
    a ignorar el rojo.
20. **El rol es único y excluyente.** Se desprende de que el médico, los enfermeros
    y el admin no presentan estudios: no hace falta una condición "es buzo"
    superpuesta.
21. **Al buzo que no se pudo inscribir porque su fecha no está publicada, la
    aplicación no se lo reprocha.** Le dice que la fecha todavía no se definió. La
    diferencia entre "no eligió" y "no hay nada que elegir" tiene que estar en la
    pantalla (§4.1).

---

## 16. Lo que queda a criterio de quien construya

- **Cómo se migran los `age` existentes a `birth_date`.** No se puede derivar una
  fecha de nacimiento de una edad. Los datos actuales son de prueba, así que lo más
  probable es que se recreen; si hubiera datos reales, hay que decidir si se pide a
  cada buzo que complete la fecha al entrar.
- **Cuántas filas por página** en el listado del médico, y si se pagina o se
  carga por scroll.
- **Cómo se implementan los filtros y el orden** del lado del servidor: backends de
  filtrado de DRF o parámetros propios.
- **Con qué se comprime la imagen en el navegador.**
- **Cómo se disparan los dos procesos periódicos** — el recordatorio de los 30 días
  (§9) y la limpieza por retención (§12). Hoy el proyecto no tiene nada programado:
  `docker-compose.yml` levanta backend y frontend y nada más. Las opciones razonables
  son un comando de Django invocado por cron en el host, un contenedor aparte, o un
  servicio de tareas. Lo que sí es parte del diseño es que el recordatorio **no puede
  depender de que alguien entre a la aplicación** para dispararse, y que mandar el
  mismo recordatorio dos veces es un error visible para el buzo, así que hace falta
  registrar que ya se envió.
- **Dónde vive la lista de los ocho estudios en el backend**: constante en código,
  tabla de catálogo, o `TextChoices`. Lo que sí es parte del diseño es que viva en
  el backend.
- **Si el panel del admin se construye como pantalla propia o sobre el admin de
  Django.** Hay que tener en cuenta que el admin tiene que poder cotejar una lista
  de 150 personas cómodamente.
- **El orden de implementación y el plan de pruebas.**

---

## Apéndice: por dónde está hoy cada cosa

| Qué | Dónde |
|---|---|
| Listado y agrupación actual (acordeón "Compartidos conmigo") | `frontend/src/components/Dashboard.jsx` |
| Lista de los ocho estudios, hardcodeada | `frontend/src/components/Dashboard.jsx`, constante `STUDY_OPTIONS` |
| Estudios, dictámenes y permisos | `backend/api/models.py` |
| Perfil, rol y DNI | `backend/users/models.py` |
| Acceso a estudios por permisos | `backend/api/views.py`, `StudyBlockViewSet.get_queryset` |
| Validación de quién puede dictaminar | `backend/api/views.py`, `CommentViewSet.perform_create` |
| Configuración SMTP con credenciales de ejemplo | `backend/core/settings.py` |
| Rutas del frontend | `frontend/src/App.jsx` |
| Pantalla de Permisos (a ocultar) | `frontend/src/components/Permissions.jsx` |
| Bitácora (no se toca) | `frontend/src/components/Bitacora.jsx`, `CompleteDiveLog.jsx` |
| Datos de prueba | `backend/create_test_data.py` |
| Bocetos aprobados de las tres pantallas | `docs/superpowers/specs/2026-11-03-bocetos/` |
