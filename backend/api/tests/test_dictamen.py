from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from api import fitness
from api.fitness import StudyState
from api.models import Comment, StudyBlock
from api.tests.test_fitness import (
    TODAY, VALID_FOR_EVERY_POINT, _diver, _november_2026,
)
from users.models import UserProfile


class DictamenTests(TestCase):
    def setUp(self):
        self.reviewer = User.objects.create(username="medico")
        self.block = StudyBlock.objects.create(
            user=User.objects.create(username="buzo1"),
            study_code="f", study_date=date(2026, 10, 18),
        )

    def _dictamen(self, **kwargs):
        return Comment(block=self.block, doctor=self.reviewer, **kwargs)

    def _errors(self, dictamen):
        with self.assertRaises(ValidationError) as ctx:
            dictamen.full_clean()
        return ctx.exception.message_dict

    def test_the_four_rejection_reasons_are_the_directive_ones(self):
        self.assertEqual(
            [key for key, _ in Comment.REJECTION_REASONS],
            ["OUT_OF_TERM", "UNFIT_VALUES", "ILLEGIBLE", "OTHER"],
        )
        self.assertEqual(
            [label for _, label in Comment.REJECTION_REASONS],
            ["Estudio fuera del plazo de la directiva",
             "Valores no aptos para realizar la actividad",
             "Documento ilegible",
             "Otros"],
        )

    def test_status_choices_are_the_verdicts(self):
        self.assertEqual(
            dict(Comment.STATUS_CHOICES),
            {"PRE_APPROVED": "Pre-revisado", "APPROVED": "Aprobado",
             "REJECTED": "Rechazado con Observación",
             "REVERTED": "Aprobación revertida"},
        )

    def test_reviewer_role_is_doctor_or_nurse(self):
        self.assertEqual(
            [key for key, _ in Comment.REVIEWER_ROLES], ["DOCTOR", "NURSE"]
        )
        errors = self._errors(self._dictamen(status="APPROVED", reviewer_role="ADMIN"))
        self.assertEqual(list(errors), ["reviewer_role"])

    def test_a_rejection_needs_a_reason(self):
        errors = self._errors(self._dictamen(
            status="REJECTED", reviewer_role="NURSE",
            content="La foto salió cortada.", rejection_reason="",
        ))
        self.assertEqual(list(errors), ["rejection_reason"])

    def test_a_rejection_needs_a_detail_for_the_diver(self):
        errors = self._errors(self._dictamen(
            status="REJECTED", reviewer_role="NURSE",
            content="", rejection_reason="ILLEGIBLE",
        ))
        self.assertEqual(list(errors), ["content"])

    def test_a_valid_rejection_passes(self):
        self._dictamen(
            status="REJECTED", reviewer_role="NURSE",
            content="La fotografía está cortada.", rejection_reason="ILLEGIBLE",
        ).full_clean()

    def test_an_approval_cannot_carry_a_rejection_reason(self):
        errors = self._errors(self._dictamen(
            status="APPROVED", reviewer_role="DOCTOR",
            rejection_reason="ILLEGIBLE",
        ))
        self.assertEqual(list(errors), ["rejection_reason"])

    def test_a_pre_approval_cannot_carry_a_rejection_reason(self):
        errors = self._errors(self._dictamen(
            status="PRE_APPROVED", reviewer_role="NURSE",
            rejection_reason="OTHER",
        ))
        self.assertEqual(list(errors), ["rejection_reason"])

    def test_an_approval_needs_no_comment(self):
        self._dictamen(status="APPROVED", reviewer_role="DOCTOR").full_clean()

    def test_a_dictamen_records_who_and_with_what_role(self):
        d = self._dictamen(status="PRE_APPROVED", reviewer_role="NURSE")
        d.full_clean()
        d.save()
        self.assertEqual(d.doctor, self.reviewer)
        self.assertEqual(d.reviewer_role, "NURSE")
        self.assertIsNotNone(d.created_at)

    def test_a_dictamen_without_reviewer_role_is_refused(self):
        errors = self._errors(self._dictamen(status="APPROVED"))
        self.assertEqual(list(errors), ["reviewer_role"])

    def test_a_dictamen_without_status_is_refused(self):
        errors = self._errors(self._dictamen(reviewer_role="DOCTOR"))
        self.assertEqual(list(errors), ["status"])

    def test_a_nurse_cannot_approve(self):
        errors = self._errors(self._dictamen(status="APPROVED", reviewer_role="NURSE"))
        self.assertEqual(list(errors), ["status"])

    def test_a_doctor_cannot_pre_approve(self):
        errors = self._errors(self._dictamen(status="PRE_APPROVED", reviewer_role="DOCTOR"))
        self.assertEqual(list(errors), ["status"])

    # --- §15.9: nadie dictamina sobre sus propios estudios --------------------

    def _own_study_dictamen(self, **kwargs):
        """Dictamen de un revisor sobre un estudio suyo.

        El médico de la unidad es uno solo y puede ser además buzo: entonces
        firma sus propios estudios y el motor lo reporta APTO.
        """
        own = StudyBlock.objects.create(
            user=self.reviewer, study_code="b", study_date=date(2026, 10, 18),
        )
        return Comment(block=own, doctor=self.reviewer, **kwargs)

    def test_nobody_may_rule_on_their_own_study(self):
        errors = self._errors(self._own_study_dictamen(
            status="APPROVED", reviewer_role="DOCTOR",
        ))
        # Sólo este error: el resto del dictamen es válido, así que el test no
        # puede pasar por un campo obligatorio ajeno a la regla.
        self.assertEqual(list(errors), ["doctor"])
        self.assertEqual(
            errors["doctor"], ["Nadie puede dictaminar sobre sus propios estudios."]
        )

    def test_a_nurse_may_not_pre_approve_their_own_study_either(self):
        errors = self._errors(self._own_study_dictamen(
            status="PRE_APPROVED", reviewer_role="NURSE",
        ))
        self.assertEqual(list(errors), ["doctor"])

    def test_rejecting_ones_own_study_is_refused_too(self):
        errors = self._errors(self._own_study_dictamen(
            status="REJECTED", reviewer_role="DOCTOR",
            content="Ilegible.", rejection_reason="ILLEGIBLE",
        ))
        self.assertEqual(list(errors), ["doctor"])

    def test_ruling_on_someone_elses_study_stays_allowed(self):
        # El contrapunto: la regla no puede bloquear el caso normal.
        self._dictamen(status="APPROVED", reviewer_role="DOCTOR").full_clean()

    def test_either_role_may_reject(self):
        for role in ("DOCTOR", "NURSE"):
            self._dictamen(
                status="REJECTED", reviewer_role=role,
                content="Falta la firma.", rejection_reason="OTHER",
            ).full_clean()


class DictamenDatabaseConstraintTests(TestCase):
    """objects.create() skips clean(); only the database can refuse these."""

    def setUp(self):
        self.reviewer = User.objects.create(username="medico")
        self.block = StudyBlock.objects.create(
            user=User.objects.create(username="buzo1"),
            study_code="f", study_date=date(2026, 10, 18),
        )

    def _assert_refused_by(self, constraint_name, **kwargs):
        with self.assertRaises(IntegrityError) as ctx, transaction.atomic():
            Comment.objects.create(block=self.block, doctor=self.reviewer, **kwargs)
        self.assertIn(constraint_name, str(ctx.exception))

    def test_a_nurse_cannot_write_an_approval(self):
        self._assert_refused_by(
            "verdict_matches_reviewer_role",
            status="APPROVED", reviewer_role="NURSE",
        )

    def test_a_doctor_cannot_write_a_pre_approval(self):
        self._assert_refused_by(
            "verdict_matches_reviewer_role",
            status="PRE_APPROVED", reviewer_role="DOCTOR",
        )

    def test_a_rejection_without_reason_is_refused(self):
        self._assert_refused_by(
            "rejection_has_reason_and_detail",
            status="REJECTED", reviewer_role="NURSE", content="Ilegible.",
        )

    def test_a_rejection_without_detail_is_refused(self):
        self._assert_refused_by(
            "rejection_has_reason_and_detail",
            status="REJECTED", reviewer_role="DOCTOR", rejection_reason="OTHER",
        )

    def test_an_approval_with_a_reason_is_refused(self):
        self._assert_refused_by(
            "rejection_has_reason_and_detail",
            status="APPROVED", reviewer_role="DOCTOR", rejection_reason="OTHER",
        )

    def test_the_legal_combinations_are_stored(self):
        for status, role, extra in [
            ("APPROVED", "DOCTOR", {}),
            ("PRE_APPROVED", "NURSE", {}),
            ("REJECTED", "NURSE", {"content": "x", "rejection_reason": "OTHER"}),
            ("REJECTED", "DOCTOR", {"content": "x", "rejection_reason": "OTHER"}),
        ]:
            Comment.objects.create(
                block=self.block, doctor=self.reviewer,
                status=status, reviewer_role=role, **extra,
            )
        self.assertEqual(Comment.objects.count(), 4)


def _revisor(username, role):
    user = User.objects.create(username=username)
    UserProfile.objects.create(user=user, role=role)
    return user


class RevertirAprobacionTests(APITestCase):
    """El médico deshace una aprobación que firmó él, y queda asentado.

    Sin esto una aprobación equivocada deja al buzo apto hasta que venza: el
    buzo no puede reemplazar lo aprobado (`fitness.puede_reemplazarse`) y la
    ficha no ofrece ninguna acción. Revertir no borra el dictamen: agrega uno
    nuevo (`REVERTED`) con su autor y su fecha, porque el último manda.
    """

    CODE = "b"

    def setUp(self):
        self.medico = _revisor("medico", "DOCTOR")
        self.otro_medico = _revisor("otro_medico", "DOCTOR")
        self.enfermero = _revisor("enfermero", "NURSE")
        self.perfil = _diver(1988, window=_november_2026())
        self.bloque = StudyBlock.objects.create(
            user=self.perfil.user, study_code=self.CODE,
            study_date=VALID_FOR_EVERY_POINT)
        self.aprobacion_del_medico = Comment.objects.create(
            block=self.bloque, doctor=self.medico, reviewer_role="DOCTOR",
            status="APPROVED")

    def revertir(self, usuario, dictamen):
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return cliente.post(f"/api/comments/{dictamen.pk}/revertir/")

    def dictamenes_del_punto(self):
        return Comment.objects.filter(block=self.bloque).order_by("created_at", "pk")

    def estado_del_punto(self):
        perfil = UserProfile.objects.get(pk=self.perfil.pk)
        resumen = fitness.diver_summary(perfil, TODAY)
        return next(s for s in resumen.slots if s.code == self.CODE).state

    def test_el_punto_arranca_aprobado(self):
        # El contrapunto de los demás: sin esto "queda en IN_REVIEW" podría ser
        # el estado de partida.
        self.assertEqual(self.estado_del_punto(), StudyState.APPROVED)

    def test_el_medico_revierte_su_propia_aprobacion(self):
        r = self.revertir(self.medico, self.aprobacion_del_medico)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.estado_del_punto(), StudyState.IN_REVIEW)

    def test_revertida_el_buzo_puede_volver_a_subir(self):
        self.revertir(self.medico, self.aprobacion_del_medico)
        self.assertTrue(fitness.puede_reemplazarse(
            self.CODE, StudyBlock.objects.get(pk=self.bloque.pk),
            self.perfil.habilitation_window, TODAY))

    def test_queda_asentado_quien_revirtio_y_cuando(self):
        self.revertir(self.medico, self.aprobacion_del_medico)
        self.assertEqual(self.dictamenes_del_punto().count(), 2)
        ultimo = self.dictamenes_del_punto().last()
        self.assertNotEqual(ultimo.pk, self.aprobacion_del_medico.pk)
        self.assertEqual(ultimo.status, "REVERTED")
        self.assertEqual(ultimo.doctor, self.medico)
        self.assertEqual(ultimo.reviewer_role, "DOCTOR")
        self.assertIsNotNone(ultimo.created_at)

    def test_la_aprobacion_original_no_se_toca(self):
        self.revertir(self.medico, self.aprobacion_del_medico)
        self.aprobacion_del_medico.refresh_from_db()
        self.assertEqual(self.aprobacion_del_medico.status, "APPROVED")

    def test_el_enfermero_no_revierte_una_aprobacion_del_medico(self):
        self.assertEqual(self.revertir(self.enfermero, self.aprobacion_del_medico)
                         .status_code, 403)
        self.assertEqual(self.estado_del_punto(), StudyState.APPROVED)
        self.assertEqual(self.dictamenes_del_punto().count(), 1)

    def test_otro_medico_no_revierte_lo_que_no_aprobo(self):
        self.assertEqual(self.revertir(self.otro_medico, self.aprobacion_del_medico)
                         .status_code, 403)
        self.assertEqual(self.estado_del_punto(), StudyState.APPROVED)
        self.assertEqual(self.dictamenes_del_punto().count(), 1)

    def test_el_buzo_no_revierte_su_propia_aprobacion(self):
        # No ve el dictamen de otro sobre un estudio ajeno, pero sí el de los
        # suyos: ahí el 403 lo da la regla.
        r = self.revertir(self.perfil.user, self.aprobacion_del_medico)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.estado_del_punto(), StudyState.APPROVED)

    def test_solo_se_revierte_una_aprobacion(self):
        rechazo = Comment.objects.create(
            block=self.bloque, doctor=self.medico, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="OTHER", content="Mal.")
        r = self.revertir(self.medico, rechazo)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self.dictamenes_del_punto().count(), 2)

    def test_no_se_revierte_dos_veces(self):
        self.revertir(self.medico, self.aprobacion_del_medico)
        r = self.revertir(self.medico, self.aprobacion_del_medico)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self.dictamenes_del_punto().count(), 2)

    def test_no_se_revierte_una_aprobacion_ya_superada(self):
        # Si después hubo otro dictamen, la aprobación ya no es la que manda.
        Comment.objects.create(
            block=self.bloque, doctor=self.medico, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="OTHER", content="Mal.")
        r = self.revertir(self.medico, self.aprobacion_del_medico)
        self.assertEqual(r.status_code, 400, r.content)

    def test_no_se_fabrica_una_reversion_por_la_via_comun(self):
        # REVERTED sólo sale de la acción: por POST común (o un PATCH, que ya no existe) deshacería una
        # aprobación sin pasar por las reglas de arriba.
        cliente = APIClient()
        cliente.force_authenticate(self.medico)
        r = cliente.post("/api/comments/", {
            "block": self.bloque.pk, "status": "REVERTED"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        r = cliente.patch(f"/api/comments/{self.aprobacion_del_medico.pk}/",
                          {"status": "REVERTED"}, format="json")
        self.assertEqual(r.status_code, 405, r.content)
        self.assertEqual(self.estado_del_punto(), StudyState.APPROVED)
