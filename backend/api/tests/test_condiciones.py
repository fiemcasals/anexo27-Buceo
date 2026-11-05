"""Condiciones de uso: la fecha de aceptacion se sella una sola vez, en el perfil.

Es una constancia, no una preferencia: por eso es fecha y no booleano, y por eso
no se puede escribir con un PATCH del perfil.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import UserProfile


class CondicionesTests(TestCase):
    def setUp(self):
        self.buzo = User.objects.create_user(
            username='buzo@ejemplo.com', email='buzo@ejemplo.com', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.buzo)

    def test_arranca_sin_aceptar(self):
        r = self.client.get('/api/profiles/me/')

        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data['terms_accepted_at'])

    def test_aceptar_sella_la_fecha(self):
        r = self.client.post('/api/profiles/accept-terms/')

        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data['terms_accepted_at'])
        self.assertIsNotNone(
            UserProfile.objects.get(user=self.buzo).terms_accepted_at)

    def test_aceptar_de_nuevo_no_rompe(self):
        self.client.post('/api/profiles/accept-terms/')
        primera = UserProfile.objects.get(user=self.buzo).terms_accepted_at

        r = self.client.post('/api/profiles/accept-terms/')

        self.assertEqual(r.status_code, 200)
        # Se vuelve a sellar: lo que importa es que no falle ni se pierda.
        self.assertGreaterEqual(
            UserProfile.objects.get(user=self.buzo).terms_accepted_at, primera)

    def test_no_se_puede_antedatar_con_un_patch_del_perfil(self):
        """Si fuera escribible, aceptar y la constancia serian la misma accion."""
        r = self.client.patch('/api/profiles/me/',
                              {'terms_accepted_at': '2020-01-01T00:00:00Z'},
                              format='json')

        self.assertEqual(r.status_code, 200)
        self.assertIsNone(
            UserProfile.objects.get(user=self.buzo).terms_accepted_at)

    def test_sin_sesion_no_se_puede_aceptar(self):
        r = APIClient().post('/api/profiles/accept-terms/')

        self.assertEqual(r.status_code, 401)
