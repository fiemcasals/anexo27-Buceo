import re

from django.db import migrations

_SEPARADORES = re.compile(r'[.,\s]')


def limpiar_dnis(apps, schema_editor):
    """Saca puntos, comas y espacios de los DNI ya guardados. Si el DNI limpio
    ya lo tiene otro perfil, el repetido se deja como está: pisarlo chocaría con
    el índice único, y decidir cuál es el bueno es de una persona."""
    UserProfile = apps.get_model('users', 'UserProfile')
    for perfil in UserProfile.objects.exclude(dni__isnull=True).exclude(dni=''):
        limpio = _SEPARADORES.sub('', perfil.dni)
        if limpio == perfil.dni:
            continue
        if limpio and not UserProfile.objects.filter(dni=limpio).exclude(pk=perfil.pk).exists():
            UserProfile.objects.filter(pk=perfil.pk).update(dni=limpio)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_otro_curso_hasta_70'),
    ]

    operations = [
        migrations.RunPython(limpiar_dnis, migrations.RunPython.noop),
    ]
