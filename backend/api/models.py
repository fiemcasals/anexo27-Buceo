from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.auth.models import User
import uuid
from django.contrib.auth.models import User
from . import catalog

class StudyBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_blocks')
    study_code = models.CharField(max_length=1, choices=[(c, c) for c in catalog.CODES])
    is_current = models.BooleanField(default=True)
    # Filled from the catalog in save(); never typed by the diver.
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    study_date = models.DateField()
    pdf_attachment = models.FileField(upload_to='studies/%Y/%m/%d/')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study_code'],
                condition=models.Q(is_current=True),
                name='one_current_study_per_diver_and_point',
            ),
        ]

    def save(self, *args, **kwargs):
        # Un código fuera del catálogo no es un dato del usuario — el
        # serializador valida las choices — sino un error de programación de la
        # consola o de la siembra. Antes guardaba un title vacío en silencio.
        if self.study_code not in catalog.CODES:
            raise ValueError(
                f'study_code {self.study_code!r} no es uno de los ocho puntos '
                f'de la directiva: {"".join(catalog.CODES)}.'
            )
        self.title = catalog.get(self.study_code).text
        with transaction.atomic():
            if self._state.adding and self.is_current:
                StudyBlock.objects.filter(
                    user=self.user, study_code=self.study_code, is_current=True
                ).update(is_current=False)
            super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Comment(models.Model):
    STATUS_CHOICES = [
        ('PRE_APPROVED', 'Pre-revisado'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado con Observación'),
    ]
    REJECTION_REASONS = [
        ('OUT_OF_TERM', 'Estudio fuera del plazo de la directiva'),
        ('UNFIT_VALUES', 'Valores no aptos para realizar la actividad'),
        ('ILLEGIBLE', 'Documento ilegible'),
        ('OTHER', 'Otros'),
    ]
    REVIEWER_ROLES = [
        ('DOCTOR', 'Médico'),
        ('NURSE', 'Enfermero auxiliar'),
    ]
    block = models.ForeignKey(StudyBlock, on_delete=models.CASCADE, related_name='comments')
    # Nombre histórico: también lo usa un enfermero; reviewer_role dice quién dictaminó.
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    reviewer_role = models.CharField(max_length=10, choices=REVIEWER_ROLES)
    # Obligatorio sólo en los rechazos (ver clean()).
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    rejection_reason = models.CharField(max_length=20, choices=REJECTION_REASONS, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_signature = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Sólo el médico declara apto; el enfermero pre-aprueba; ambos pueden rechazar.
            models.CheckConstraint(
                condition=(
                    models.Q(status='REJECTED')
                    | models.Q(status='PRE_APPROVED', reviewer_role='NURSE')
                    | models.Q(status='APPROVED', reviewer_role='DOCTOR')
                ),
                name='verdict_matches_reviewer_role',
                violation_error_message=(
                    'La aprobación corresponde sólo al médico y la '
                    'pre-aprobación sólo al enfermero auxiliar.'
                ),
            ),
            # Todo rechazo lleva motivo y detalle; nada más lleva motivo.
            models.CheckConstraint(
                condition=(
                    (models.Q(status='REJECTED')
                     & ~models.Q(rejection_reason='') & ~models.Q(content=''))
                    | (~models.Q(status='REJECTED') & models.Q(rejection_reason=''))
                ),
                name='rejection_has_reason_and_detail',
                violation_error_message=(
                    'Todo rechazo requiere motivo y detalle, y sólo un '
                    'rechazo lleva motivo.'
                ),
            ),
        ]

    def clean(self):
        errors = {}
        # Spec §15.9: nadie dictamina sobre sus propios estudios. La unidad tiene
        # un solo médico y puede ser además buzo; sin esto se declara apto solo.
        # Va acá y no en una CheckConstraint porque comparar el revisor contra el
        # dueño del estudio exige un join, que SQLite no admite dentro de un
        # CHECK. El spec pide la validación, no la interfaz, y esta es la capa.
        if self.block_id and self.doctor_id == self.block.user_id:
            errors['doctor'] = 'Nadie puede dictaminar sobre sus propios estudios.'
        if self.status == 'APPROVED' and self.reviewer_role == 'NURSE':
            errors['status'] = 'La aprobación corresponde sólo al médico.'
        elif self.status == 'PRE_APPROVED' and self.reviewer_role == 'DOCTOR':
            errors['status'] = 'La pre-aprobación corresponde sólo al enfermero auxiliar.'
        if self.status == 'REJECTED':
            if not self.rejection_reason:
                errors['rejection_reason'] = 'Todo rechazo requiere un motivo.'
            if not self.content.strip():
                errors['content'] = 'Todo rechazo requiere un detalle para el buzo.'
        elif self.rejection_reason:
            errors['rejection_reason'] = 'Sólo un rechazo lleva motivo.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Comment by {self.doctor.username} on {self.block.title}"

class Permission(models.Model):
    ACCESS_CHOICES = [
        ('VIEW', 'View'),
        ('MODIFY', 'Modify'),
    ]
    grantor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions_given')
    grantee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions_received')
    access_level = models.CharField(max_length=10, choices=ACCESS_CHOICES)
    shared_items = models.JSONField(default=list) # List of StudyBlock IDs or ["ALL"]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.grantor.username} -> {self.grantee.username} ({self.access_level})"

class DiveActivity(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities_created')
    
    date = models.DateField()
    location_coords = models.CharField(max_length=255, blank=True)
    location_type = models.CharField(max_length=255, blank=True)
    dive_type = models.CharField(max_length=255, blank=True)
    
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    
    max_depth_meters = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    surface_temp_celsius = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    water_temp_celsius = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    visibility_meters = models.IntegerField(null=True, blank=True)
    altitude_meters = models.IntegerField(null=True, blank=True)
    
    atmospheric_conditions = models.CharField(max_length=255, blank=True)
    water_course_conditions = models.CharField(max_length=255, blank=True)
    wind_speed_knots = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Signatures
    safety_diver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities_as_safety')
    medic = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities_as_medic')
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities_as_supervisor')
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - Actividad Instructor {self.instructor.username}"

class DiveLog(models.Model):
    activity = models.ForeignKey(DiveActivity, on_delete=models.CASCADE, related_name='logs')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    diver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dive_logs')
    is_completed = models.BooleanField(default=False)
    
    dive_graph = models.FileField(upload_to='dive_graphs/', blank=True, null=True)
    residual_nitrogen_post = models.CharField(max_length=50, blank=True)
    residual_nitrogen_pre = models.CharField(max_length=50, blank=True)
    
    decompression_stop = models.BooleanField(default=False)
    decompression_depth_meters = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    decompression_time_minutes = models.IntegerField(null=True, blank=True)
    
    equipment_type = models.CharField(max_length=255, blank=True)
    gas_type = models.CharField(max_length=50, default='Aire')
    suit_type = models.CharField(max_length=255, blank=True)
    weight_kgs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tank_type = models.CharField(max_length=255, blank=True)
    
    start_pressure_bar = models.IntegerField(null=True, blank=True)
    end_pressure_bar = models.IntegerField(null=True, blank=True)
    
    diver_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Log - {'Completed' if self.is_completed else 'Pending'}"


class HabilitationWindow(models.Model):
    """Fecha de habilitación: un rango de días dentro de un ciclo anual.

    Cada ciclo tiene hasta tres (1.ª, 2.ª y complementaria), que se cargan de a
    una: un ciclo incompleto es el estado normal. Toda vigencia se mide contra
    este rango, y el estudio debe estar vigente todos los días, o sea hasta
    `end_date`.
    """
    FIRST = 'FIRST'
    SECOND = 'SECOND'
    COMPLEMENTARY = 'COMPLEMENTARY'
    SLOT_CHOICES = [
        (FIRST, '1.ª fecha'),
        (SECOND, '2.ª fecha'),
        (COMPLEMENTARY, 'Complementaria'),
    ]

    cycle = models.PositiveIntegerField()
    slot = models.CharField(max_length=13, choices=SLOT_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['cycle', 'slot'], name='unique_window_slot_per_cycle',
                violation_error_message='Ya existe una fecha con ese lugar en el ciclo.',
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='window_end_not_before_start',
                violation_error_message='La fecha de fin no puede ser anterior a la de inicio.',
            ),
        ]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError('La fecha de fin no puede ser anterior a la de inicio.')

    @property
    def anexo27_earliest_date(self):
        """Primer día en que el Anexo 27 sigue vigente para todo el rango."""
        return self.end_date - timedelta(days=30)

    def __str__(self):
        label = self.get_slot_display()
        if self.start_date == self.end_date:
            rango = f"{self.start_date:%d/%m/%Y}"
        else:
            rango = f"{self.start_date:%d/%m/%Y} al {self.end_date:%d/%m/%Y}"
        return f"{label} {self.cycle}: {rango}"
