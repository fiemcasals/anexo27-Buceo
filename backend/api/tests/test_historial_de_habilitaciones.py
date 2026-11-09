"""El historial de a qué habilitaciones se anotó cada buzo: una fila por ciclo,
con la última fecha que eligió."""

import datetime

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import HabilitationEnrollment, HabilitationWindow
from users.models import UserProfile

URL = '/api/mi-fecha/'


def _ventana(ciclo, lugar, mes):
    return HabilitationWindow.objects.create(
        cycle=ciclo, slot=lugar, start_date=datetime.date(ciclo, mes, 10),
        end_date=datetime.date(ciclo, mes, 12))


class HistorialTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='buzo', email='b@b.com')
        UserProfile.objects.create(user=self.user, role='USER')
        self.primera = _ventana(2026, 'FIRST', 11)
        self.segunda = _ventana(2026, 'SECOND', 12)
        self.del_otro_anio = _ventana(2027, 'FIRST', 4)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def elegir(self, ventana):
        r = self.client.put(URL, {'window': None if ventana is None else ventana.pk},
                            format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_elegir_una_fecha_la_anota(self):
        self.elegir(self.primera)
        fila = HabilitationEnrollment.objects.get()
        self.assertEqual((fila.user, fila.cycle, fila.window), (self.user, 2026, self.primera))

    def test_cambiar_de_fecha_en_el_mismo_ciclo_deja_solo_la_ultima(self):
        self.elegir(self.primera)
        self.elegir(self.segunda)
        fila = HabilitationEnrollment.objects.get()  # una sola
        self.assertEqual(fila.window, self.segunda)

    def test_volver_a_elegir_la_misma_no_cambia_nada(self):
        self.elegir(self.primera)
        antes = HabilitationEnrollment.objects.get().chosen_at
        self.elegir(self.primera)
        self.assertEqual(HabilitationEnrollment.objects.count(), 1)
        self.assertEqual(HabilitationEnrollment.objects.get().chosen_at, antes)

    def test_un_ciclo_distinto_es_otra_fila(self):
        self.elegir(self.primera)
        self.elegir(self.del_otro_anio)
        self.assertEqual(
            sorted(HabilitationEnrollment.objects.values_list('cycle', flat=True)),
            [2026, 2027])

    def test_desinscribirse_no_borra_el_historial(self):
        self.elegir(self.primera)
        self.elegir(None)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.habilitation_window)
        self.assertEqual(HabilitationEnrollment.objects.get().window, self.primera)

    def test_cada_buzo_tiene_su_propio_historial(self):
        otro = User.objects.create(username='otro')
        UserProfile.objects.create(user=otro, role='USER')
        self.elegir(self.primera)
        cliente = APIClient()
        cliente.force_authenticate(otro)
        cliente.put(URL, {'window': self.segunda.pk}, format='json')
        self.assertEqual(HabilitationEnrollment.objects.get(user=self.user).window, self.primera)
        self.assertEqual(HabilitationEnrollment.objects.get(user=otro).window, self.segunda)

    def test_la_fecha_no_se_puede_borrar_si_alguien_se_anoto(self):
        from django.db.models import ProtectedError
        self.elegir(self.primera)
        self.elegir(self.segunda)  # el perfil ya no apunta a la primera...
        with self.assertRaises(ProtectedError):
            self.segunda.delete()  # ...pero la segunda consta en el historial


class MigracionInicialTests(APITestCase):
    def test_los_ya_inscriptos_entran_al_historial_una_sola_vez(self):
        import importlib
        from django.apps import apps
        migracion = importlib.import_module('api.migrations.0019_historial_inicial')
        ventana = _ventana(2026, 'FIRST', 11)
        user = User.objects.create(username='viejo')
        UserProfile.objects.create(user=user, role='USER', habilitation_window=ventana)
        User.objects.create(username='sin-fecha')
        UserProfile.objects.create(user=User.objects.get(username='sin-fecha'), role='USER')

        migracion.anotar_a_los_inscriptos(apps, None)
        migracion.anotar_a_los_inscriptos(apps, None)  # idempotente

        self.assertEqual(HabilitationEnrollment.objects.count(), 1)
        self.assertEqual(HabilitationEnrollment.objects.get().user, user)
