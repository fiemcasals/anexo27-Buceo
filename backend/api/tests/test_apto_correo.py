"""El aviso de "estás apto": sale cuando una aprobación completa los estudios
exigidos, y solo en ese cambio."""

from unittest import mock

from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from api import correo, fitness
from api.models import Comment, StudyBlock
from api.tests.test_fitness import TODAY, VALID_FOR_EVERY_POINT, _diver, _november_2026
from api.tests.test_dictamen import _revisor


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AvisoDeAptoTests(APITestCase):
    def setUp(self):
        patcher = mock.patch("api.serializers.hoy", return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.medico = _revisor("medico", "DOCTOR")
        self.perfil = _diver(1988, window=_november_2026())
        self.perfil.user.email = "buzo@example.com"
        self.perfil.user.save()
        self.codigos = fitness.required_codes(self.perfil)
        self.bloques = [
            StudyBlock.objects.create(
                user=self.perfil.user, study_code=c, study_date=VALID_FOR_EVERY_POINT)
            for c in self.codigos
        ]

    def _aprobar(self, bloque):
        cliente = APIClient()
        cliente.force_authenticate(self.medico)
        return cliente.post(
            "/api/comments/", {"block": bloque.pk, "status": "APPROVED"}, format="json")

    def _asuntos(self):
        return [m.subject for m in mail.outbox]

    def test_la_ultima_aprobacion_avisa_que_esta_apto(self):
        for bloque in self.bloques[:-1]:
            self.assertEqual(self._aprobar(bloque).status_code, 201)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self._aprobar(self.bloques[-1]).status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["buzo@example.com"])
        self.assertIn("apto", mail.outbox[0].subject)

    def test_una_aprobacion_que_no_completa_no_avisa(self):
        self._aprobar(self.bloques[0])
        self.assertEqual(len(mail.outbox), 0)

    def test_un_correo_caido_no_impide_el_dictamen(self):
        for bloque in self.bloques[:-1]:
            self._aprobar(bloque)
        with mock.patch("api.correo.send_mail", side_effect=OSError):
            r = self._aprobar(self.bloques[-1])
        self.assertEqual(r.status_code, 201)

    def test_sin_correo_del_buzo_no_manda_ni_falla(self):
        self.perfil.user.email = ""
        self.assertFalse(correo.avisar_apto(self.perfil.user))
        self.assertEqual(len(mail.outbox), 0)
