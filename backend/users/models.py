from django.db import models
from django.contrib.auth.models import User

class Specialty(models.Model):
    """Especialidad medica/enfermeria, administrada por el admin"""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Specialties'

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('USER', 'User'),
        ('DOCTOR', 'Doctor'),
        ('ADMIN', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    is_instructor = models.BooleanField(default=False)
    PROFESSION_CHOICES = [
        ('MEDICO', 'Médico'),
        ('ENFERMERO', 'Enfermero'),
    ]
    profession = models.CharField(max_length=20, choices=PROFESSION_CHOICES, blank=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')
    profile_data = models.JSONField(default=dict, blank=True)
    
    # Base fields requested by user
    dni = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    rank = models.CharField(max_length=50, blank=True) # Grado
    destination = models.CharField(max_length=100, blank=True) # Destino
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)

    # Fecha en que acepto las condiciones de uso; vacio = todavia no las acepto
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class ProfileFieldTemplate(models.Model):
    """Admin-defined template for dynamic fields"""
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=50, default='text') # text, number, date
    default_value = models.CharField(max_length=255, blank=True, null=True)
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return self.label
