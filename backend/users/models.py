from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    # Etiquetas en castellano: el admin de Django es donde el oficial de la
    # unidad designa los roles, y son los nombres del §5. Los valores quedan en
    # ingles porque los usa el codigo.
    ROLE_CHOICES = [
        ('USER', 'Buzo'),
        ('NURSE', 'Enfermero auxiliar'),
        ('DOCTOR', 'Médico'),
        ('ADMIN', 'Administrador'),
    ]
    # Lista cerrada de grados, en orden jerarquico.
    RANK_CHOICES = [
        ('Oficiales', [
            ('GD', 'GD'),
            ('GB', 'GB'),
            ('CY', 'CY'),
            ('CR', 'CR'),
            ('TC', 'TC'),
            ('MY', 'MY'),
            ('CT', 'CT'),
            ('TP', 'TP'),
            ('TT', 'TT'),
            ('ST', 'ST'),
        ]),
        ('Suboficiales', [
            ('SM', 'SM'),
            ('SP', 'SP'),
            ('SA', 'SA'),
            ('SI', 'SI'),
            ('SG', 'SG'),
            ('CI', 'CI'),
            ('CB', 'CB'),
        ]),
    ]
    RANK_VALUES = tuple(value for _, group in RANK_CHOICES for value, _ in group)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile',
        verbose_name='Usuario',
    )
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='USER', verbose_name='Rol',
    )
    is_instructor = models.BooleanField(default=False, verbose_name='Es instructor')
    profile_data = models.JSONField(
        default=dict, blank=True, verbose_name='Datos adicionales',
    )

    # Base fields requested by user
    dni = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name='DNI',
    )
    # Nullable a proposito: sin fecha de nacimiento no se puede derivar la edad.
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Fecha de nacimiento',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    rank = models.CharField(
        max_length=2, choices=RANK_CHOICES, blank=True, verbose_name='Grado',
    )
    destination = models.CharField(
        max_length=100, blank=True, verbose_name='Destino',
    )
    # Nullable: sin fecha elegida el buzo no puede estar apto, y no siempre es culpa suya.
    # PROTECT y no SET_NULL: borrar una ventana con buzos inscriptos los
    # des-inscribia en silencio y sin rastro. El administrador aca es un oficial
    # de la unidad, y el §4.1 dice que las fechas se completan despues, o sea que
    # el flujo real es editar. Una ventana sin nadie inscripto se borra igual.
    habilitation_window = models.ForeignKey(
        'api.HabilitationWindow', null=True, blank=True,
        on_delete=models.PROTECT, related_name='divers',
        verbose_name='Fecha de habilitación elegida',
    )
    weight = models.FloatField(null=True, blank=True, verbose_name='Peso')
    height = models.FloatField(null=True, blank=True, verbose_name='Altura')

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def save(self, *args, **kwargs):
        # Un DNI en blanco se guarda como NULL: el indice unico ignora NULL,
        # pero dos '' chocarian. Vale para cualquier via de escritura.
        if not self.dni:
            self.dni = None
        super().save(*args, **kwargs)

    def age_in_year(self, year):
        """Edad que se alcanza en `year`: resta de años, no edad cumplida."""
        if self.birth_date is None:
            return None
        return year - self.birth_date.year

    def __str__(self):
        # Se lee en los desplegables y encabezados del admin: grado y apellido es
        # como identifica a la persona la unidad. Sin esos datos cargados, cae al
        # nombre de usuario.
        etiqueta = ' '.join(
            parte for parte in (self.rank, self.user.last_name, self.user.first_name)
            if parte
        )
        return etiqueta or self.user.username

class ProfileFieldTemplate(models.Model):
    """Admin-defined template for dynamic fields"""
    name = models.CharField(max_length=100, verbose_name='Nombre interno')
    label = models.CharField(max_length=100, verbose_name='Etiqueta')
    field_type = models.CharField(
        max_length=50, default='text', verbose_name='Tipo de dato',
    ) # text, number, date
    default_value = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Valor por omisión',
    )
    is_required = models.BooleanField(default=False, verbose_name='Obligatorio')

    class Meta:
        verbose_name = 'Campo de perfil'
        verbose_name_plural = 'Campos de perfil'

    def __str__(self):
        return self.label
