from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from api.models import Comment, StudyBlock


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

    def test_status_choices_are_the_three_verdicts(self):
        self.assertEqual(
            dict(Comment.STATUS_CHOICES),
            {"PRE_APPROVED": "Pre-revisado", "APPROVED": "Aprobado",
             "REJECTED": "Rechazado con Observación"},
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
