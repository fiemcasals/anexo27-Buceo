"""Inscripción del buzo a una fecha de habilitación (§4.1).

Los estudios valen sólo si cubren el rango de la fecha elegida, así que esta
elección es la que le da sentido al resto. Las fechas publicadas son de sólo
lectura acá: cargarlas es de otro plan.

`hoy` se fija en 2026-11-04 para que los casos de "ya pasó" y "no pasó" no
dependan del día en que corra la suite.
"""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import HabilitationWindow
from users.models import UserProfile

HOY = date(2026, 11, 4)


def _user(username, role=None):
    user = User.objects.create(username=username)
    if role is not None:
        UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _fecha(slot, inicio, fin, ciclo=None):
    inicio = date.fromisoformat(inicio)
    return HabilitationWindow.objects.create(
        cycle=ciclo or inicio.year, slot=slot,
        start_date=inicio, end_date=date.fromisoformat(fin))


class _ConBuzo(APITestCase):
    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=HOY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.buzo = _user('buzo1', 'USER')
        self.perfil = self.buzo.profile
        self.otro = _user('buzo2', 'USER')
        self.perfil_del_otro = self.otro.profile


class LasFechasPublicadasTests(_ConBuzo):
    def test_las_fechas_salen_ordenadas_por_inicio(self):
        _fecha(slot='SECOND', inicio='2026-12-10', fin='2026-12-12')
        _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        datos = _client(self.buzo).get('/api/fechas/').data
        self.assertEqual([f['slot'] for f in datos], ['FIRST', 'SECOND'])

    def test_un_ciclo_incompleto_devuelve_solo_las_que_existen(self):
        # 4.1: el ciclo incompleto es el estado normal
        _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        self.assertEqual(len(_client(self.buzo).get('/api/fechas/').data), 1)

    def test_una_fecha_que_ya_paso_viene_marcada(self):
        _fecha(slot='FIRST', inicio='2026-01-10', fin='2026-01-12')
        self.assertTrue(_client(self.buzo).get('/api/fechas/').data[0]['ya_paso'])

    def test_una_fecha_futura_no_viene_marcada_y_trae_su_nombre(self):
        _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        dato = _client(self.buzo).get('/api/fechas/').data[0]
        self.assertFalse(dato['ya_paso'])
        self.assertEqual(dato['slot_display'], '1.ª fecha')

    def test_una_fecha_cuyo_ultimo_dia_es_hoy_no_ha_pasado(self):
        _fecha(slot='FIRST', inicio='2026-11-02', fin='2026-11-04')
        self.assertFalse(_client(self.buzo).get('/api/fechas/').data[0]['ya_paso'])

    def test_no_se_pueden_cargar_fechas_desde_aca(self):
        r = _client(self.buzo).post('/api/fechas/', {})
        self.assertEqual(r.status_code, 405)
        self.assertEqual(HabilitationWindow.objects.count(), 0)

    def test_hay_que_estar_autenticado(self):
        self.assertIn(APIClient().get('/api/fechas/').status_code, (401, 403))


class InscribirseTests(_ConBuzo):
    def test_elegir_una_fecha_la_guarda_en_el_perfil(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        self.assertEqual(r.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.habilitation_window_id, futura.pk)

    def test_cambiarla_mientras_no_paso_se_permite(self):
        # 15.18
        primera = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        segunda = _fecha(slot='SECOND', inicio='2026-12-10', fin='2026-12-12')
        _client(self.buzo).put('/api/mi-fecha/', {'window': primera.pk})
        _client(self.buzo).put('/api/mi-fecha/', {'window': segunda.pk})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.habilitation_window_id, segunda.pk)

    def test_cambiar_a_una_fecha_que_ya_paso_da_400_por_la_fecha(self):
        pasada = _fecha(slot='FIRST', inicio='2026-01-10', fin='2026-01-12')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': pasada.pk})
        self.assertEqual(r.status_code, 400)
        # El error va atado a `window`, no suelto: un 400 generico no distingue
        # "esa fecha ya paso" de "ese id no existe", y la pantalla necesita
        # poder ubicar el mensaje junto al campo.
        self.assertIn('window', r.data)
        self.perfil.refresh_from_db()
        self.assertIsNone(self.perfil.habilitation_window_id)

    def test_una_fecha_que_termina_hoy_todavia_se_puede_elegir(self):
        hoy = _fecha(slot='FIRST', inicio='2026-11-02', fin='2026-11-04')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': hoy.pk})
        self.assertEqual(r.status_code, 200)

    def test_un_id_que_no_existe_da_400_por_la_fecha(self):
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': 9999})
        self.assertEqual(r.status_code, 400)
        self.assertIn('window', r.data)

    def test_sin_el_campo_window_da_400_por_la_fecha(self):
        r = _client(self.buzo).put('/api/mi-fecha/', {})
        self.assertEqual(r.status_code, 400)
        self.assertIn('window', r.data)

    def test_desinscribirse_deja_el_perfil_sin_fecha(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': None}, format='json')
        self.assertEqual(r.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertIsNone(self.perfil.habilitation_window_id)

    def test_el_buzo_no_puede_inscribir_a_otro(self):
        # 5: ve y gestiona lo suyo, nada mas. La vista actua sobre request.user,
        # asi que no hay id de perfil que mandar; este test fija esa forma.
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        self.perfil_del_otro.refresh_from_db()
        self.assertIsNone(self.perfil_del_otro.habilitation_window_id)

    def test_un_id_de_usuario_en_el_cuerpo_se_ignora(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        _client(self.buzo).put('/api/mi-fecha/', {
            'window': futura.pk, 'user': self.otro.pk,
            'profile': self.perfil_del_otro.pk})
        self.perfil_del_otro.refresh_from_db()
        self.assertIsNone(self.perfil_del_otro.habilitation_window_id)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.habilitation_window_id, futura.pk)

    def test_la_respuesta_trae_la_fecha_elegida(self):
        futura = _fecha(slot='FIRST', inicio='2026-11-18', fin='2026-11-20')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': futura.pk})
        self.assertEqual(r.data['window'], futura.pk)

    def test_hay_que_estar_autenticado(self):
        r = APIClient().put('/api/mi-fecha/', {'window': None}, format='json')
        self.assertIn(r.status_code, (401, 403))
