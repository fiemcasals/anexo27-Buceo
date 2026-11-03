"""Motor de aptitud derivada.

Ningún estado se guarda ni se tipea: cada lectura lo deriva de los dictámenes y
de las fechas. Así la aptitud de un buzo se cae sola el día que un estudio
vence, sin que nadie tenga que acordarse de cambiar una marca.

Cinco reglas gobiernan el cálculo:

1. La vigencia se mide contra el rango de la fecha de habilitación que el buzo
   eligió, **no** contra hoy.
2. El estudio tiene que estar vigente todos los días del rango, así que el día
   que obliga es el último: ``window.end_date``.
3. La edad es ``año de la habilitación − año de nacimiento``: una resta de años,
   no una edad cumplida. El que cumple 40 en cualquier momento de ese año debe
   los ocho estudios.
4. El Anexo 27 tiene ventana de presentación, no vencimiento común: su fecha más
   vieja aceptable es ``end_date − 30 días``. Sale de la misma fórmula que el
   resto, porque su vigencia de catálogo es de 30 días.
5. ``today`` no interviene en la vigencia (regla 1), pero sí pone un techo a la
   fecha que el buzo declara: un estudio no puede estar hecho en el futuro. Es
   lo único que atrapa el año mal tipeado cuando la fecha errada cae dentro del
   rango.

Las funciones son puras en el sentido que importa acá: **no consultan la base**.
Leen el perfil y sus relaciones ya traídas, así que el llamador que necesita el
plantel entero (unos 150 buzos) lo trae de una sola vez:

.. code-block:: python

    UserProfile.objects.select_related("user", "habilitation_window").prefetch_related(
        Prefetch(
            "user__study_blocks",
            queryset=StudyBlock.objects.filter(is_current=True).prefetch_related(
                "comments"
            ),
        )
    )

El motor filtra ``is_current`` y ordena los dictámenes en memoria, así que sirve
igual si el ``Prefetch`` no filtra ni ordena; lo que no debe hacer el llamador es
dejar sin traer los bloques o los dictámenes, porque entonces cada punto de cada
buzo cuesta una consulta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from django.utils import timezone

from . import catalog

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from users.models import UserProfile

    from .models import Comment, HabilitationWindow, StudyBlock


class StudyState(Enum):
    """Estado de un punto de la directiva para una fecha de habilitación."""

    NOT_REQUIRED = "NOT_REQUIRED"      # no le corresponde (edad, o no hay con qué medir)
    MISSING = "MISSING"                # exigido y sin cargar
    BEFORE_WINDOW = "BEFORE_WINDOW"    # todavía no se puede presentar
    IN_REVIEW = "IN_REVIEW"            # cargado y sin dictamen
    PRE_REVIEWED = "PRE_REVIEWED"      # pre-aprobado por el enfermero: falta el médico
    APPROVED = "APPROVED"              # aprobado por el médico
    REJECTED = "REJECTED"              # rechazado
    EXPIRED = "EXPIRED"                # no cubre todo el rango elegido
    DATE_INVALID = "DATE_INVALID"      # fechado después del rango


class DiverState(Enum):
    """Estado global de un buzo frente a su fecha de habilitación.

    Son los seis del §7, uno por uno: el listado del médico muestra esta fila
    tal cual, sin volver a derivarla de los estados de cada punto.
    """

    NO_WINDOW = "NO_WINDOW"            # no eligió fecha: no hay contra qué medir
    UNKNOWN_AGE = "UNKNOWN_AGE"        # sin fecha de nacimiento no se sabe qué debe
    REJECTED = "REJECTED"              # algo rechazado
    EXPIRED = "EXPIRED"                # algo vencido o mal fechado
    INCOMPLETE = "INCOMPLETE"          # falta documentación
    TO_REVIEW = "TO_REVIEW"            # todo presentado, falta dictamen
    APTO = "APTO"                      # todo exigido aprobado por el médico y vigente


#: Puntos rechazados: el buzo tiene que leer el motivo para poder arreglarlos.
REJECTED_STATES = frozenset({StudyState.REJECTED})
#: Puntos cuya fecha no sirve para esta ventana. ``DATE_INVALID`` se pliega acá
#: y no en los rechazados: un estudio mal fechado es, en la práctica, un
#: documento que no cubre el rango, igual que uno vencido, y como el vencido no
#: lleva un motivo que alguien tenga que leer.
EXPIRED_STATES = frozenset({StudyState.EXPIRED, StudyState.DATE_INVALID})
#: Puntos que piden una corrección: el buzo tiene que volver a cargarlos. Es la
#: unión de los dos anteriores, y son disjuntos.
PROBLEM_STATES = REJECTED_STATES | EXPIRED_STATES
#: Puntos que todavía no están presentados.
INCOMPLETE_STATES = frozenset({StudyState.MISSING, StudyState.BEFORE_WINDOW})
#: Puntos presentados que esperan el dictamen del médico.
REVIEW_STATES = frozenset({StudyState.IN_REVIEW, StudyState.PRE_REVIEWED})

#: El último dictamen manda. La base garantiza que sólo existen cuatro
#: combinaciones, y que toda aprobación es del médico, así que el veredicto
#: alcanza para nombrar el estado.
_STATE_BY_VERDICT = {
    "APPROVED": StudyState.APPROVED,
    "PRE_APPROVED": StudyState.PRE_REVIEWED,
    "REJECTED": StudyState.REJECTED,
}

_DOCTOR = "DOCTOR"


@dataclass(frozen=True)
class SlotStatus:
    """Lo que se sabe de un punto de la directiva para un buzo."""

    code: str
    state: StudyState
    block: StudyBlock | None
    last_dictamen: Comment | None
    #: Último día en que el estudio cargado sigue vigente; None si no hay carga.
    expires_on: date | None


@dataclass(frozen=True)
class DiverSummary:
    """Todo lo que las pantallas y los avisos necesitan de un buzo."""

    required_codes: tuple[str, ...]
    #: Los ocho puntos del catálogo, en su orden; los que no corresponden van
    #: en NOT_REQUIRED pero conservan su carga, si hay.
    slots: tuple[SlotStatus, ...]
    presented: int
    approved: int
    pending_review: int
    pre_reviewed: int
    #: Total de puntos a corregir: siempre ``expired + rejected``. Se conserva
    #: porque el total es lo que resume la fila; el desglose está abajo.
    problems: int
    #: Desglose de ``problems``. El §8.1 pide "cuántos vencidos" en particular y
    #: el §13 nombra la fila del plantel como "... vencidos, rechazados ...".
    expired: int
    rejected: int
    last_doctor_review: date | None
    state: DiverState
    is_apto: bool


def habilitation_year(window: HabilitationWindow) -> int:
    """Año de la habilitación: el del último día del rango, que es el que obliga."""
    return window.end_date.year


def validity_ends_on(study_code: str, study_date: date) -> date:
    """Último día en que un estudio de ese punto y esa fecha sigue vigente."""
    return study_date + timedelta(days=catalog.get(study_code).validity_days)


def earliest_valid_date(study_code: str, window: HabilitationWindow) -> date:
    """Fecha más vieja que puede llevar el estudio para cubrir todo el rango.

    Para el Anexo 27 son los 30 días de ``window.anexo27_earliest_date``; para
    los demás, los 365 de su vigencia.
    """
    return window.end_date - timedelta(days=catalog.get(study_code).validity_days)


def required_codes(profile: UserProfile) -> tuple[str, ...]:
    """Puntos que le corresponden al buzo; vacío si falta la fecha de habilitación
    o la de nacimiento, porque entonces no hay con qué determinarlos."""
    window = profile.habilitation_window
    if window is None:
        return ()
    return _codes_for_age(profile.age_in_year(habilitation_year(window)))


def diver_summary(profile: UserProfile, today: date) -> DiverSummary:
    """Estado derivado de un buzo. No consulta la base más allá de lo que el
    llamador no haya traído (ver el docstring del módulo)."""
    window = profile.habilitation_window
    age = None if window is None else profile.age_in_year(habilitation_year(window))
    required = _codes_for_age(age)
    current = _current_blocks(profile)

    slots = tuple(
        _slot_status(code, current.get(code), window,
                     required=code in required, today=today)
        for code in catalog.CODES
    )
    required_slots = [slot for slot in slots if slot.code in required]
    states = [slot.state for slot in required_slots]
    state = _diver_state(window, age, states)
    expired = sum(1 for s in states if s in EXPIRED_STATES)
    rejected = sum(1 for s in states if s in REJECTED_STATES)

    return DiverSummary(
        required_codes=required,
        slots=slots,
        presented=sum(1 for slot in required_slots if slot.block is not None),
        approved=states.count(StudyState.APPROVED),
        pending_review=states.count(StudyState.IN_REVIEW),
        pre_reviewed=states.count(StudyState.PRE_REVIEWED),
        problems=expired + rejected,
        expired=expired,
        rejected=rejected,
        last_doctor_review=_last_doctor_review(slots),
        state=state,
        is_apto=state is DiverState.APTO,
    )


def _codes_for_age(age: int | None) -> tuple[str, ...]:
    if age is None:
        return ()
    return tuple(study.code for study in catalog.required_for_age(age))


def _current_blocks(profile: UserProfile) -> dict[str, StudyBlock]:
    """La carga vigente de cada punto.

    Filtra en memoria a propósito: así aprovecha el cache de ``prefetch_related``
    en lugar de disparar una consulta por buzo. La restricción
    ``one_current_study_per_diver_and_point`` garantiza que no haya dos.
    """
    return {
        block.study_code: block
        for block in profile.user.study_blocks.all()
        if block.is_current
    }


def _latest_dictamen(block: StudyBlock) -> Comment | None:
    """El último dictamen del punto.

    La historia no se pisa: un punto puede tener la pre-aprobación del
    enfermero y después el rechazo del médico, y las dos filas quedan. Vale el
    último, no "existe alguno de tal tipo". Ordena en memoria para no perder el
    cache del prefetch ni depender del orden con que lo trajo el llamador.
    """
    dictamenes = sorted(block.comments.all(), key=lambda c: (c.created_at, c.pk))
    return dictamenes[-1] if dictamenes else None


def _slot_status(code: str, block: StudyBlock | None,
                 window: HabilitationWindow | None, *,
                 required: bool, today: date) -> SlotStatus:
    dictamen = None if block is None else _latest_dictamen(block)
    return SlotStatus(
        code=code,
        state=_study_state(code, block, dictamen, window,
                           required=required, today=today),
        block=block,
        last_dictamen=dictamen,
        expires_on=(None if block is None
                    else validity_ends_on(code, block.study_date)),
    )


def _study_state(code: str, block: StudyBlock | None, dictamen: Comment | None,
                 window: HabilitationWindow | None, *,
                 required: bool, today: date) -> StudyState:
    if not required:
        # Sin ventana o sin edad no hay nada exigido, así que `window` puede ser
        # None y no se lo toca.
        return StudyState.NOT_REQUIRED
    if block is None:
        # Un estudio hecho hoy vencería antes del último día del rango: el punto
        # todavía no se puede presentar. Es el caso del Anexo 27.
        if today < earliest_valid_date(code, window):
            return StudyState.BEFORE_WINDOW
        return StudyState.MISSING
    # La fecha manda sobre el dictamen: un estudio que no cubre el rango no
    # sirve ni aprobado.
    #
    # Dos topes, y manda el más bajo. La comparación es estricta: la fecha del
    # tope sirve, la siguiente no.
    #   - `window.end_date`: un estudio fechado después del rango no puede
    #     estar cubriéndolo.
    #   - `today`: un estudio no puede estar hecho en el futuro. Sin este tope,
    #     el error de tipear el año de más queda dentro del rango y pasa por
    #     vigente: el buzo termina APTO con un papel que ya no sirve.
    latest_trusted_date = min(today, window.end_date)
    if block.study_date > latest_trusted_date:
        return StudyState.DATE_INVALID
    if validity_ends_on(code, block.study_date) < window.end_date:
        return StudyState.EXPIRED
    if dictamen is None:
        return StudyState.IN_REVIEW
    return _STATE_BY_VERDICT[dictamen.status]


def _last_doctor_review(slots: tuple[SlotStatus, ...]) -> date | None:
    """Día del último dictamen del médico sobre alguna carga vigente del buzo.

    Las pre-aprobaciones del enfermero no cuentan: la pregunta es cuándo miró el
    médico. Recorre los ocho puntos, no sólo los exigidos, para que un punto que
    la edad dejó afuera no borre el registro de que el médico lo revisó.
    """
    days = [
        timezone.localtime(dictamen.created_at).date()
        for slot in slots if slot.block is not None
        for dictamen in slot.block.comments.all()
        if dictamen.reviewer_role == _DOCTOR
    ]
    return max(days) if days else None


def _diver_state(window: HabilitationWindow | None, age: int | None,
                 states: list[StudyState]) -> DiverState:
    """Estado de la fila del §7, en su orden de prioridad.

    El §7 pone Vencido y Rechazado por delante de los demás, porque son los dos
    que necesitan que alguien actúe ya; entre esos dos, la precedencia es la que
    documenta el bloque de abajo.
    """
    if window is None:
        return DiverState.NO_WINDOW
    if age is None:
        return DiverState.UNKNOWN_AGE
    present = set(states)
    # Precedencia entre los dos estados que el §7 marca como prioritarios: si
    # el buzo tiene un estudio rechazado y otro vencido, gana REJECTED, porque
    # el rechazo trae un motivo que el buzo tiene que leer para poder
    # arreglarlo, mientras que "vencido" se explica solo.
    if present & REJECTED_STATES:
        return DiverState.REJECTED
    if present & EXPIRED_STATES:
        return DiverState.EXPIRED
    if present & INCOMPLETE_STATES:
        return DiverState.INCOMPLETE
    if present & REVIEW_STATES:
        return DiverState.TO_REVIEW
    # Agotados los anteriores, a cada punto exigido sólo le queda APPROVED. Y
    # con ventana y edad siempre hay al menos un punto exigido (los siete que no
    # dependen de la edad), así que el apto nunca sale de un conjunto vacío.
    return DiverState.APTO
