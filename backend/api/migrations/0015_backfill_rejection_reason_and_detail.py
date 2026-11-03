"""Da motivo y detalle a todo rechazo preexistente, antes de exigirlo.

`0013` agrega la CHECK `rejection_has_reason_and_detail`, que pide que toda fila
con `status='REJECTED'` lleve `rejection_reason` y `content` no vacíos.
`rejection_reason` recién aparece en `0010`, con `blank=True` y sin paso de
datos, así que todo rechazo anterior lo tiene en `''` y viola la CHECK en el
momento de crearla: tanto SQLite como Postgres validan las filas que ya están,
el `migrate` falla y el despliegue queda a mitad de camino.

**Posición en el grafo.** No corre al final: `run_before` la mete entre `0010`
(que crea el campo que rellena) y `0013` (que agrega la CHECK), que es donde
tiene que estar. El número de archivo es el siguiente libre, como pide la
convención de `makemigrations`; el orden real lo fijan las dependencias. Sobre
una base que ya pasó de `0013` hace falta la reconciliación de una sola vez que
documenta `0014`, que vale para las dos.

**La otra CHECK de `0013` no necesita relleno.** `verdict_matches_reviewer_role`
exige `REJECTED`, o `PRE_APPROVED` de enfermero, o `APPROVED` de médico. Antes
de `0010` los únicos estados que existían eran `APPROVED` y `REJECTED` (ver
`0002`), y `0010` agregó `reviewer_role` con `default='DOCTOR'`: toda fila
preexistente queda en `APPROVED`+`DOCTOR` o en `REJECTED`, y las dos satisfacen
la CHECK. Por eso acá sólo se rellenan motivo y detalle.
"""

from django.db import migrations

#: Detalle para el rechazo que llegó sin ninguno. Registro impersonal, como
#: todo texto que ve el buzo: no se dirige al lector y no inventa un motivo que
#: nadie escribió.
MISSING_DETAIL = (
    'El motivo de este rechazo no quedó registrado en el sistema anterior. '
    'Se solicita consultar en el servicio de sanidad antes de volver a '
    'presentar el estudio.'
)


def backfill_rejection_reason_and_detail(apps, schema_editor):
    """Rellena los dos campos que la CHECK exige, sólo donde faltan.

    Las dos reglas son deterministas, no adivinanzas: 'OTHER' es justamente el
    motivo "Otros" del catálogo de la directiva, que es lo que un rechazo sin
    motivo registrado es; y el detalle dice que el motivo no quedó registrado,
    en lugar de inventar uno.

    Idempotente: a la segunda corrida ya no queda ninguna fila en `''`.
    """
    Comment = apps.get_model('api', 'Comment')
    Comment.objects.filter(status='REJECTED', rejection_reason='').update(
        rejection_reason='OTHER')
    Comment.objects.filter(status='REJECTED', content='').update(
        content=MISSING_DETAIL)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_comment_rejection_reason_comment_reviewer_role_and_more'),
    ]

    run_before = [
        ('api', '0013_comment_verdict_matches_reviewer_role_and_more'),
    ]

    operations = [
        # El reverso no hace nada a propósito: no queda registro de qué filas se
        # rellenaron, y vaciarlas de nuevo rompería la misma CHECK que esta
        # migración existe para no romper. Revertir no falla.
        migrations.RunPython(backfill_rejection_reason_and_detail,
                             migrations.RunPython.noop),
    ]
