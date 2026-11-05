"""Aviso por correo al buzo cuando se le rechaza un estudio.

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
