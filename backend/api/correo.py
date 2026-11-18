"""Avisos por correo al buzo: estudio rechazado, observación y apto.

Se invoca desde la vista de dictámenes y no desde una señal ni desde
`Model.save()`: una señal también dispararía desde el admin de Django y desde
`create_test_data.py`, y sembrar la base mandaría correos de verdad.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Comment

logger = logging.getLogger(__name__)


def _texto(comment):
    motivo = dict(Comment.REJECTION_REASONS).get(
        comment.rejection_reason, comment.rejection_reason)
    return (
        f'Se rechazó el estudio "{comment.block.title}".\n'
        f'\n'
        f'Motivo: {motivo}\n'
        f'\n'
        f'Detalle:\n'
        f'{comment.content}\n'
        f'\n'
        f'Para corregirlo, ingresar al sistema y subir nuevamente el estudio: '
        f'{settings.FRONTEND_URL}\n'
    )


def avisar_rechazo(comment) -> bool:
    """Avisa al buzo que se rechazó su estudio. True si el correo salió.

    No dice quién revisó: el buzo necesita saber qué corregir. Nunca propaga:
    un servidor de correo caído no puede impedir que el médico dictamine.
    La espera la acota `settings.EMAIL_TIMEOUT`: un servidor que cuelga no
    lanza excepción, y sin tope el médico quedaría esperando.
    """
    try:
        destino = comment.block.user.email
        if not destino:
            logger.warning(
                'Rechazo %s: el buzo no tiene correo, no se avisa.', comment.pk)
            return False
        enviados = send_mail(
            subject='Estudio médico rechazado',
            message=_texto(comment),
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[destino],
        )
        return enviados > 0
    except Exception:
        logger.exception(
            'Rechazo %s: no se pudo enviar el correo.', comment.pk)
        return False


def avisar_observacion(observacion) -> bool:
    """Le manda al buzo la observación que dejó el médico o el enfermero.

    Mismo contrato que `avisar_rechazo`: nunca propaga y devuelve si salió.
    """
    try:
        destino = observacion.block.user.email
        if not destino:
            logger.warning(
                'Observación %s: el buzo no tiene correo, no se avisa.', observacion.pk)
            return False
        texto = (
            f'Hay una observación sobre tu estudio "{observacion.block.title}".\n'
            f'\n'
            f'{observacion.content}\n'
            f'\n'
            f'Podés verlo ingresando al sistema: {settings.FRONTEND_URL}\n'
        )
        enviados = send_mail(
            subject='Observación sobre tu estudio médico',
            message=texto,
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[destino],
        )
        return enviados > 0
    except Exception:
        logger.exception(
            'Observación %s: no se pudo enviar el correo.', observacion.pk)
        return False


def avisar_apto(user) -> bool:
    """Le avisa al buzo que todos sus estudios están aprobados: está apto.

    Mismo contrato que `avisar_rechazo`: nunca propaga y devuelve si salió.
    """
    try:
        destino = user.email
        if not destino:
            logger.warning('Apto %s: el buzo no tiene correo, no se avisa.', user.pk)
            return False
        texto = (
            'Todos tus estudios médicos fueron aprobados: estás apto.\n'
            '\n'
            f'Podés verlo ingresando al sistema: {settings.FRONTEND_URL}\n'
        )
        enviados = send_mail(
            subject='Estudios médicos aprobados: estás apto',
            message=texto,
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[destino],
        )
        return enviados > 0
    except Exception:
        logger.exception('Apto %s: no se pudo enviar el correo.', user.pk)
        return False
