"""El plantel para el listado del médico: una fila por buzo.

No define ninguna regla. Cada conteo, vigencia, estado y último dictamen sale de
``fitness.diver_summary``; acá sólo se elige qué se muestra y cómo se nombra. Una
segunda definición de la regla (un ``annotate``, una consulta "para optimizar")
se desincronizaría de la que ve el buzo.

Tampoco consulta la base: lee el perfil ya traído, con la receta de ``select_related``
y ``prefetch_related`` que documenta ``fitness``.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from . import fitness
from .fitness import REVIEW_STATES

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from users.models import UserProfile

#: Los dos estados sin dictamen del médico que dejan la subida en la pila cruda.
_SIN_DICTAMEN_DEL_MEDICO = REVIEW_STATES


def fila(profile: UserProfile, today: date) -> dict:
    """La fila del listado para un buzo. No hace consultas.

    ``presentados`` cuenta los slots que tienen bloque; cuando los exigidos se
    conocen se restringe a ellos, que es lo que hace ``DiverSummary.presented``,
    y cuando no se conocen se cuentan todos. Es una sola cuenta sobre dos
    conjuntos, no dos caminos de conteo.
    """
    resumen = fitness.diver_summary(profile, today)
    window = profile.habilitation_window

    # Sin turno o sin fecha de nacimiento el exigido no se puede determinar, y eso
    # no es lo mismo que cero: un buzo que subió ocho estudios sin inscribirse
    # leería "0/0", o sea que no presentó nada.
    determinado = window is not None and profile.birth_date is not None

    return {
        'id': profile.pk,
        'grado': profile.rank,
        'apellido': profile.user.last_name,
        'nombre': profile.user.first_name,
        'unidad': profile.destination,
        'dni': profile.dni,
        # La edad de la regla (año del turno menos año de nacimiento), no la de
        # hoy: es la que decide si corresponden siete estudios u ocho.
        'edad': (profile.age_in_year(fitness.habilitation_year(window))
                 if determinado else None),
        'turno': None if window is None else {
            'id': window.pk,
            'slot': window.slot,
            'slot_display': window.get_slot_display(),
            'start_date': window.start_date,
            'end_date': window.end_date,
        },
        'presentados': (resumen.presented if determinado
                        else _subidos(resumen)),
        'exigidos': len(resumen.required_codes) if determinado else None,
        'a_revisar': resumen.pending_review + resumen.pre_reviewed,
        'sin_tocar': resumen.pending_review,
        'pre_revisados': resumen.pre_reviewed,
        'vencidos': resumen.expired,
        'rechazados': resumen.rejected,
        'ultima_revision': resumen.last_doctor_review,
        'estado': resumen.state.name,
        'subida_mas_vieja_sin_dictamen': _subida_mas_vieja(resumen),
    }


def _subidos(resumen: fitness.DiverSummary) -> int:
    """Cuántos puntos tienen carga vigente cuando no hay exigidos contra los
    cuales contar.

    ``DiverSummary.presented`` cuenta sólo los exigidos, y sin turno o sin edad no
    hay ninguno: daría cero para un buzo que subió ocho. Los ``slots`` conservan
    la carga de los ocho, así que se cuenta de ahí, sin definir ninguna regla.
    """
    return sum(1 for slot in resumen.slots if slot.block is not None)


def _subida_mas_vieja(resumen: fitness.DiverSummary):
    """Cuándo se cargó lo más viejo que espera al médico; None si no hay nada.

    Sólo mira lo que no tiene dictamen del médico (en revisión o pre-revisado):
    un estudio viejo ya dictaminado no puede encabezar la pila cruda.
    """
    subidas = [
        slot.block.created_at for slot in resumen.slots
        if slot.state in _SIN_DICTAMEN_DEL_MEDICO and slot.block is not None
    ]
    return min(subidas) if subidas else None
