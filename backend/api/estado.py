"""El estado del buzo para su pantalla (`GET /api/mi-estado/`).

No calcula nada: serializa el `DiverSummary` del motor. Lo único que decide acá
es qué se le muestra al buzo, y lo que no se le muestra es tan parte del
contrato como lo que sí:

* ni `is_apto` (el apto es de otro plan) ni quién dictaminó (§15.12): el
  rechazo viaja con su motivo y su detalle, sin el nombre ni el rol del
  revisor;
* los estados salen por su nombre (`StudyState.name`), no por su rótulo: la
  traducción al vocabulario de la aplicación es de la pantalla.
"""

from __future__ import annotations

from datetime import date

from . import catalog
from .fitness import (
    StudyState, diver_summary, earliest_valid_date, puede_reemplazarse,
)
from .models import HabilitationWindow
from .serializers import HabilitationWindowSerializer

SIN_VENTANA = 'Se determina al elegir la fecha de habilitación'
SIN_EDAD = 'Se determina al completar la fecha de nacimiento'

#: Lo que necesita una carga nueva ahora: nunca subido, rechazado, vencido o mal
#: fechado. Es el grupo "Falta subir" de la pantalla **menos** BEFORE_WINDOW, a
#: propósito: el Anexo 27 fuera de su ventana todavía no se puede presentar
#: (§15.19), así que un buzo cuyo único pendiente es ése ve "Faltan 0 estudios"
#: con una tarjeta que dice desde cuándo se puede presentar. Parece un error y
#: no lo es: no tiene nada que hacer hoy, y al abrirse la ventana el punto pasa
#: a MISSING y el contador sube a 1. No es `fitness.INCOMPLETE_STATES`, que
#: responde otra pregunta (si la documentación está completa).
ESTADOS_QUE_PIDEN_CARGA = frozenset({
    StudyState.MISSING, StudyState.REJECTED,
    StudyState.EXPIRED, StudyState.DATE_INVALID,
})


def _motivo_no_corresponde(code: str, profile) -> str:
    """Por qué un punto no le corresponde al buzo, en castellano formal.

    Sin ventana o sin fecha de nacimiento el motor no exige nada, y entonces
    la causa no es el punto sino el dato que falta.
    """
    if profile.habilitation_window is None:
        return SIN_VENTANA
    if profile.birth_date is None:
        return SIN_EDAD
    return f'Se exige a partir de los {catalog.get(code).min_age} años de edad'


def _rechazo(slot) -> dict | None:
    """Motivo y detalle del rechazo vigente; nunca quién lo dictó (§15.12)."""
    if slot.state is not StudyState.REJECTED:
        return None
    dictamen = slot.last_dictamen
    return {
        'motivo': dictamen.get_rejection_reason_display(),
        'detalle': dictamen.content,
    }


def _archivo(slot, request) -> str | None:
    if slot.block is None:
        return None
    archivo = slot.block.pdf_attachment
    # `blank=False` no es una restricción de la base: puede haber un bloque sin
    # archivo, y pedirle `.url` a un FieldFile vacío levanta ValueError. Se
    # pregunta por el archivo, no se atrapa la excepción: un archivo que existe
    # pero falta en el disco tiene que notarse, no confundirse con "sin archivo".
    if not archivo:
        return None
    url = archivo.url
    return request.build_absolute_uri(url) if request is not None else url


def armar_estado(profile, today: date, request=None) -> dict:
    """El estado del buzo dueño de `profile`, listo para serializar a JSON.

    `request`, si viene, vuelve absoluta la dirección de los archivos.
    """
    resumen = diver_summary(profile, today)
    ventana = profile.habilitation_window

    estudios = []
    for slot in resumen.slots:
        corresponde = slot.code in resumen.required_codes
        estudios.append({
            'code': slot.code,
            'texto': catalog.get(slot.code).text,
            'estado': slot.state.name,
            'corresponde': corresponde,
            'motivo_no_corresponde': (
                None if corresponde else _motivo_no_corresponde(slot.code, profile)),
            'vence_el': slot.expires_on,
            'desde_cuando': (
                earliest_valid_date(slot.code, ventana)
                if slot.state is StudyState.BEFORE_WINDOW else None),
            'rechazo': _rechazo(slot),
            # La regla es la del motor y se le pasa la ventana, no el estado
            # del slot: sin ventana o sin edad todo punto sale NOT_REQUIRED, y
            # eso no puede ser la llave para pisar lo que el médico aprobó.
            'puede_reemplazarse': puede_reemplazarse(
                slot.code, slot.block, ventana, today),
            'archivo': _archivo(slot, request),
        })

    return {
        'fecha_elegida': (
            None if ventana is None else HabilitationWindowSerializer(ventana).data),
        # Una fecha que ya pasó no se puede elegir: no cuenta como algo que
        # elegir (§15.21).
        'hay_fechas_para_elegir': HabilitationWindow.objects.filter(
            end_date__gte=today).exists(),
        # Sólo cuentan los exigidos: un punto que no corresponde está en
        # NOT_REQUIRED y no entra en el conjunto (ver ESTADOS_QUE_PIDEN_CARGA).
        'faltan': sum(1 for slot in resumen.slots
                      if slot.state in ESTADOS_QUE_PIDEN_CARGA),
        'revisados': resumen.approved,
        'total_exigidos': len(resumen.required_codes),
        'correo': profile.user.email,
        'estudios': estudios,
    }
