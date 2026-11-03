from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('USER', 'User'),
        ('NURSE', 'Enfermero auxiliar'),
        ('DOCTOR', 'Doctor'),
        ('ADMIN', 'Admin'),
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    is_instructor = models.BooleanField(default=False)
    profile_data = models.JSONField(default=dict, blank=True)
    
    # Base fields requested by user
    dni = models.CharField(max_length=20, unique=True, null=True, blank=True)
    # Nullable a proposito: sin fecha de nacimiento no se puede derivar la edad.
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    rank = models.CharField(max_length=2, choices=RANK_CHOICES, blank=True) # Grado
    destination = models.CharField(max_length=100, blank=True) # Destino
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)

    def age_in_year(self, year):
        """Edad que se alcanza en `year`: resta de años, no edad cumplida."""
        if self.birth_date is None:
            return None
        return year - self.birth_date.year

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
