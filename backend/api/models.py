from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models
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

    def save(self, *args, **kwargs):
        if self.study_code in catalog.CODES:
            self.title = catalog.get(self.study_code).text
        if self._state.adding and self.is_current:
            StudyBlock.objects.filter(
                user=self.user, study_code=self.study_code, is_current=True
            ).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Comment(models.Model):
    STATUS_CHOICES = [
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado con Observación'),
    ]
    block = models.ForeignKey(StudyBlock, on_delete=models.CASCADE, related_name='comments')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPROVED')
    created_at = models.DateTimeField(auto_now_add=True)
    verified_signature = models.BooleanField(default=True)

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
