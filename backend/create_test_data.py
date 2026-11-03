"""Datos de prueba del dominio de aptitud medica.

Ejecutar desde backend/ (NO con `manage.py shell < archivo`: la consola
interactiva pierde las variables entre bloques separados por lineas en blanco):

    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 ./venv/Scripts/python.exe manage.py shell \
        -c "exec(open('create_test_data.py', encoding='utf-8').read())"

Es re-ejecutable: BORRA y vuelve a crear los usuarios sembrados (se reconocen
por su username; el borrado arrastra perfiles, estudios y dictamenes) y hace
upsert de la fecha de habilitacion. Nada que no sea de esta lista se toca.

El ciclo 2026 queda INCOMPLETO a proposito: solo la 1.a fecha esta confirmada
(18 al 20 de noviembre). La 2.a y la complementaria no existen todavia.

Cada buzo ejercita un estado distinto del motor (api/fitness.py). Los estados
se derivan al final y se imprimen, para verificar que son los buscados.
"""
import datetime

from django.contrib.auth.models import User

from api import catalog, fitness
from api.models import Comment, HabilitationWindow, StudyBlock
from users.models import UserProfile

PASSWORD = '12345'
CYCLE = 2026
TODAY = datetime.date.today()

# Estudios recientes: vigentes todo el rango 18-20/11/2026 (los de 365 dias deben
# ser posteriores al 20/11/2025; el Anexo 27 debe ser del 21/10/2026 en adelante).
RECENT = datetime.date(2026, 9, 15)
RECENT_ANEXO27 = datetime.date(2026, 10, 28)
# Vencido para esa fecha: 01/10/2025 + 365 dias = 01/10/2026 < 20/11/2026.
STALE = datetime.date(2025, 10, 1)

# username -> (nombre, apellido, rol, grado, nacimiento, DNI, destino)
PEOPLE = {
    'admin':   ('Admin', 'Sistema', 'ADMIN', '', None, '10000001', ''),
    'medico':  ('Elena', 'Molina', 'DOCTOR', 'CT', datetime.date(1985, 3, 12), '10000002', 'Sanidad'),
    'vera':    ('Marcos', 'Vera', 'NURSE', 'SG', datetime.date(1990, 7, 4), '10000003', 'Sanidad'),
    # Menores de 40 en 2026: siete estudios.
    'apto':        ('Juan', 'Perez', 'USER', 'CB', datetime.date(1996, 5, 20), '20000001', 'Base Naval'),
    'faltantes':   ('Lucia', 'Gomez', 'USER', 'CI', datetime.date(1999, 2, 2), '20000002', 'Base Naval'),
    'vencido':     ('Diego', 'Suarez', 'USER', 'SG', datetime.date(1994, 9, 9), '20000003', 'Base Naval'),
    'rechazo':     ('Sofia', 'Rios', 'USER', 'TT', datetime.date(1997, 1, 15), '20000004', 'Base Naval'),
    'preaprobado': ('Tomas', 'Luna', 'USER', 'CB', datetime.date(1998, 11, 30), '20000005', 'Base Naval'),
    # 40 o mas en 2026: ocho estudios. Borde: 'cumple40' nace el 30/12/1986 y
    # cumple 40 DESPUES de la habilitacion, pero la edad es resta de anios.
    'cumple40':    ('Raul', 'Acosta', 'USER', 'MY', datetime.date(1986, 12, 30), '30000001', 'Base Naval'),
    'mayor':       ('Carlos', 'Ortiz', 'USER', 'SM', datetime.date(1978, 4, 1), '30000002', 'Base Naval'),
    # Sin ventana elegida / sin fecha de nacimiento.
    'sinfecha':    ('Ana', 'Duarte', 'USER', 'CB', datetime.date(1995, 6, 6), '40000001', 'Base Naval'),
    'sinnacim':    ('Pedro', 'Sosa', 'USER', 'CI', None, '40000002', 'Base Naval'),
}

# --- Limpieza: re-ejecutable ------------------------------------------------
User.objects.filter(username__in=PEOPLE).delete()

# --- Fecha de habilitacion: solo la 1.a del ciclo 2026 -----------------------
first_window, _ = HabilitationWindow.objects.update_or_create(
    cycle=CYCLE, slot=HabilitationWindow.FIRST,
    defaults={'start_date': datetime.date(2026, 11, 18),
              'end_date': datetime.date(2026, 11, 20)},
)

# --- Usuarios ----------------------------------------------------------------
users = {}
for username, (first, last, role, rank, birth, dni, destination) in PEOPLE.items():
    user = User.objects.create_user(
        username=username, email=f'{username}@buceo.com', password=PASSWORD,
        first_name=first, last_name=last,
        is_superuser=(role == 'ADMIN'), is_staff=(role == 'ADMIN'),
    )
    UserProfile.objects.update_or_create(user=user, defaults={
        'role': role, 'rank': rank, 'birth_date': birth, 'dni': dni,
        'destination': destination, 'phone': f'+54 9 11 5555 {dni[-4:]}',
        # Medico, enfermero y admin no presentan estudios: no eligen fecha.
        'habilitation_window': (None if role != 'USER' or username == 'sinfecha'
                                else first_window),
    })
    users[username] = user

doctor, nurse = users['medico'], users['vera']


def upload(diver, code, study_date=RECENT):
    """El buzo carga un estudio (queda como vigente)."""
    if code == 'h' and study_date == RECENT:
        study_date = RECENT_ANEXO27
    return StudyBlock.objects.create(
        user=users[diver], study_code=code, study_date=study_date,
        pdf_attachment='',
    )


def approve(block):
    return Comment.objects.create(block=block, doctor=doctor, reviewer_role='DOCTOR',
                                  status='APPROVED')


def pre_approve(block):
    return Comment.objects.create(block=block, doctor=nurse, reviewer_role='NURSE',
                                  status='PRE_APPROVED')


def reject(block, reviewer, role, reason, detail):
    return Comment.objects.create(block=block, doctor=reviewer, reviewer_role=role,
                                  status='REJECTED', rejection_reason=reason,
                                  content=detail)


def fully_approved(diver, codes):
    for code in codes:
        approve(upload(diver, code))


UNDER_40 = [c.code for c in catalog.required_for_age(30)]   # b..h
OVER_40 = [c.code for c in catalog.required_for_age(40)]    # a..h

# Apto: siete estudios, todos aprobados por el medico.
fully_approved('apto', UNDER_40)
# Apto con ocho (el borde de los 40).
fully_approved('cumple40', OVER_40)
# Faltantes: solo tres de siete presentados -> incompleto.
fully_approved('faltantes', ['b', 'c', 'd'])
# Vencido: el punto c es de octubre de 2025 y no cubre el rango, aun aprobado.
fully_approved('vencido', [c for c in UNDER_40 if c != 'c'])
approve(upload('vencido', 'c', STALE))
# Rechazo: d rechazado por el medico; e pre-aprobado por el enfermero y luego
# rechazado por el medico (la historia no se pisa: vale el ultimo dictamen).
fully_approved('rechazo', [c for c in UNDER_40 if c not in ('d', 'e')])
reject(upload('rechazo', 'd'), doctor, 'DOCTOR', 'ILLEGIBLE',
       'Falta la placa de perfil; el archivo es ilegible.')
block_e = upload('rechazo', 'e')
pre_approve(block_e)
reject(block_e, doctor, 'DOCTOR', 'UNFIT_VALUES',
       'Hallazgo en senos paranasales que requiere evaluacion.')
# Pre-aprobado: f espera la aprobacion del medico (no cuenta como apto).
fully_approved('preaprobado', [c for c in UNDER_40 if c != 'f'])
pre_approve(upload('preaprobado', 'f'))
# Mayor de 40 que no presento el electrocardiograma de esfuerzo (punto a).
fully_approved('mayor', [c for c in OVER_40 if c != 'a'])
# Sin ventana elegida y sin fecha de nacimiento: con algo cargado cada uno.
fully_approved('sinfecha', ['b', 'c'])
fully_approved('sinnacim', ['b', 'c'])

# --- Verificacion con el motor -----------------------------------------------
print('\nFecha de habilitacion sembrada:', first_window)
print('Contrasena de todos los usuarios:', PASSWORD, '\n')
print(f"{'usuario':<12} {'rol':<7} {'edad':<5} {'exige':<6} {'estado':<12} "
      f"{'pres':<5} {'apr':<4} {'rev':<4} {'pre':<4} prob")
for username, person in PEOPLE.items():
    if person[2] != 'USER':
        continue  # solo los buzos tienen estado de aptitud
    profile = UserProfile.objects.select_related(
        'user', 'habilitation_window').get(user__username=username)
    summary = fitness.diver_summary(profile, TODAY)
    age = (None if profile.habilitation_window is None
           else profile.age_in_year(fitness.habilitation_year(profile.habilitation_window)))
    print(f"{username:<12} {profile.role:<7} {str(age):<5} "
          f"{len(summary.required_codes):<6} {summary.state.value:<12} "
          f"{summary.presented:<5} {summary.approved:<4} {summary.pending_review:<4} "
          f"{summary.pre_reviewed:<4} {summary.problems}")
