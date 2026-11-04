"""Quién puede emitir el Anexo 27 de un buzo.

El endpoint decidía por `is_staff`, que es la llave del admin de Django y no
tiene nada que ver con el §5. Las dos consecuencias iban contra el diseño, y la
primera es la que importa: **el médico designado recibía 403** sobre el
formulario que el sistema existe para producir. Es el tercer endpoint que sirve
el registro médico —y el que lo sirve como el documento que firma un oficial— y
fue el único de los tres que el cierre del plan 1 no convirtió al acceso por rol.

El acceso del admin (`is_staff`) se conserva a propósito: D-1 deja el admin de
Django como acceso crudo y salida de emergencia hasta que exista su pantalla
propia, así que ya ve los estudios y los dictámenes. Negarle este endpoint
mientras el panel sirve los mismos datos no protegería nada.

No había ningún test de acceso sobre este endpoint.
"""

from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from users.models import UserProfile


def _user(username, role=None, is_staff=False):
    user = User.objects.create(username=username, is_staff=is_staff)
    if role is not None:
        UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class QuienEmiteElAnexo27Tests(APITestCase):
    def setUp(self):
        self.diver = _user("buzo1", "USER")

    def _url(self, user=None):
        return f"/api/anexo27/{(user or self.diver).pk}/"

    def _assert_pdf(self, response):
        self.assertEqual(response.status_code, 200, response.content[:200])
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_the_designated_doctor_can_emit_a_divers_anexo_27(self):
        # §5: el médico "ve los estudios de todos". Antes recibía 403 — no es
        # dueño del legajo y no tiene `is_staff`.
        self._assert_pdf(_client(_user("medico", "DOCTOR")).get(self._url()))

    def test_a_designated_nurse_can_emit_it_too(self):
        # §5: el enfermero auxiliar "ve los estudios de todos los buzos". Misma
        # base que `StudyBlockViewSet` y `CommentViewSet`.
        self._assert_pdf(_client(_user("enfermero", "NURSE")).get(self._url()))

    def test_the_diver_can_still_get_their_own(self):
        self._assert_pdf(_client(self.diver).get(self._url()))

    def test_a_plain_diver_cannot_get_another_divers_anexo_27(self):
        other = _user("buzo2", "USER")
        response = _client(other).get(self._url())
        self.assertEqual(response.status_code, 403, response.content[:200])

    def test_a_user_without_a_profile_cannot_get_it_and_does_not_500(self):
        # La falta de perfil nunca puede querer decir "ve todo".
        response = _client(_user("nadie")).get(self._url())
        self.assertEqual(response.status_code, 403, response.content[:200])

    def test_the_admin_keeps_their_raw_access(self):
        # D-1: el admin de Django se conserva como acceso crudo hasta que su
        # pantalla propia exista. Ya ve los estudios y los dictámenes por ahí.
        self._assert_pdf(
            _client(_user("admin", "ADMIN", is_staff=True)).get(self._url()))

    def test_an_unknown_user_id_is_404_and_not_a_500(self):
        # `User.objects.get(pk=pk)` propagaba `DoesNotExist`, que con DEBUG=True
        # devuelve un traceback.
        response = _client(_user("medico", "DOCTOR")).get("/api/anexo27/99999/")
        self.assertEqual(response.status_code, 404, response.content[:200])
