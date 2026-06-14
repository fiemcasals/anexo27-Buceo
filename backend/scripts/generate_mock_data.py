import os
import django
import sys

# Setup django environment
sys.path.append('/home/mauri/anexo-buceo/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import StudyBlock, Permission
from users.models import UserProfile
from django.utils import timezone
from datetime import date

def create_mock_data():
    # 1. Create a "Patient" user
    patient_user, _ = User.objects.get_or_create(username='soldado_perez', email='perez@ejercito.mil.ar')
    patient_user.set_password('password123')
    patient_user.first_name = 'Juan'
    patient_user.last_name = 'Perez'
    patient_user.save()
    
    patient_profile, _ = UserProfile.objects.get_or_create(user=patient_user)
    patient_profile.dni = '12.345.678'
    patient_profile.rank = 'Cabo'
    patient_profile.save()

    # 2. Get current devuser (Auditor)
    auditor_user = User.objects.get(username='devuser')

    # 3. Create some studies for Perez
    s1, _ = StudyBlock.objects.get_or_create(
        user=patient_user,
        title='Audiometria 2024',
        study_date=date(2024, 1, 15),
        description='Estudio anual de audicion'
    )
    
    s2, _ = StudyBlock.objects.get_or_create(
        user=patient_user,
        title='Electrocardiograma',
        study_date=date(2024, 2, 20),
        description='Control cardiovascular'
    )

    # 4. Share Perez's data with devuser
    # Share both Personal Data and all studies
    Permission.objects.get_or_create(
        grantor=patient_user,
        grantee=auditor_user,
        access_level='MODIFY',
        shared_items=['ALL', 'PERSONAL_DATA']
    )

    print(f"Mock data created successfully!")
    print(f"User 'soldado_perez' shared his data with 'devuser'.")

if __name__ == "__main__":
    create_mock_data()
