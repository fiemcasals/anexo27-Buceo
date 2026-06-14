from django.db import models
from django.contrib.auth.models import User
import uuid
from django.contrib.auth.models import User

class StudyBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_blocks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    study_date = models.DateField()
    pdf_attachment = models.FileField(upload_to='studies/%Y/%m/%d/')

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
