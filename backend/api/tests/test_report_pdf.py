"""§6: el estudio reemplazado no es visible en la vista normal, tampoco en el PDF.

Y cómo imprime el formulario oficial cada dictamen. `PRE_APPROVED` y el rol
`NURSE` los introdujo esta rama, y el Anexo 27 no tenía rama para ninguno de los
dos: imprimía la pre-aprobación del enfermero como "RECHAZADO", en rojo, en el
documento que firma un oficial, y le atribuía al médico lo que había dictaminado
un enfermero auxiliar.
"""

from datetime import date
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from reportlab.lib import colors

from api import report_pdf
from api.models import Comment, StudyBlock


class Anexo27ReportTests(TestCase):
    def test_the_report_lists_only_the_current_upload(self):
        diver = User.objects.create(username="buzo1")
        StudyBlock.objects.create(
            user=diver, study_code="d", study_date=date(2026, 8, 1))
        StudyBlock.objects.create(
            user=diver, study_code="d", study_date=date(2026, 10, 30))
        with mock.patch.object(report_pdf.canvas, "Canvas") as canvas_cls:
            report_pdf.generate_anexo_27(BytesIO(), diver)
        drawn = [c.args[2] for c in canvas_cls.return_value.drawString.call_args_list]
        self.assertTrue(any("2026-10-30" in t for t in drawn), drawn)
        self.assertFalse(any("2026-08-01" in t for t in drawn), drawn)


class Anexo27VerdictLineTests(TestCase):
    """El renglón del dictamen: su texto, su color y a quién se lo atribuye."""

    def setUp(self):
        self.diver = User.objects.create(username="buzo1")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="d", study_date=date(2026, 10, 30))

    def _render(self, **verdict):
        Comment.objects.create(block=self.block, **verdict)
        with mock.patch.object(report_pdf.canvas, "Canvas") as canvas_cls:
            report_pdf.generate_anexo_27(BytesIO(), self.diver)
        drawn = [c.args[2]
                 for c in canvas_cls.return_value.drawString.call_args_list]
        painted = [c.args[0]
                   for c in canvas_cls.return_value.setFillColor.call_args_list]
        # El renglón del dictamen abre con el corchete del estado y cierra con
        # los dos puntos; "[Firma Digital Verificada]" también abre con uno.
        lines = [t for t in drawn if t.startswith("[") and t.endswith(":")]
        return lines, painted

    def test_a_nurse_pre_approval_is_not_printed_as_a_rejection(self):
        nurse = User.objects.create(username="enfermero1")
        lines, painted = self._render(
            doctor=nurse, reviewer_role="NURSE", status="PRE_APPROVED")
        self.assertEqual(lines, ["[PRE-REVISADO] Enfermero auxiliar (enfermero1):"])
        # Las dos direcciones: aparece lo suyo y no aparece su opuesto.
        self.assertNotIn("RECHAZADO", "".join(lines))
        self.assertIn(colors.orange, painted)
        self.assertNotIn(colors.red, painted)

    def test_the_doctors_approval_keeps_its_text_and_its_green(self):
        doctor = User.objects.create(username="medico1")
        lines, painted = self._render(
            doctor=doctor, reviewer_role="DOCTOR", status="APPROVED")
        self.assertEqual(lines, ["[APROBADO] Médico (medico1):"])
        self.assertIn(colors.green, painted)

    def test_a_nurse_rejection_is_a_rejection_but_is_not_the_doctors_word(self):
        # El rechazo del enfermero sí es definitivo (§6), pero el formulario no
        # puede decir que lo firmó el médico.
        nurse = User.objects.create(username="enfermero1")
        lines, painted = self._render(
            doctor=nurse, reviewer_role="NURSE", status="REJECTED",
            rejection_reason="ILLEGIBLE", content="Ilegible.")
        self.assertEqual(lines, ["[RECHAZADO] Enfermero auxiliar (enfermero1):"])
        self.assertIn(colors.red, painted)

    def test_the_reviewer_label_comes_from_the_role_not_from_the_status(self):
        # Mismo dictamen, dos roles: el renglón tiene que distinguirlos. Hacen
        # falta los dos en el mismo caso — con la etiqueta fija en "Médico", uno
        # solo seguía coincidiendo y el test no podía fallar.
        doctor = User.objects.create(username="medico1")
        nurse = User.objects.create(username="enfermero1")
        Comment.objects.create(
            block=self.block, doctor=doctor, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="OTHER",
            content="Falta el sello.")
        lines, _ = self._render(
            doctor=nurse, reviewer_role="NURSE", status="REJECTED",
            rejection_reason="ILLEGIBLE", content="Ilegible.")
        self.assertEqual(lines, ["[RECHAZADO] Médico (medico1):",
                                 "[RECHAZADO] Enfermero auxiliar (enfermero1):"])
