from django.db import migrations
from django.utils import timezone


def anotar_a_los_inscriptos(apps, schema_editor):
    """Los buzos que ya tienen una fecha elegida entran al historial con ella.

    No se sabe cuándo la eligieron (hasta hoy no se guardaba): queda la fecha de
    esta migración, que es lo más cercano que se puede decir con verdad."""
    UserProfile = apps.get_model('users', 'UserProfile')
    Enrollment = apps.get_model('api', 'HabilitationEnrollment')
    ahora = timezone.now()
    for perfil in UserProfile.objects.filter(habilitation_window__isnull=False).select_related('habilitation_window'):
        Enrollment.objects.get_or_create(
            user_id=perfil.user_id, cycle=perfil.habilitation_window.cycle,
            defaults={'window_id': perfil.habilitation_window_id, 'chosen_at': ahora})


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_historial_de_habilitaciones'),
        ('users', '0011_dni_sin_puntos'),
    ]

    operations = [
        migrations.RunPython(anotar_a_los_inscriptos, migrations.RunPython.noop),
    ]
