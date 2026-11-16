"""La observación del médico o del enfermero: una nota que le llega al buzo por
correo aunque el estudio esté apto, y que no toca ningún dictamen."""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from api.models import Comment, Observacion, StudyBlock
from users.models import UserProfile

URL = "/api/observaciones/"


def _user(username, role, email=""):
    user = User.objects.create(username=username, email=email)
    UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ObservacionTests(APITestCase):
    def setUp(self):
        self.buzo = _user("buzo1", "USER", "buzo1@example.com")
        self.medico = _user("medico", "DOCTOR")
        self.enfermero = _user("enfermero", "NURSE")
        self.bloque = StudyBlock.objects.create(
            user=self.buzo, study_code="b", study_date=date(2026, 10, 1))
        Comment.objects.create(
            block=self.bloque, doctor=self.medico, reviewer_role="DOCTOR",
            status="APPROVED")

    def _crear(self, usuario, contenido="Repetir en 6 meses."):
        return _client(usuario).post(
            URL, {"block": self.bloque.pk, "content": contenido}, format="json")

    def test_el_medico_deja_una_observacion_sobre_un_estudio_apto_y_le_llega_al_buzo(self):
        r = self._crear(self.medico)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Observacion.objects.get().reviewer_role, "DOCTOR")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["buzo1@example.com"])
        self.assertIn("Repetir en 6 meses.", mail.outbox[0].body)

    def test_el_enfermero_tambien_puede(self):
        r = self._crear(self.enfermero)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Observacion.objects.get().reviewer_role, "NURSE")

    def test_no_cambia_el_dictamen_vigente(self):
        self._crear(self.medico)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.get().status, "APPROVED")

    def test_un_buzo_no_puede_dejar_observaciones(self):
        otro = _user("buzo2", "USER")
        r = self._crear(otro)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Observacion.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_nadie_opina_sobre_sus_propios_estudios(self):
        propio = StudyBlock.objects.create(
            user=self.medico, study_code="a", study_date=date(2026, 10, 1))
        r = _client(self.medico).post(
            URL, {"block": propio.pk, "content": "x"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_una_observacion_vacia_se_rechaza(self):
        r = self._crear(self.medico, "   ")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Observacion.objects.count(), 0)

    def test_si_el_correo_falla_la_observacion_queda_guardada(self):
        with mock.patch("api.correo.send_mail", side_effect=OSError("caído")):
            r = self._crear(self.medico)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Observacion.objects.count(), 1)

    def test_sin_correo_cargado_se_guarda_y_no_se_manda_nada(self):
        self.buzo.email = ""
        self.buzo.save()
        r = self._crear(self.medico)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(mail.outbox), 0)
