from django.contrib.auth.models import User
from users.models import UserProfile
from api.models import StudyBlock, Comment, Permission, DiveActivity, DiveLog
import datetime

def create_user(username, email, password, role='BUZO', is_superuser=False, is_instructor=False, first_name='', last_name=''):
    user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'first_name': first_name, 'last_name': last_name})
    if created:
        user.set_password(password)
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        user.save()
        print(f"✅ Usuario creado: {email} (Pass: {password})")
    else:
        print(f"⚠️ Usuario ya existe: {email}")

    # Asegurar que tenga perfil
    profile, p_created = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.is_instructor = is_instructor
    profile.save()
    return user

print("\n🚀 INICIANDO CREACIÓN DE DATOS DE PRUEBA 🚀\n")

# 1. Crear Usuarios
admin = create_user('admin', 'admin@buceo.com', '12345', role='ADMIN', is_superuser=True, first_name='Admin', last_name='Sistema')
instructor = create_user('instructor', 'instructor@buceo.com', '12345', is_instructor=True, first_name='Carlos', last_name='Instructor')
medico = create_user('medico', 'medico@buceo.com', '12345', first_name='Dra. Elena', last_name='Medica')
buzo1 = create_user('buzo1', 'buzo1@buceo.com', '12345', first_name='Juan', last_name='Perez')
buzo2 = create_user('buzo2', 'buzo2@buceo.com', '12345', first_name='Maria', last_name='Gomez')

# 2. Rellenar datos de perfil básicos
for p_user in [instructor, medico, buzo1, buzo2]:
    prof = p_user.profile
    prof.dni = f"123456{p_user.id}"
    prof.age = 30 + p_user.id
    prof.phone = f"+54 9 11 1234 {p_user.id}000"
    prof.rank = 'Sargento' if p_user == buzo1 else 'Cabo'
    prof.destination = 'Base Naval'
    prof.weight = 75.5
    prof.height = 175
    prof.save()

# 3. Crear Estudios Médicos para Buzo 1
print("\n📁 Creando Estudios Médicos...")
study1, created = StudyBlock.objects.get_or_create(
    user=buzo1, title="Audiometría Anual",
    defaults={
        'description': 'Estudio de audición de rutina',
        'study_date': datetime.date.today(),
        'pdf_attachment': ''
    }
)

study2, created = StudyBlock.objects.get_or_create(
    user=buzo1, title="Electrocardiograma",
    defaults={
        'description': 'Apto físico cardiológico',
        'study_date': datetime.date.today(),
        'pdf_attachment': ''
    }
)

# 4. Otorgar Permisos al Médico
print("🔐 Otorgando permisos médicos...")
Permission.objects.get_or_create(
    grantor=buzo1, grantee=medico,
    defaults={
        'access_level': 'MODIFY',
        'shared_items': ['ALL']
    }
)

# 5. Médico dictamina sobre el estudio
print("✍️ Creando dictamen médico...")
Comment.objects.get_or_create(
    block=study1, doctor=medico,
    defaults={
        'content': 'El paciente se encuentra en óptimas condiciones auditivas para realizar inmersiones.',
        'status': 'APPROVED'
    }
)

# 6. Crear una Actividad de Buceo (Instructor)
print("🌊 Creando Actividad de Buceo...")
act, created = DiveActivity.objects.get_or_create(
    instructor=instructor, date=datetime.date.today(),
    defaults={
        'location_coords': '38° 00 S 57° 33 W',
        'location_type': 'Mar Abierto',
        'dive_type': 'Entrenamiento',
        'max_depth_meters': 18.5,
        'duration_minutes': 45,
        'safety_diver': buzo2.id,
        'medic': medico.id,
        'supervisor': admin.id
    }
)

# 7. Asignar Buceo al Buzo 1 en la Bitácora
print("📖 Registrando Bitácora de Buzo 1...")
DiveLog.objects.get_or_create(
    activity=act, diver=buzo1,
    defaults={
        'is_completed': True,
        'equipment_type': 'Circuito Abierto',
        'gas_type': 'Aire',
        'suit_type': 'Húmedo 7mm',
        'weight_kgs': 8.5,
        'start_pressure_bar': 200,
        'end_pressure_bar': 50
    }
)

print("\n✨ ¡DATOS DE PRUEBA GENERADOS CON ÉXITO! ✨")
print("Puedes iniciar sesión con cualquiera de los siguientes usuarios (Contraseña para todos: 12345):")
print("- admin@buceo.com (Superusuario)")
print("- instructor@buceo.com (Instructor)")
print("- medico@buceo.com (Médico Auditor)")
print("- buzo1@buceo.com (Buzo de prueba 1)")
print("- buzo2@buceo.com (Buzo de prueba 2)\n")
