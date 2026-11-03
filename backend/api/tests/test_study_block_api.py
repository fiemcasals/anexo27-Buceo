"""Tests del endpoint de estudios: la vista normal no muestra el historial.

§6: el estudio reemplazado "no es visible en la vista normal". La rama creó la
distinción (`is_current`) y dejó al viewset sirviendo las dos cargas, la vigente
y la que reemplazó. El historial se pide aparte y a propósito.
"""

from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import Permission, StudyBlock

URL = "/api/blocks/"


class StudyBlockVisibilityTests(APITestCase):
    def setUp(self):
        self.diver = User.objects.create(username="buzo1")
        # La segunda carga degrada a la primera: queda una vigente y un
        # historial, que es lo que pasa cuando el buzo reemplaza un estudio.
        self.replaced = StudyBlock.objects.create(
            user=self.diver, study_code="d", study_date=date(2026, 8, 1))
        self.current = StudyBlock.objects.create(
            user=self.diver, study_code="d", study_date=date(2026, 10, 30))
        self.client = APIClient()
        self.client.force_authenticate(self.diver)

    def _ids(self, query=""):
        response = self.client.get(f"{URL}{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()}

    def test_the_fixture_really_has_one_current_and_one_replaced(self):
        self.replaced.refresh_from_db()
        self.assertFalse(self.replaced.is_current)
        self.assertTrue(self.current.is_current)

    def test_the_normal_view_serves_only_the_current_upload(self):
        self.assertEqual(self._ids(), {self.current.pk})

    def test_the_history_can_be_asked_for_explicitly(self):
        # Sin pantalla ninguna: el plan 2 la va a necesitar.
        self.assertEqual(self._ids("?historico=1"),
                         {self.current.pk, self.replaced.pk})

    def test_any_other_value_of_the_parameter_keeps_the_normal_view(self):
        for query in ("?historico=0", "?historico=", "?historico=si",
                      "?otro=1"):
            with self.subTest(query=query):
                self.assertEqual(self._ids(query), {self.current.pk})

    def test_a_point_with_a_single_current_upload_is_served_either_way(self):
        only = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 9, 1))
        self.assertIn(only.pk, self._ids())
        self.assertIn(only.pk, self._ids("?historico=1"))

    def test_another_divers_uploads_are_not_served(self):
        someone_else = User.objects.create(username="buzo2")
        theirs = StudyBlock.objects.create(
            user=someone_else, study_code="b", study_date=date(2026, 9, 1))
        self.assertNotIn(theirs.pk, self._ids())
        self.assertNotIn(theirs.pk, self._ids("?historico=1"))

    def test_a_shared_history_is_filtered_the_same_way(self):
        # El filtro no se puede escapar por la rama de lo compartido.
        reviewer = User.objects.create(username="medico")
        Permission.objects.create(
            grantor=self.diver, grantee=reviewer,
            access_level="VIEW", shared_items=["ALL"])
        client = APIClient()
        client.force_authenticate(reviewer)
        response = client.get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual({row["id"] for row in response.json()},
                         {self.current.pk})
        response = client.get(f"{URL}?historico=1")
        self.assertEqual({row["id"] for row in response.json()},
                         {self.current.pk, self.replaced.pk})
