"""Tests del motor de aptitud derivada.

Ningún estado se guarda ni se tipea: todo sale de los dictámenes y las fechas,
medido contra el rango de la fecha de habilitación elegida, no contra hoy.
"""

import itertools
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.test import TestCase
from django.utils import timezone

from api import catalog, fitness
from api.fitness import DiverState, StudyState
from api.models import Comment, HabilitationWindow, StudyBlock
from users.models import UserProfile

TODAY = date(2026, 11, 3)

#: Fecha de estudio que deja vigente cualquiera de los ocho puntos en la ventana
#: de noviembre de 2026, incluido el Anexo 27 (cuya ventana abre el 21/10/2026).
VALID_FOR_EVERY_POINT = date(2026, 10, 30)

_counter = itertools.count(1)


def _november_2026():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="FIRST",
        start_date=date(2026, 11, 18), end_date=date(2026, 11, 20))


def _july_2027():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="COMPLEMENTARY",
        start_date=date(2027, 7, 12), end_date=date(2027, 7, 14))


def _diver(birth_year, birth_month=6, birth_day=15, window=None, dni=None):
    """Perfil de buzo. birth_year=None deja birth_date vacía."""
    n = next(_counter)
    return UserProfile.objects.create(
        user=User.objects.create(username=f"buzo{n}"),
        dni=dni or f"{30_000_000 + n}",
        birth_date=(None if birth_year is None
                    else date(birth_year, birth_month, birth_day)),
        habilitation_window=window,
    )


def _reviewer(role):
    return User.objects.get_or_create(username=f"revisor-{role.lower()}")[0]


def _upload(profile, code, study_date, dictamenes=(), reviewed_on=None):
    """Crea el StudyBlock vigente del punto y sus dictámenes en orden.

    `dictamenes` es una secuencia de (status, reviewer_role). `reviewed_on` fija
    el día del primer dictamen (por defecto el del estudio) y cada dictamen
    siguiente queda un día después, para que el orden no dependa del reloj.
    """
    block = StudyBlock.objects.create(
        user=profile.user, study_code=code, study_date=study_date)
    first_day = reviewed_on or study_date
    for offset, (status, role) in enumerate(dictamenes):
        extra = ({"content": "Falta la firma.", "rejection_reason": "OTHER"}
                 if status == "REJECTED" else {})
        dictamen = Comment.objects.create(
            block=block, doctor=_reviewer(role),
            status=status, reviewer_role=role, **extra)
        # created_at es auto_now_add: sólo la base acepta otra fecha.
        Comment.objects.filter(pk=dictamen.pk).update(
            created_at=timezone.make_aware(datetime.combine(
                first_day + timedelta(days=offset), time(12, 0))))
    return block


def _slot_of(summary, code):
    """El SlotStatus de un punto."""
    return next(slot for slot in summary.slots if slot.code == code)


class RequiredSetTests(TestCase):
    def test_under_forty_in_the_habilitation_year_owes_seven(self):
        # Nacido en 1988, habilitación de noviembre de 2026 -> 38
        p = _diver(birth_year=1988, window=_november_2026())
        self.assertEqual(fitness.required_codes(p), tuple("bcdefgh"))

    def test_turning_forty_during_the_habilitation_year_owes_eight(self):
        # Nacido el 31/12/1986: el 18 de noviembre de 2026 tiene 39 cumplidos,
        # pero el criterio de la unidad es la edad a fin de año -> 40.
        p = _diver(birth_year=1986, birth_month=12, birth_day=31,
                   window=_november_2026())
        self.assertEqual(fitness.required_codes(p), tuple("abcdefgh"))

    def test_thirty_nine_in_the_habilitation_year_still_owes_seven(self):
        # El límite es 40: con 39 el esfuerzo todavía no corresponde.
        p = _diver(birth_year=1987, window=_november_2026())
        self.assertEqual(fitness.required_codes(p), tuple("bcdefgh"))

    def test_the_complementary_date_uses_its_own_year(self):
        # Complementaria de julio de 2027: el mismo buzo es un año mayor.
        p = _diver(birth_year=1987, window=_july_2027())
        self.assertEqual(fitness.required_codes(p), tuple("abcdefgh"))

    def test_no_window_means_nothing_can_be_required(self):
        self.assertEqual(fitness.required_codes(_diver(birth_year=1988)), ())

    def test_no_birth_date_means_nothing_can_be_required(self):
        self.assertEqual(
            fitness.required_codes(_diver(birth_year=None, window=_november_2026())), ()
        )


class SlotStateTests(TestCase):
    # Ventana: 18 al 20 de noviembre de 2026. El estudio tiene que estar
    # vigente el día 20, que es el más exigente.

    def setUp(self):
        self.window = _november_2026()

    def _state(self, code, study_date=None, dictamen=None, dictamenes=None,
               block=True, today=TODAY, birth_year=1986, window=None):
        """Estado del punto `code` de un buzo que sólo cargó ese punto.

        `block=None` arma el buzo sin ninguna carga. Por defecto el buzo tiene
        40 años en 2026, así que le corresponden los ocho puntos.
        """
        p = _diver(birth_year=birth_year, birth_month=12, birth_day=31,
                   window=window or self.window)
        if block is not None:
            if dictamenes is None:
                dictamenes = [dictamen] if dictamen else []
            _upload(p, code, study_date or VALID_FOR_EVERY_POINT,
                    dictamenes=dictamenes)
        return _slot_of(fitness.diver_summary(p, today), code).state

    def _state_for_young_diver(self, code):
        """Lo mismo, con un buzo de 38 años en 2026."""
        return self._state(code, block=None, birth_year=1988)

    def test_approved_and_valid_through_the_last_day(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.APPROVED)

    def test_approved_but_expiring_inside_the_window_is_expired(self):
        # Vence el 19: no cubre el día 20.
        self.assertEqual(self._state("b", study_date=date(2025, 11, 19),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.EXPIRED)

    def test_a_study_valid_exactly_through_the_last_day_is_not_expired(self):
        # Vence el 20, el último día del rango: el límite es inclusivo.
        self.assertEqual(self._state("b", study_date=date(2025, 11, 20),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.APPROVED)

    def test_a_nurse_approval_is_only_a_pre_review(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15),
                                     dictamen=("PRE_APPROVED", "NURSE")),
                         StudyState.PRE_REVIEWED)

    def test_uploaded_without_any_dictamen_is_in_review(self):
        self.assertEqual(self._state("b", study_date=date(2026, 1, 15)),
                         StudyState.IN_REVIEW)

    def test_the_last_dictamen_wins(self):
        # Pre-aprobado por el enfermero y después rechazado por el médico.
        self.assertEqual(
            self._state("b", study_date=date(2026, 1, 15),
                        dictamenes=[("PRE_APPROVED", "NURSE"), ("REJECTED", "DOCTOR")]),
            StudyState.REJECTED,
        )

    def test_the_last_dictamen_wins_also_when_it_lifts_a_rejection(self):
        # El enfermero rechazó y el médico después aprobó: vale el último.
        self.assertEqual(
            self._state("b", study_date=date(2026, 1, 15),
                        dictamenes=[("REJECTED", "NURSE"), ("APPROVED", "DOCTOR")]),
            StudyState.APPROVED,
        )

    def test_a_point_that_does_not_apply_by_age(self):
        self.assertEqual(self._state_for_young_diver("a"), StudyState.NOT_REQUIRED)

    def test_a_required_point_with_nothing_uploaded_is_missing(self):
        self.assertEqual(self._state("g", block=None), StudyState.MISSING)

    def test_the_anexo_27_is_not_missing_before_its_window_opens(self):
        # La ventana abre el 21/10/2026; hoy es el 3/10.
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 3)),
                         StudyState.BEFORE_WINDOW)

    def test_the_anexo_27_is_missing_once_its_window_is_open(self):
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 25)),
                         StudyState.MISSING)

    def test_the_anexo_27_window_opens_on_the_thirtieth_day_before_the_end(self):
        # 20/11 - 30 = 21/10. Ese día ya se puede presentar; el anterior, no.
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 21)),
                         StudyState.MISSING)
        self.assertEqual(self._state("h", block=None, today=date(2026, 10, 20)),
                         StudyState.BEFORE_WINDOW)

    def test_an_anexo_27_dated_when_its_window_opens_is_valid(self):
        self.assertEqual(self._state("h", study_date=date(2026, 10, 21),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.APPROVED)

    def test_an_anexo_27_dated_one_day_before_its_window_is_too_old(self):
        self.assertEqual(self._state("h", study_date=date(2026, 10, 20),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.EXPIRED)

    def test_a_study_dated_on_the_last_day_of_the_window_is_valid(self):
        # `today` es ese mismo día: el tope de confianza es el menor entre hoy y
        # el fin del rango, así que el borde de `end_date` sólo se puede medir
        # cuando ese día llegó. Antes, manda el tope de hoy (ver los tres tests
        # de fecha futura más abajo).
        self.assertEqual(self._state("b", study_date=date(2026, 11, 20),
                                     today=date(2026, 11, 20),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.APPROVED)

    def test_a_study_dated_after_the_window_is_flagged_not_trusted(self):
        # El buzo tipeó 2027 por 2026. No puede contar como vigente.
        self.assertEqual(self._state("b", study_date=date(2027, 1, 15),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.DATE_INVALID)

    def test_a_study_dated_in_the_future_but_inside_the_window_is_not_trusted(self):
        # Ventana complementaria (12 al 14/07/2027): el buzo tipeó 2027 por 2026
        # al cargar un estudio hecho el 15/01/2026. La fecha cae ANTES del fin
        # del rango, así que la regla de la ventana no la atrapa, y la vigencia
        # llegaría hasta 2028. El tope es hoy: un estudio del futuro no existe.
        self.assertEqual(
            self._state("b", study_date=date(2027, 1, 15), today=TODAY,
                        dictamen=("APPROVED", "DOCTOR"), window=_july_2027()),
            StudyState.DATE_INVALID,
        )

    def test_a_study_dated_after_a_window_that_already_passed_is_not_trusted(self):
        # El otro tope del `min`: la ventana cerró el 20/11 y hoy es el 1/12. Un
        # estudio fechado el 25/11 ya no está en el futuro, pero tampoco pudo
        # cubrir un rango que terminó antes.
        self.assertEqual(
            self._state("b", study_date=date(2026, 11, 25),
                        today=date(2026, 12, 1),
                        dictamen=("APPROVED", "DOCTOR")),
            StudyState.DATE_INVALID,
        )

    def test_a_study_dated_today_is_trusted(self):
        # El tope es estricto: hoy sirve, mañana no. Sin esto, el arreglo
        # anterior podría rechazar el estudio que el buzo acaba de hacerse.
        self.assertEqual(
            self._state("b", study_date=TODAY, today=TODAY,
                        dictamen=("APPROVED", "DOCTOR"), window=_july_2027()),
            StudyState.APPROVED,
        )

    def test_a_study_dated_tomorrow_is_not_trusted(self):
        self.assertEqual(
            self._state("b", study_date=TODAY + timedelta(days=1), today=TODAY,
                        dictamen=("APPROVED", "DOCTOR"), window=_july_2027()),
            StudyState.DATE_INVALID,
        )

    def test_a_study_dated_one_day_after_the_window_is_already_not_trusted(self):
        self.assertEqual(self._state("b", study_date=date(2026, 11, 21),
                                     dictamen=("APPROVED", "DOCTOR")),
                         StudyState.DATE_INVALID)

    def test_a_single_day_window_is_judged_against_that_one_day(self):
        one_day = HabilitationWindow.objects.create(
            cycle=2025, slot="SECOND",
            start_date=date(2026, 11, 18), end_date=date(2026, 11, 18))
        self.assertEqual(self._state("b", study_date=date(2025, 11, 18),
                                     dictamen=("APPROVED", "DOCTOR"),
                                     window=one_day),
                         StudyState.APPROVED)
        self.assertEqual(self._state("b", study_date=date(2025, 11, 17),
                                     dictamen=("APPROVED", "DOCTOR"),
                                     window=one_day),
                         StudyState.EXPIRED)

    def test_only_the_current_block_of_a_slot_is_considered(self):
        # Un rechazado histórico no debe pisar al reemplazo aprobado.
        p = _diver(birth_year=1988, window=self.window)
        _upload(p, "f", date(2026, 10, 18),
                dictamenes=[("REJECTED", "NURSE")])          # queda histórico
        _upload(p, "f", date(2026, 10, 30),
                dictamenes=[("APPROVED", "DOCTOR")])         # pasa a vigente
        slot = _slot_of(fitness.diver_summary(p, TODAY), "f")
        self.assertEqual(slot.state, StudyState.APPROVED)
        self.assertEqual(slot.block.study_date, date(2026, 10, 30))

    def test_a_demoted_block_is_ignored_even_if_it_was_saved_last(self):
        # El orden de llegada no decide nada: decide is_current. Sin esto, el
        # test anterior pasaría igual por el orden de las filas.
        p = _diver(birth_year=1988, window=self.window)
        current = _upload(p, "f", date(2026, 10, 30),
                          dictamenes=[("APPROVED", "DOCTOR")])
        stale = _upload(p, "f", date(2026, 10, 18),
                        dictamenes=[("REJECTED", "NURSE")])
        # Al guardarse, `stale` pasó a vigente y bajó al otro; se repone el
        # bueno, que es lo que hace el buzo cuando se equivocó de archivo.
        StudyBlock.objects.filter(pk=stale.pk).update(is_current=False)
        StudyBlock.objects.filter(pk=current.pk).update(is_current=True)
        slot = _slot_of(fitness.diver_summary(p, TODAY), "f")
        self.assertEqual(slot.state, StudyState.APPROVED)
        self.assertEqual(slot.block.pk, current.pk)

    def test_a_slot_whose_only_block_is_demoted_counts_as_missing(self):
        # Discrimina sin depender del orden en que lleguen las filas: hay una
        # sola, y es histórica. Sigue valiendo si StudyBlock gana un ordering.
        p = _diver(birth_year=1988, window=self.window)
        stale = _upload(p, "e", date(2026, 10, 18),
                        dictamenes=[("APPROVED", "DOCTOR")])
        StudyBlock.objects.filter(pk=stale.pk).update(is_current=False)
        slot = _slot_of(fitness.diver_summary(p, TODAY), "e")
        self.assertEqual(slot.state, StudyState.MISSING)
        self.assertIsNone(slot.block)

    def test_a_study_both_rejected_and_expired_reports_expired(self):
        # La fecha manda sobre el dictamen: vencido el 19, no cubre el 20.
        p = _diver(birth_year=1988, window=self.window)
        _upload(p, "b", date(2025, 11, 19), dictamenes=[("REJECTED", "DOCTOR")])
        slot = _slot_of(fitness.diver_summary(p, TODAY), "b")
        self.assertEqual(slot.state, StudyState.EXPIRED)
        # Y el motivo no se pierde: queda a la vista al lado del vencimiento.
        self.assertEqual(slot.last_dictamen.status, "REJECTED")
        self.assertEqual(slot.last_dictamen.rejection_reason, "OTHER")
        self.assertEqual(slot.last_dictamen.content, "Falta la firma.")

    def test_the_slot_carries_the_block_and_its_last_dictamen(self):
        p = _diver(birth_year=1988, window=self.window)
        block = _upload(p, "f", date(2026, 10, 18),
                        dictamenes=[("PRE_APPROVED", "NURSE"),
                                    ("REJECTED", "DOCTOR")])
        slot = _slot_of(fitness.diver_summary(p, TODAY), "f")
        self.assertEqual(slot.block.pk, block.pk)
        self.assertEqual(slot.last_dictamen.status, "REJECTED")
        self.assertEqual(slot.last_dictamen.reviewer_role, "DOCTOR")

    def test_expires_on_is_the_last_day_the_study_still_covers(self):
        p = _diver(birth_year=1988, window=self.window)
        _upload(p, "b", date(2026, 1, 15))
        _upload(p, "h", date(2026, 10, 30))
        summary = fitness.diver_summary(p, TODAY)
        self.assertEqual(_slot_of(summary, "b").expires_on, date(2027, 1, 15))
        self.assertEqual(_slot_of(summary, "h").expires_on, date(2026, 11, 29))

    def test_a_slot_with_nothing_uploaded_has_no_expiry(self):
        p = _diver(birth_year=1988, window=self.window)
        slot = _slot_of(fitness.diver_summary(p, TODAY), "b")
        self.assertIsNone(slot.expires_on)
        self.assertIsNone(slot.block)
        self.assertIsNone(slot.last_dictamen)

    def test_the_engine_and_the_window_agree_on_the_anexo_27_opening(self):
        # Una sola regla: la del catálogo. Si alguna de las dos cambia, falla.
        window = self.window
        self.assertEqual(fitness.earliest_valid_date("h", window),
                         window.anexo27_earliest_date)


class DiverSummaryTests(TestCase):
    # El buzo base tiene 38 años en 2026: le corresponden siete puntos (b..h).
    REQUIRED = tuple("bcdefgh")

    def _base_diver(self):
        return _diver(birth_year=1988, window=_november_2026())

    def _diver_with_every_point(self, dictamenes, codes=None):
        p = self._base_diver()
        for code in (codes or self.REQUIRED):
            _upload(p, code, VALID_FOR_EVERY_POINT, dictamenes=dictamenes)
        return p

    def _diver_with_all_approved_by_doctor(self):
        return self._diver_with_every_point([("APPROVED", "DOCTOR")])

    def _diver_with_all_pre_approved(self):
        return self._diver_with_every_point([("PRE_APPROVED", "NURSE")])

    def _summary_with_one_rejected_and_two_missing(self):
        p = self._base_diver()
        _upload(p, "b", VALID_FOR_EVERY_POINT, dictamenes=[("REJECTED", "DOCTOR")])
        for code in "cdef":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        # g y h quedan sin cargar.
        return fitness.diver_summary(p, TODAY)

    def _summary_all_uploaded_one_rejected(self):
        p = self._base_diver()
        _upload(p, "b", VALID_FOR_EVERY_POINT, dictamenes=[("REJECTED", "DOCTOR")])
        for code in "cdefgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        return fitness.diver_summary(p, TODAY)

    def _summary_reviewed_by_doctor_then_nurse(self):
        p = self._base_diver()
        _upload(p, "b", VALID_FOR_EVERY_POINT,
                dictamenes=[("APPROVED", "DOCTOR")], reviewed_on=date(2026, 10, 14))
        _upload(p, "c", VALID_FOR_EVERY_POINT,
                dictamenes=[("PRE_APPROVED", "NURSE")], reviewed_on=date(2026, 10, 28))
        return fitness.diver_summary(p, TODAY)

    def _summary_only_pre_reviewed(self):
        return fitness.diver_summary(self._diver_with_all_pre_approved(), TODAY)

    def test_apto_needs_every_required_point_approved_by_the_doctor(self):
        s = fitness.diver_summary(self._diver_with_all_approved_by_doctor(), TODAY)
        self.assertTrue(s.is_apto)
        self.assertEqual(s.state, DiverState.APTO)
        self.assertEqual(s.approved, 7)

    def test_nurse_pre_approvals_never_make_anyone_apto(self):
        s = fitness.diver_summary(self._diver_with_all_pre_approved(), TODAY)
        self.assertFalse(s.is_apto)
        self.assertEqual(s.approved, 0)
        self.assertEqual(s.pre_reviewed, 7)
        self.assertEqual(s.state, DiverState.TO_REVIEW)

    def test_without_a_window_nobody_is_apto(self):
        s = fitness.diver_summary(_diver(birth_year=1988), TODAY)
        self.assertFalse(s.is_apto)
        self.assertEqual(s.state, DiverState.NO_WINDOW)

    def test_without_a_birth_date_the_state_says_so(self):
        s = fitness.diver_summary(
            _diver(birth_year=None, window=_november_2026()), TODAY)
        self.assertEqual(s.state, DiverState.UNKNOWN_AGE)
        self.assertFalse(s.is_apto)

    def test_a_rejection_outranks_an_incomplete_set(self):
        self.assertEqual(self._summary_with_one_rejected_and_two_missing().state,
                         DiverState.REJECTED)

    def test_presented_counts_rejected_and_expired_as_presented(self):
        # "Documentación completa" significa todo subido, no todo aprobado (§8.1).
        self.assertEqual(self._summary_all_uploaded_one_rejected().presented, 7)

    def test_last_doctor_review_ignores_nurse_dictamenes(self):
        s = self._summary_reviewed_by_doctor_then_nurse()
        self.assertEqual(s.last_doctor_review, date(2026, 10, 14))

    def test_last_doctor_review_is_none_when_the_doctor_never_looked(self):
        self.assertIsNone(self._summary_only_pre_reviewed().last_doctor_review)

    def test_last_doctor_review_is_the_calendar_day_in_buenos_aires(self):
        # Un dictamen firmado a las 22:00 del 27/10 en Buenos Aires se guarda
        # como 01:00 UTC del 28. La columna del médico tiene que decir 27: la
        # pregunta es qué día lo miró, y los días son los de acá.
        p = self._base_diver()
        block = _upload(p, "b", VALID_FOR_EVERY_POINT,
                        dictamenes=[("APPROVED", "DOCTOR")])
        Comment.objects.filter(block=block).update(
            created_at=datetime(2026, 10, 28, 1, 0, tzinfo=dt_timezone.utc))
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.last_doctor_review, date(2026, 10, 27))

    # --- Más allá de los casos del brief ---

    def test_the_summary_reports_the_required_set_and_all_eight_slots(self):
        s = fitness.diver_summary(self._base_diver(), TODAY)
        self.assertEqual(s.required_codes, self.REQUIRED)
        self.assertEqual(tuple(slot.code for slot in s.slots), catalog.CODES)

    def test_a_point_outside_the_required_set_is_not_counted(self):
        # El buzo de 38 subió el esfuerzo de más: no suma ni al presentado ni
        # al aprobado.
        p = self._diver_with_all_approved_by_doctor()
        _upload(p, "a", VALID_FOR_EVERY_POINT, dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(_slot_of(s, "a").state, StudyState.NOT_REQUIRED)
        self.assertEqual(s.approved, 7)
        self.assertEqual(s.presented, 7)
        self.assertEqual(s.state, DiverState.APTO)

    def test_last_doctor_review_counts_a_point_the_age_rule_left_out(self):
        # El médico revisó el esfuerzo que este buzo de 38 no debía presentar,
        # y es el único dictamen suyo: que el punto no se exija no borra el
        # registro de que lo miró.
        p = self._base_diver()
        _upload(p, "a", VALID_FOR_EVERY_POINT,
                dictamenes=[("APPROVED", "DOCTOR")], reviewed_on=date(2026, 10, 14))
        _upload(p, "b", VALID_FOR_EVERY_POINT,
                dictamenes=[("PRE_APPROVED", "NURSE")], reviewed_on=date(2026, 10, 28))
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(_slot_of(s, "a").state, StudyState.NOT_REQUIRED)
        self.assertEqual(s.last_doctor_review, date(2026, 10, 14))

    def test_the_counters_split_the_required_points_by_state(self):
        p = self._base_diver()
        _upload(p, "b", VALID_FOR_EVERY_POINT, dictamenes=[("APPROVED", "DOCTOR")])
        _upload(p, "c", VALID_FOR_EVERY_POINT, dictamenes=[("PRE_APPROVED", "NURSE")])
        _upload(p, "d", VALID_FOR_EVERY_POINT)
        _upload(p, "e", VALID_FOR_EVERY_POINT, dictamenes=[("REJECTED", "DOCTOR")])
        _upload(p, "f", date(2025, 11, 19), dictamenes=[("APPROVED", "DOCTOR")])
        _upload(p, "g", date(2027, 1, 15), dictamenes=[("APPROVED", "DOCTOR")])
        # h queda sin cargar.
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.presented, 6)
        self.assertEqual(s.approved, 1)
        self.assertEqual(s.pre_reviewed, 1)
        self.assertEqual(s.pending_review, 1)
        self.assertEqual(s.problems, 3)   # rechazado, vencido y fecha inválida
        # `problems` es la suma de los dos desgloses, y la fecha inválida cuenta
        # como vencida: un papel mal fechado tampoco sirve para esta ventana.
        self.assertEqual(s.rejected, 1)
        self.assertEqual(s.expired, 2)
        self.assertEqual(s.problems, s.rejected + s.expired)
        self.assertEqual(_slot_of(s, "f").state, StudyState.EXPIRED)
        self.assertEqual(_slot_of(s, "g").state, StudyState.DATE_INVALID)
        self.assertEqual(_slot_of(s, "h").state, StudyState.MISSING)
        self.assertEqual(s.state, DiverState.REJECTED)

    def test_a_future_dated_study_cannot_leave_the_diver_apto(self):
        # El peligro concreto: el buzo cargó el ecocardiograma que se hizo el
        # 15/11/2025 (vence el 15/11/2026, antes del 20) pero tipeó el año
        # corriente, 15/11/2026. Esa fecha cae DENTRO del rango, así que no es
        # posterior al fin de la ventana, y su vigencia llega hasta 2027: sin el
        # tope de hoy el punto sale aprobado y el buzo queda APTO con un papel
        # que en realidad ya no cubre su fecha de habilitación.
        p = self._base_diver()
        for code in "cdefgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        _upload(p, "b", date(2026, 11, 15), dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)       # hoy es el 3/11/2026
        self.assertEqual(_slot_of(s, "b").state, StudyState.DATE_INVALID)
        self.assertFalse(s.is_apto)
        self.assertEqual(s.state, DiverState.EXPIRED)
        self.assertEqual(s.problems, 1)

    def test_an_expired_point_is_a_problem_even_with_everything_uploaded(self):
        p = self._base_diver()
        _upload(p, "b", date(2025, 11, 19), dictamenes=[("APPROVED", "DOCTOR")])
        for code in "cdefgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.state, DiverState.EXPIRED)
        self.assertEqual(s.problems, 1)
        self.assertEqual(s.expired, 1)
        self.assertEqual(s.rejected, 0)
        self.assertFalse(s.is_apto)

    def test_a_rejected_point_reports_rejected_not_expired(self):
        # El §7 lista Vencido y Rechazado como dos estados distintos de la fila,
        # y el §8.1 pide el conteo de vencidos en particular.
        p = self._base_diver()
        _upload(p, "b", VALID_FOR_EVERY_POINT, dictamenes=[("REJECTED", "DOCTOR")])
        for code in "cdefgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.state, DiverState.REJECTED)
        self.assertEqual(s.rejected, 1)
        self.assertEqual(s.expired, 0)
        self.assertEqual(s.problems, 1)
        self.assertFalse(s.is_apto)

    def test_a_rejection_outranks_an_expiry(self):
        # Precedencia: el rechazo trae un motivo que el buzo tiene que leer para
        # poder arreglarlo; "vencido" se explica solo.
        p = self._base_diver()
        _upload(p, "b", date(2025, 11, 19), dictamenes=[("APPROVED", "DOCTOR")])
        _upload(p, "c", VALID_FOR_EVERY_POINT, dictamenes=[("REJECTED", "DOCTOR")])
        for code in "defgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(_slot_of(s, "b").state, StudyState.EXPIRED)
        self.assertEqual(_slot_of(s, "c").state, StudyState.REJECTED)
        self.assertEqual(s.state, DiverState.REJECTED)
        self.assertEqual(s.expired, 1)
        self.assertEqual(s.rejected, 1)
        self.assertEqual(s.problems, 2)

    def test_an_invalid_date_alone_reports_expired(self):
        # DATE_INVALID se pliega en EXPIRED y no en REJECTED: un papel mal
        # fechado es, en la práctica, uno que no sirve para esta ventana.
        p = self._base_diver()
        _upload(p, "b", date(2027, 1, 15), dictamenes=[("APPROVED", "DOCTOR")])
        for code in "cdefgh":
            _upload(p, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(_slot_of(s, "b").state, StudyState.DATE_INVALID)
        self.assertEqual(s.state, DiverState.EXPIRED)
        self.assertEqual(s.expired, 1)
        self.assertEqual(s.rejected, 0)

    def test_a_diver_with_no_problem_counts_nothing_as_a_problem(self):
        s = fitness.diver_summary(self._diver_with_all_approved_by_doctor(), TODAY)
        self.assertEqual(s.problems, 0)
        self.assertEqual(s.expired, 0)
        self.assertEqual(s.rejected, 0)

    def test_a_missing_point_outranks_the_ones_awaiting_review(self):
        p = self._base_diver()
        for code in "bcdefg":
            _upload(p, code, VALID_FOR_EVERY_POINT)
        # h sin cargar: falta documentación antes de que haya algo que revisar.
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.state, DiverState.INCOMPLETE)
        self.assertEqual(s.pending_review, 6)

    def test_an_anexo_27_whose_window_is_still_closed_leaves_it_incomplete(self):
        # Todo aprobado menos el Anexo 27, que recién se puede presentar el
        # 21/10. El 3/10 el buzo no está apto, pero tampoco tiene un problema.
        p = self._base_diver()
        for code in "bcdefg":
            _upload(p, code, date(2026, 9, 20), dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, date(2026, 10, 3))
        self.assertEqual(_slot_of(s, "h").state, StudyState.BEFORE_WINDOW)
        self.assertEqual(s.state, DiverState.INCOMPLETE)
        self.assertFalse(s.is_apto)

    def test_without_a_window_the_summary_requires_and_counts_nothing(self):
        p = _diver(birth_year=1988)
        _upload(p, "b", VALID_FOR_EVERY_POINT, dictamenes=[("APPROVED", "DOCTOR")])
        s = fitness.diver_summary(p, TODAY)
        self.assertEqual(s.required_codes, ())
        self.assertEqual(s.presented, 0)
        self.assertEqual(s.approved, 0)
        self.assertEqual(_slot_of(s, "b").state, StudyState.NOT_REQUIRED)
        # La carga sigue estando a la vista aunque no haya contra qué medirla.
        self.assertIsNotNone(_slot_of(s, "b").block)


class RosterPerformanceTests(TestCase):
    """El médico ve los 150 buzos de una vez: el motor no puede consultar."""

    def _roster(self):
        return UserProfile.objects.select_related(
            "user", "habilitation_window"
        ).prefetch_related(
            Prefetch(
                "user__study_blocks",
                queryset=StudyBlock.objects.filter(is_current=True).prefetch_related(
                    Prefetch("comments", queryset=Comment.objects.order_by("created_at", "pk"))
                ),
            )
        )

    def test_a_prefetched_roster_computes_without_a_single_extra_query(self):
        window = _november_2026()
        for _ in range(3):
            p = _diver(birth_year=1988, window=window)
            for code in "bcdefgh":
                _upload(p, code, VALID_FOR_EVERY_POINT,
                        dictamenes=[("PRE_APPROVED", "NURSE"), ("APPROVED", "DOCTOR")])
        profiles = list(self._roster())
        self.assertEqual(len(profiles), 3)
        with self.assertNumQueries(0):
            states = [fitness.diver_summary(p, TODAY).state for p in profiles]
        self.assertEqual(states, [DiverState.APTO] * 3)
