from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('USER', 'User'),
        ('DOCTOR', 'Doctor'),
        ('ADMIN', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    is_instructor = models.BooleanField(default=False)
    profile_data = models.JSONField(default=dict, blank=True)
    
    # Base fields requested by user
    dni = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    rank = models.CharField(max_length=50, blank=True) # Grado
    destination = models.CharField(max_length=100, blank=True) # Destino
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)

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
