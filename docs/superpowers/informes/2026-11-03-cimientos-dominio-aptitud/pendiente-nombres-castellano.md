# PENDIENTE (aprobado por el usuario) — nombres del panel de admin en castellano

**Estado:** encolado detrás del pase de correcciones de la revisión final (agente
a49ed5a3590ac7022), que está editando los mismos archivos. Aplicar en cuanto ese pase cierre y
su re-revisión esté limpia.

**Origen:** el usuario preguntó cómo entrar al panel de admin para designar médico y enfermeros
y cargar las fechas de habilitación. Al explicárselo noté que el panel muestra los nombres de
modelos y campos en inglés. Lo ofrecí, lo aprobó, y aprobó los términos exactos de abajo.

**Por qué importa:** el panel de Django es la única interfaz humana que entrega esta rama, y el
usuario (oficial de la unidad, no desarrollador) es quien la va a usar para designar roles y
cargar las tres fechas del año.

## Etiquetas aprobadas

### Secciones (verbose_name en los AppConfig)
- `api` -> **Aptitud médica**
- `users` -> **Personal**

### Modelos (Meta.verbose_name / verbose_name_plural)
- `UserProfile` -> **Perfil** / **Perfiles**
- `HabilitationWindow` -> **Fecha de habilitación** / **Fechas de habilitación**
- `StudyBlock` -> **Estudio médico** / **Estudios médicos**
- `Comment` -> **Dictamen** / **Dictámenes**
- `ProfileFieldTemplate` -> **Campo de perfil** / **Campos de perfil**

### Campos de HabilitationWindow
- `cycle` -> **Ciclo (año)**
- `slot` -> **Lugar en el ciclo**
- `start_date` -> **Fecha de inicio**
- `end_date` -> **Fecha de fin**

### Campos de UserProfile
- `role` -> **Rol**, `dni` -> **DNI**, `birth_date` -> **Fecha de nacimiento**,
  `rank` -> **Grado**, `destination` -> **Destino**, `phone` -> **Teléfono**,
  `weight` -> **Peso**, `height` -> **Altura**,
  `habilitation_window` -> **Fecha de habilitación elegida**

### Encabezado del panel
Reemplazar "Django administration" por un título propio (site_header, site_title, index_title).

## Restricciones

- **NO tocar las etiquetas de `ROLE_CHOICES`**: el pase de correcciones ya las cambia a
  Buzo / Enfermero auxiliar / Médico / Administrador (ítem 5 del brief final). No pisarlo.
- **Necesita una migración nueva**: Django trata verbose_name como parte del campo, así que
  genera AlterField. Inofensiva, no toca datos. Nunca reescribir una migración existente.
- `DiveActivity` y `DiveLog` no están registrados en el admin, así que no se ven; quedan afuera
  para mantener el cambio chico.
- `Permission` se deja como está (el spec §5 dice dejarlo).
- La suite tiene que seguir pasando y `makemigrations --check` tiene que quedar limpio.
