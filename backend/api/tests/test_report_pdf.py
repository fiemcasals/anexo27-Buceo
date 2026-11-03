"""§6: el estudio reemplazado no es visible en la vista normal, tampoco en el PDF."""

from datetime import date
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from api import report_pdf
from api.models import StudyBlock


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
