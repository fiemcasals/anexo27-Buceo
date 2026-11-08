"""Tests de `GET /api/plantel/<id>/`: la ficha de un buzo para el revisor.

La ficha no define reglas, así que lo que se prueba es lo que agrega: quién
entra, que sean siempre los ocho puntos, que el historial diga quién dictaminó,
que `REVERTED` viaje como un dictamen más, y quién puede revertir.
"""

from unittest import mock

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APITestCase

from api import catalog
from api.models import Comment
from api.tests.test_fitness import (
    TODAY, VALID_FOR_EVERY_POINT, _diver, _november_2026, _upload,
)
from users.models import UserProfile


def _revisor(username, role, **datos):
    user = User.objects.create(username=username, email=f'{username}@ara.mil.ar',
                               **datos)
    UserProfile.objects.create(user=user, role=role)
    return user


def _url(perfil):
    return f'/api/plantel/{perfil.pk}/'


class FichaTests(APITestCase):
    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.turno = _november_2026()
        # Dos usuarios de relleno: el id del perfil no puede coincidir con el
        # del usuario, o el test no distinguiría uno del otro.
        User.objects.create(username='relleno-1')
        User.objects.create(username='relleno-2')
        self.buzo = _diver(birth_year=1988, window=self.turno)
        User.objects.filter(pk=self.buzo.user_id).update(
            first_name='Ana', last_name='Molina', email='ana@buceo.com')
        self.medico = _revisor('doc', 'DOCTOR',
                               first_name='Elena', last_name='Médica')
        self.enfermero = _revisor('vera', 'NURSE')
        self.client = APIClient()
        self.client.force_authenticate(self.medico)

    def pedir(self, perfil=None):
        respuesta = self.client.get(_url(perfil or self.buzo))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def estudio(self, cuerpo, code):
        return next(e for e in cuerpo['estudios'] if e['code'] == code)

    # --- quién entra ------------------------------------------------------
    def test_el_buzo_recibe_403(self):
        self.client.force_authenticate(self.buzo.user)
        self.assertEqual(self.client.get(_url(self.buzo)).status_code, 403)

    def test_sin_sesion_recibe_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(_url(self.buzo)).status_code, 401)

    def test_el_medico_y_el_enfermero_entran(self):
        for usuario in (self.medico, self.enfermero):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get(_url(self.buzo)).status_code, 200)

    def test_un_perfil_que_no_es_buzo_o_no_existe_da_404(self):
        # El plantel son los buzos: la ficha de un médico no existe.
        self.assertEqual(
            self.client.get(_url(self.medico.profile)).status_code, 404)
        self.assertEqual(self.client.get('/api/plantel/999999/').status_code, 404)

    # --- la forma ---------------------------------------------------------
    def test_trae_la_fila_del_listado_y_los_ocho_puntos_en_orden(self):
        cuerpo = self.pedir()
        self.assertEqual(cuerpo['id'], self.buzo.pk)
        self.assertNotEqual(self.buzo.pk, self.buzo.user_id)
        self.assertEqual(cuerpo['apellido'], 'Molina')
        self.assertEqual(cuerpo['correo'], 'ana@buceo.com')
        self.assertEqual(cuerpo['exigidos'], 7)
        self.assertEqual([e['code'] for e in cuerpo['estudios']],
                         list(catalog.CODES))

    def test_un_buzo_sin_nada_igual_trae_los_ocho(self):
        cuerpo = self.pedir()
        self.assertEqual(len(cuerpo['estudios']), 8)
        self.assertTrue(all(e['bloque'] is None and e['dictamenes'] == []
                            for e in cuerpo['estudios']))
        self.assertFalse(self.estudio(cuerpo, 'a')['corresponde'])

    def test_un_buzo_sin_turno_trae_los_ocho_y_exigidos_null(self):
        sin_turno = _diver(birth_year=1988, window=None)
        _upload(sin_turno, 'b', VALID_FOR_EVERY_POINT)
        cuerpo = self.pedir(sin_turno)
        self.assertIsNone(cuerpo['exigidos'])
        self.assertEqual(cuerpo['presentados'], 1)
        self.assertEqual(len(cuerpo['estudios']), 8)

    def test_los_aprobados_son_los_del_medico(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR')])
        _upload(self.buzo, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        cuerpo = self.pedir()
        self.assertEqual(cuerpo['aprobados'], 1)
        self.assertEqual(cuerpo['pre_revisados'], 1)

    # --- lo que espera dictamen -------------------------------------------
    def test_espera_dictamen_lo_sin_tocar_y_lo_pre_revisado(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT)
        _upload(self.buzo, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        _upload(self.buzo, 'd', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR')])
        _upload(self.buzo, 'e', VALID_FOR_EVERY_POINT,
                dictamenes=[('REJECTED', 'DOCTOR')])
        cuerpo = self.pedir()
        esperan = {e['code'] for e in cuerpo['estudios'] if e['espera_dictamen']}
        self.assertEqual(esperan, {'b', 'c'})

    def test_para_el_enfermero_lo_pre_revisado_ya_no_espera_nada_de_el(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT)
        _upload(self.buzo, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        self.client.force_authenticate(self.enfermero)
        cuerpo = self.pedir()
        esperan = {e['code'] for e in cuerpo['estudios'] if e['espera_dictamen']}
        self.assertEqual(esperan, {'b'})

    # --- el historial -----------------------------------------------------
    def test_el_historial_dice_quien_y_en_calidad_de_que(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        dictamen = self.estudio(self.pedir(), 'b')['dictamenes'][0]
        self.assertEqual(dictamen['estado'], 'PRE_APPROVED')
        self.assertEqual(dictamen['en_calidad_de'], 'NURSE')
        self.assertEqual(dictamen['por'], 'revisor-nurse')

    def test_el_rechazo_trae_motivo_y_detalle(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('REJECTED', 'DOCTOR')])
        dictamen = self.estudio(self.pedir(), 'b')['dictamenes'][0]
        self.assertEqual(dictamen['motivo'], 'OTHER')
        self.assertEqual(dictamen['motivo_texto'], 'Otros')
        self.assertEqual(dictamen['detalle'], 'Falta la firma.')

    def test_una_reversion_viaja_como_un_dictamen_sin_contenido(self):
        # Es el caso que la pantalla tiene que leer como "aprobación revertida"
        # y no como una fila en blanco: estado REVERTED, sin motivo ni detalle.
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR'), ('REVERTED', 'DOCTOR')])
        estudio = self.estudio(self.pedir(), 'b')
        self.assertEqual([d['estado'] for d in estudio['dictamenes']],
                         ['APPROVED', 'REVERTED'])
        revertido = estudio['dictamenes'][1]
        self.assertEqual((revertido['motivo'], revertido['detalle']), ('', ''))
        # Y el punto volvió a la pila del médico.
        self.assertEqual(estudio['estado'], 'IN_REVIEW')
        self.assertTrue(estudio['espera_dictamen'])

    def test_el_historial_va_en_orden_cronologico(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE'), ('APPROVED', 'DOCTOR')])
        estudio = self.estudio(self.pedir(), 'b')
        self.assertEqual([d['estado'] for d in estudio['dictamenes']],
                         ['PRE_APPROVED', 'APPROVED'])

    # --- revertir ---------------------------------------------------------
    def _aprobado_por(self, medico):
        bloque = _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT)
        return Comment.objects.create(
            block=bloque, doctor=medico, reviewer_role='DOCTOR',
            status='APPROVED')

    def test_quien_aprobo_puede_revertir(self):
        aprobacion = self._aprobado_por(self.medico)
        self.assertEqual(
            self.estudio(self.pedir(), 'b')['revertible_id'], aprobacion.pk)

    def test_otro_medico_no_puede_revertir_lo_que_aprobo_otro(self):
        # `SoloQuienDictamino` lo rechazaría: la ficha no ofrece el botón.
        self._aprobado_por(self.medico)
        otro = _revisor('doc2', 'DOCTOR')
        self.client.force_authenticate(otro)
        self.assertIsNone(self.estudio(self.pedir(), 'b')['revertible_id'])

    def test_el_enfermero_nunca_puede_revertir(self):
        self._aprobado_por(self.medico)
        self.client.force_authenticate(self.enfermero)
        self.assertIsNone(self.estudio(self.pedir(), 'b')['revertible_id'])

    def test_lo_ya_revertido_no_se_revierte_de_nuevo(self):
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR'), ('REVERTED', 'DOCTOR')])
        self.assertIsNone(self.estudio(self.pedir(), 'b')['revertible_id'])

    # --- consultas --------------------------------------------------------
    def _consultas(self):
        with CaptureQueriesContext(connection) as capturadas:
            self.pedir()
        return len(capturadas)

    def test_cuesta_las_mismas_consultas_con_uno_que_con_siete_estudios(self):
        # El prefetch de comentarios y de sus autores es lo que lo mantiene
        # fijo: sin él, cada dictamen cuesta una consulta para su autor.
        _upload(self.buzo, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR')])
        con_uno = self._consultas()
        for code in 'cdefgh':
            _upload(self.buzo, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('PRE_APPROVED', 'NURSE'),
                                ('APPROVED', 'DOCTOR')])
        self.assertEqual(self._consultas(), con_uno)
