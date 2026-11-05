"""`correo.avisar_rechazo`: qué dice el aviso y que nunca propaga."""

from datetime import date
from smtplib import SMTPException
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from api import correo
from api.models import Comment, StudyBlock


class AvisarRechazoTests(TestCase):
    def setUp(self):
        self.diver = User.objects.create(
            username="buzo1", email="buzo1@example.com")
        self.doctor = User.objects.create(username="medico")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.comment = Comment.objects.create(
            block=self.block, doctor=self.doctor, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="OUT_OF_TERM",
            content="Pasaron más de seis meses.")

    def test_devuelve_true_y_manda_un_correo(self):
        self.assertTrue(correo.avisar_rechazo(self.comment))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Estudio fuera del plazo", mail.outbox[0].body)

    def test_el_correo_caido_da_false_y_no_propaga(self):
        with mock.patch("api.correo.send_mail", side_effect=SMTPException):
            self.assertFalse(correo.avisar_rechazo(self.comment))

    def test_cualquier_excepcion_da_false(self):
        with mock.patch("api.correo.send_mail", side_effect=OSError):
            self.assertFalse(correo.avisar_rechazo(self.comment))

    def test_sin_correo_del_buzo_da_false_y_no_manda(self):
        self.diver.email = ""
        self.diver.save()
        self.assertFalse(correo.avisar_rechazo(self.comment))
        self.assertEqual(len(mail.outbox), 0)
