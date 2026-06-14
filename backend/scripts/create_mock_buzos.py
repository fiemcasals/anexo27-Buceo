import os
import django
import sys

sys.path.append('/app')  # for docker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

print("Generando buzos...")

for i in range(1, 6):
    email = f'buzo{i}@ejercito.mil.ar'
    username = f'buzo{i}'
    
    if not User.objects.filter(email=email).exists():
        user = User.objects.create_user(username=username, email=email, password='securePW75#')
        user.first_name = f'Buzo {i}'
        user.save()
        
        # El profile ya puede haberse creado por signals (dependiendo de tu conf), 
        # pero si no, lo forzamos:
        UserProfile.objects.get_or_create(user=user)
        print(f'✅ Creado: {email} (Nombre: Buzo {i})')
    else:
        print(f'⚠️ Ya existe: {email}')

print("¡Listo!")
