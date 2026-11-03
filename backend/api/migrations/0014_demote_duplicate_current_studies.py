"""Deja una sola carga vigente por (buzo, punto), antes de exigirlo.

`0009` agrega el índice único parcial `one_current_study_per_diver_and_point`.
`0008` había puesto `is_current=True` en TODA fila preexistente de `StudyBlock`,
así que cualquier buzo que hubiera subido dos veces el mismo punto viola el
índice en el momento de crearlo: tanto SQLite como Postgres validan las filas
que ya están, el `migrate` falla y el despliegue queda a mitad de camino.

**Posición en el grafo.** No corre al final: `run_before` la mete entre `0008`
(que crea `is_current` y `study_code`) y `0009` (que agrega el índice), que es
donde tiene que estar. El número de archivo es el siguiente libre, como pide la
convención de `makemigrations`; el orden real lo fijan las dependencias.

**Base que ya pasó de `0009`.** Meter una migración antes de una ya aplicada
deja el historial "inconsistente" para Django, que entonces se niega a correr
`migrate` y `makemigrations`. Le pasa a cualquier base que haya aplicado `0009`
sin esta — en la práctica, sólo a las de desarrollo, porque `0008`..`0013` son
de esta misma rama y no llegaron a ningún servidor. La reconciliación es de una
sola vez y es exacta, porque sobre esa base estas dos migraciones no tendrían
nada que hacer (el índice ya está puesto, así que no hay duplicados):

.. code-block:: python

    # manage.py shell  (`migrate --fake` no sirve: lo ataja el mismo chequeo)
    from django.db import connection
    from django.db.migrations.recorder import MigrationRecorder
    r = MigrationRecorder(connection)
    r.record_applied('api', '0014_demote_duplicate_current_studies')
    r.record_applied('api', '0015_backfill_rejection_reason_and_detail')

**Lo que NO arregla.** `0008` etiquetó todo estudio preexistente como punto "g"
(odontológico), porque antes la subida era de texto libre. No hay manera de
saber qué estudio era cada una, y adivinar sería inventar datos médicos: eso
necesita triage humano. Esta migración hace que el `migrate` no falle, no que
los datos queden correctos. Como efecto de ese etiquetado, acá "dos cargas del
mismo punto" va a ser casi siempre "dos cargas cualesquiera del mismo buzo".
"""

from django.db import migrations, models


def demote_duplicate_current_studies(apps, schema_editor):
    """Degrada toda carga vigente repetida de un punto, menos la más nueva.

    Criterio: queda vigente la de `study_date` más reciente, desempatando por
    `pk` más alto (la última cargada). Es exactamente lo que el índice exige, y
    coincide con lo que hace `StudyBlock.save()` de ahora en adelante.

    Idempotente: a la segunda corrida ya no hay ningún grupo con más de una.
    """
    StudyBlock = apps.get_model('api', 'StudyBlock')
    duplicated = (
        StudyBlock.objects.filter(is_current=True)
        .values('user_id', 'study_code')
        .annotate(n=models.Count('pk'))
        .filter(n__gt=1)
    )
    for group in duplicated:
        rows = list(
            StudyBlock.objects
            .filter(is_current=True, user_id=group['user_id'],
                    study_code=group['study_code'])
            .order_by('-study_date', '-pk')
            .values_list('pk', flat=True)
        )
        StudyBlock.objects.filter(pk__in=rows[1:]).update(is_current=False)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_studyblock_is_current_studyblock_study_code'),
    ]

    run_before = [
        ('api', '0009_studyblock_one_current_study_per_diver_and_point'),
    ]

    operations = [
        # El reverso no hace nada a propósito: no queda registro de cuáles
        # filas se degradaron, y volver a marcarlas vigentes rompería el mismo
        # índice que esta migración existe para no romper. Revertir no falla.
        migrations.RunPython(demote_duplicate_current_studies,
                             migrations.RunPython.noop),
    ]
