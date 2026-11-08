"""La ficha de un buzo para el revisor (`GET /api/plantel/<id>/`).

Como el listado, no define ninguna regla: la fila sale de `plantel.fila`, los
ocho puntos de `estado.armar_estado` y los dictámenes de lo que ya trajo el
prefetch. Lo que agrega es lo que sólo le sirve a quien dictamina: el historial
de cada punto con quién dictaminó (el buzo no lo ve, §15.12), si el punto espera
dictamen y si el que mira puede revertir la aprobación vigente.
"""

from __future__ import annotations

from datetime import date

from . import fitness, plantel
from .estado import armar_estado
from .fitness import REVIEW_STATES, StudyState


def _quien(usuario) -> str:
    return usuario.get_full_name().strip() or usuario.username


def _dictamen(comment) -> dict:
    return {
        'id': comment.pk,
        'estado': comment.status,
        'en_calidad_de': comment.reviewer_role,
        'por': _quien(comment.doctor),
        'fecha': comment.created_at,
        # Un REVERTED y un aprobado no llevan motivo ni detalle: vacíos, no null.
        'motivo': comment.rejection_reason,
        'motivo_texto': (comment.get_rejection_reason_display()
                         if comment.rejection_reason else ''),
        'detalle': comment.content,
    }


def _historial(slot) -> list[dict]:
    if slot.block is None:
        return []
    comentarios = sorted(slot.block.comments.all(),
                         key=lambda c: (c.created_at, c.pk))
    return [_dictamen(c) for c in comentarios]


def _puede_revertir(slot, revisor) -> bool:
    """La aprobación vigente es del que mira. Es la misma condición que exige
    `CommentViewSet.revertir`: sólo el autor, y sólo si es el último dictamen."""
    ultimo = slot.last_dictamen
    return (slot.state is StudyState.APPROVED and ultimo is not None
            and ultimo.status == 'APPROVED' and ultimo.doctor_id == revisor.pk)


def _espera(slot, revisor) -> bool:
    """Si el punto espera el dictamen de quien mira. Para el enfermero auxiliar,
    lo que ya pre-aprobó no espera nada más de él: sólo falta el médico."""
    if slot.state not in REVIEW_STATES:
        return False
    perfil = getattr(revisor, 'profile', None)
    if (slot.state is StudyState.PRE_REVIEWED and perfil is not None
            and perfil.role == 'NURSE'):
        return False
    return True


def armar_ficha(profile, today: date, revisor, request=None) -> dict:
    """La ficha de `profile`, vista por `revisor` (un `User`)."""
    resumen = fitness.diver_summary(profile, today)
    estado = armar_estado(profile, today, request=request)
    slots = {slot.code: slot for slot in resumen.slots}

    estudios = []
    for estudio in estado['estudios']:
        slot = slots[estudio['code']]
        estudios.append({
            **estudio,
            'bloque': None if slot.block is None else slot.block.pk,
            'subido_el': None if slot.block is None else slot.block.created_at,
            'fecha_del_estudio': (None if slot.block is None
                                  else slot.block.study_date),
            'espera_dictamen': _espera(slot, revisor),
            'revertible_id': (slot.last_dictamen.pk
                              if _puede_revertir(slot, revisor) else None),
            'dictamenes': _historial(slot),
        })

    return {
        **plantel.fila(profile, today),
        'correo': profile.user.email,
        'aprobados': resumen.approved,
        'estudios': estudios,
    }
