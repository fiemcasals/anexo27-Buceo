"""El DNI se guarda sin puntos, comas ni espacios, por cualquier vía."""

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from users.dni import normalizar_dni
from users.models import UserProfile
from users.tests.test_registro_api import _registrar


class NormalizarTests(APITestCase):
    def test_saca_puntos_comas_y_espacios(self):
        self.assertEqual(normalizar_dni('30.123.456'), '30123456')
        self.assertEqual(normalizar_dni('30,123,456'), '30123456')
        self.assertEqual(normalizar_dni(' 30 123 456 '), '30123456')
        self.assertEqual(normalizar_dni('30.123,456'), '30123456')

    def test_none_y_vacio_pasan_tal_cual(self):
        self.assertIsNone(normalizar_dni(None))
        self.assertEqual(normalizar_dni(''), '')


class RegistroConPuntosTests(APITestCase):
    def test_el_registro_guarda_el_dni_sin_puntos(self):
        r = _registrar(dni='30.111.222')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(UserProfile.objects.get().dni, '30111222')

    def test_el_registro_guarda_el_dni_sin_comas_ni_espacios(self):
        r = _registrar(dni=' 30,111 222 ')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(UserProfile.objects.get().dni, '30111222')

    def test_un_dni_con_otro_formato_es_el_mismo_y_se_rechaza_por_repetido(self):
        self.assertEqual(_registrar(dni='30111222').status_code, 201)
        r = _registrar(email='otro@b.com', dni='30.111.222')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('dni', r.data)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_un_dni_que_son_solo_separadores_se_rechaza_como_vacio(self):
        r = _registrar(dni='. , .')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('dni', r.data)
        self.assertEqual(UserProfile.objects.count(), 0)

    def test_el_largo_maximo_se_mide_ya_limpio(self):
        # 20 dígitos con puntos: 26 caracteres escritos, 20 guardados.
        con_puntos = '.'.join(['1234'] * 5)
        r = _registrar(dni=con_puntos)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(UserProfile.objects.get().dni, '12341234123412341234')


class PerfilConPuntosTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='buzo', email='buzo@b.com')
        self.perfil = UserProfile.objects.create(user=self.user, role='USER')
        self.otro = UserProfile.objects.create(
            user=User.objects.create(username='otro'), role='USER', dni='20111222')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_corregir_el_dni_con_puntos_lo_guarda_limpio(self):
        r = self.client.patch('/api/profiles/me/', {'dni': '30.222.333'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.dni, '30222333')
        self.assertEqual(r.json()['dni'], '30222333')

    def test_el_dni_de_otro_con_puntos_se_rechaza_por_repetido(self):
        r = self.client.patch('/api/profiles/me/', {'dni': '20.111.222'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('dni', r.json())
        self.perfil.refresh_from_db()
        self.assertIsNone(self.perfil.dni)

    def test_quedarse_con_el_propio_dni_no_es_repetido(self):
        self.client.patch('/api/profiles/me/', {'dni': '30.222.333'}, format='json')
        r = self.client.patch('/api/profiles/me/', {'dni': '30.222.333'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_dejar_el_dni_en_blanco_sigue_guardando_null(self):
        r = self.client.patch('/api/profiles/me/', {'dni': ''}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.perfil.refresh_from_db()
        self.assertIsNone(self.perfil.dni)


class ElModeloTambienLimpiaTests(APITestCase):
    def test_guardar_desde_el_admin_o_el_shell_tambien_normaliza(self):
        perfil = UserProfile.objects.create(
            user=User.objects.create(username='x'), role='USER', dni='30.333.444')
        perfil.refresh_from_db()
        self.assertEqual(perfil.dni, '30333444')


class MigracionDeDnisExistentesTests(APITestCase):
    def test_limpia_los_que_tienen_puntos_y_respeta_los_que_chocarian(self):
        import importlib
        from django.apps import apps
        migracion = importlib.import_module('users.migrations.0011_dni_sin_puntos')
        # Se crean con update() para saltear la limpieza de save(): así quedan
        # como estaban en la base antes de este cambio.
        sucio = UserProfile.objects.create(
            user=User.objects.create(username='a'), role='USER')
        ya_limpio = UserProfile.objects.create(
            user=User.objects.create(username='b'), role='USER', dni='20111222')
        choca = UserProfile.objects.create(
            user=User.objects.create(username='c'), role='USER')
        UserProfile.objects.filter(pk=sucio.pk).update(dni='30.222.333')
        UserProfile.objects.filter(pk=choca.pk).update(dni='20.111.222')

        migracion.limpiar_dnis(apps, None)

        for p in (sucio, ya_limpio, choca):
            p.refresh_from_db()
        self.assertEqual(sucio.dni, '30222333')
        self.assertEqual(ya_limpio.dni, '20111222')
        self.assertEqual(choca.dni, '20.111.222')  # el limpio ya es de otro
