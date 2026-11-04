"""El estado del buzo, tal como lo consume su pantalla (`GET /api/mi-estado/`).

El endpoint no calcula nada: serializa el `DiverSummary` del motor. Estos tests
fijan la forma de lo que sale, y que no salga lo que no debe (el apto y quién
dictaminó, §15.12).

`hoy` se fija en 2026-11-04 por la costura de `api.serializers`, de modo que los
casos de "antes de la ventana" y "vigente" no dependan del día en que corra la
suite. Cada cliente se arma con un `User` recién leído: el que guarda
`force_authenticate` cachea su `profile`, y estos tests cambian el perfil.
"""

import json
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APITestCase

from api import catalog
from api.models import Comment, HabilitationWindow, StudyBlock
from users.models import UserProfile

from .media_temporal import MEDIA_TEMPORAL

HOY = date(2026, 11, 4)
URL = '/api/mi-estado/'

#: Una fecha de estudio que cubre cualquiera de los ocho puntos en la ventana de
#: diciembre de 2026 y que no es futura respecto de HOY.
ESTUDIO_VIGENTE = date(2026, 10, 30)


def _user(username, nacimiento=date(1990, 6, 15), ventana=None, correo=''):
    user = User.objects.create(username=username, email=correo)
    perfil = UserProfile.objects.create(
        user=user, role='USER', birth_date=nacimiento, habilitation_window=ventana)
    return user, perfil


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _fecha(slot='FIRST', inicio='2026-12-10', fin='2026-12-12'):
    inicio = date.fromisoformat(inicio)
    return HabilitationWindow.objects.create(
        cycle=inicio.year, slot=slot,
        start_date=inicio, end_date=date.fromisoformat(fin))


def _get(user):
    """El cuerpo que viaja por el cable, con un `User` recién leído."""
    respuesta = _client(User.objects.get(pk=user.pk)).get(URL)
    assert respuesta.status_code == 200, respuesta.content
    return json.loads(respuesta.content)


def _sin_fechas_publicadas():
    # Las fechas elegidas estan protegidas contra el borrado: se desinscribe a
    # todos antes de vaciar la tabla.
    UserProfile.objects.update(habilitation_window=None)
    HabilitationWindow.objects.all().delete()


def _punto(cuerpo, code):
    return next(e for e in cuerpo['estudios'] if e['code'] == code)


def _estudio(user, code, study_date=ESTUDIO_VIGENTE, nombre='estudio.pdf'):
    bloque = StudyBlock(user=user, study_code=code, study_date=study_date)
    bloque.pdf_attachment.save(nombre, ContentFile(b'%PDF-1.4'), save=False)
    bloque.save()
    return bloque


def _dictamen(bloque, revisor, status, **extra):
    rol = {'APPROVED': 'DOCTOR', 'PRE_APPROVED': 'NURSE'}.get(status, 'DOCTOR')
    return Comment.objects.create(
        block=bloque, doctor=revisor, reviewer_role=rol, status=status, **extra)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class _ConBuzo(APITestCase):
    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=HOY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.fecha = _fecha()
        self.buzo, self.perfil = _user('buzo', ventana=self.fecha,
                                       correo='buzo@armada.example')
        self.mayor, _ = _user('mayor', nacimiento=date(1970, 3, 1), ventana=self.fecha)
        self.menor, _ = _user('menor', nacimiento=date(1995, 3, 1), ventana=self.fecha)
        self.sin_fecha, _ = _user('sinfecha', ventana=None)
        self.medico = User.objects.create(
            username='dr-quiroga', first_name='Ramon', last_name='Quiroga')
        self.estudio_c = _estudio(self.buzo, 'c')


class ElEstadoDelBuzoTests(_ConBuzo):
    def test_devuelve_los_ocho_puntos_siempre(self):
        self.assertEqual([e['code'] for e in _get(self.buzo)['estudios']], list('abcdefgh'))

    def test_el_de_mas_de_40_tiene_los_ocho_exigidos(self):
        self.assertEqual(_get(self.mayor)['total_exigidos'], 8)

    def test_el_menor_de_40_tiene_siete(self):
        self.assertEqual(_get(self.menor)['total_exigidos'], 7)

    def test_el_punto_a_de_un_menor_de_40_viene_como_no_corresponde_y_explicado(self):
        # §8.3: se muestra igual, apagado y explicado
        punto_a = _punto(_get(self.menor), 'a')
        self.assertFalse(punto_a['corresponde'])
        self.assertIn('40', punto_a['motivo_no_corresponde'])
        self.assertEqual(punto_a['motivo_no_corresponde'],
                         'Se exige a partir de los 40 años de edad')
        self.assertEqual(punto_a['estado'], 'NOT_REQUIRED')

    def test_un_punto_que_corresponde_no_trae_motivo(self):
        punto_b = _punto(_get(self.buzo), 'b')
        self.assertTrue(punto_b['corresponde'])
        self.assertIsNone(punto_b['motivo_no_corresponde'])

    def test_el_texto_sale_del_catalogo(self):
        self.assertEqual(_punto(_get(self.buzo), 'c')['texto'], 'Electroencefalograma')

    def test_no_expone_el_apto_ni_quien_dictamino(self):
        # §15.12
        cuerpo = _get(self.buzo)
        self.assertNotIn('is_apto', cuerpo)
        self.assertNotIn('doctor', json.dumps(cuerpo))

    def test_las_claves_son_exactamente_las_del_contrato(self):
        # Una clave de mas (el apto, el revisor) es un defecto aunque el dato
        # este en el DiverSummary: se compara el conjunto, no la ausencia de una.
        cuerpo = _get(self.buzo)
        self.assertEqual(set(cuerpo), {
            'fecha_elegida', 'hay_fechas_para_elegir', 'faltan', 'revisados',
            'total_exigidos', 'correo', 'estudios'})
        self.assertEqual(set(_punto(cuerpo, 'c')), {
            'code', 'texto', 'estado', 'corresponde', 'motivo_no_corresponde',
            'vence_el', 'desde_cuando', 'rechazo', 'puede_reemplazarse', 'archivo',
            'upload_hint'})

    def test_los_puntos_d_y_f_traen_el_aviso_del_catalogo(self):
        cuerpo = _get(self.buzo)
        for code in 'df':
            esperado = catalog.get(code).upload_hint
            self.assertTrue(esperado, code)  # el catalogo lo tiene: si no, el test no mide nada
            self.assertEqual(_punto(cuerpo, code)['upload_hint'], esperado, code)

    def test_un_punto_sin_aviso_lo_trae_vacio(self):
        cuerpo = _get(self.buzo)
        for code in 'abceg':
            self.assertEqual(catalog.get(code).upload_hint, '', code)
            self.assertEqual(_punto(cuerpo, code)['upload_hint'], '', code)

    def test_el_correo_es_el_del_que_llama(self):
        self.assertEqual(_get(self.buzo)['correo'], 'buzo@armada.example')

    def test_la_fecha_elegida_viaja_como_la_fecha_publicada(self):
        elegida = _get(self.buzo)['fecha_elegida']
        self.assertEqual(elegida['id'], self.fecha.pk)
        self.assertEqual(elegida['end_date'], '2026-12-12')

    def test_el_vencimiento_sale_del_estudio_cargado(self):
        self.assertEqual(_punto(_get(self.buzo), 'c')['vence_el'],
                         str(ESTUDIO_VIGENTE + timedelta(days=365)))
        self.assertIsNone(_punto(_get(self.buzo), 'b')['vence_el'])

    def test_el_archivo_es_la_direccion_del_pdf_o_null(self):
        punto_c = _punto(_get(self.buzo), 'c')
        self.assertTrue(punto_c['archivo'].startswith('http'))
        self.assertIn('estudio', punto_c['archivo'])
        self.assertIsNone(_punto(_get(self.buzo), 'b')['archivo'])

    def test_la_aprobacion_del_medico_cuenta_como_revisado(self):
        _dictamen(self.estudio_c, self.medico, 'APPROVED')
        cuerpo = _get(self.buzo)
        self.assertEqual(cuerpo['revisados'], 1)
        self.assertEqual(_punto(cuerpo, 'c')['estado'], 'APPROVED')

    def test_en_revision_y_pre_revisado_no_cuentan_como_revisados(self):
        enfermero = User.objects.create(username='enf')
        _dictamen(self.estudio_c, enfermero, 'PRE_APPROVED')
        _estudio(self.buzo, 'd')
        cuerpo = _get(self.buzo)
        self.assertEqual(cuerpo['revisados'], 0)
        self.assertEqual(_punto(cuerpo, 'c')['estado'], 'PRE_REVIEWED')
        self.assertEqual(_punto(cuerpo, 'd')['estado'], 'IN_REVIEW')

    def test_faltan_no_cuenta_lo_que_esta_en_revision_ni_el_anexo_27_fuera_de_ventana(self):
        # Exigidos b..h; c en revision y h antes de su ventana: faltan b, d, e, f, g.
        self.assertEqual(_get(self.buzo)['faltan'], 5)
        _estudio(self.buzo, 'd')
        self.assertEqual(_get(self.buzo)['faltan'], 4)

    def test_un_punto_que_no_corresponde_no_cuenta_en_los_que_faltan(self):
        # El menor de 40 debe b..g (h fuera de ventana): faltan seis, no siete.
        self.assertEqual(_get(self.menor)['faltan'], 6)
        self.assertEqual(_get(self.mayor)['faltan'], 7)


class LoQueFaltaEsLoQueNecesitaUnaCargaAhoraTests(_ConBuzo):
    """`faltan` es el trabajo que el buzo tiene que hacer hoy: lo exigido que
    esta MISSING, REJECTED, EXPIRED o DATE_INVALID. El Anexo 27 antes de su
    ventana no cuenta: todavia no se puede presentar (§15.19)."""

    ESTADOS = {'MISSING', 'REJECTED', 'EXPIRED', 'DATE_INVALID'}
    DENTRO_DE_LA_VENTANA = date(2026, 12, 1)

    def _todo_aprobado(self, user):
        """Sube y aprueba todo lo exigido, h incluido, con el reloj dentro de
        la ventana del Anexo 27."""
        for code in 'bcdefg':
            _dictamen(_estudio(user, code), self.medico, 'APPROVED')
        _dictamen(_estudio(user, 'h', study_date=date(2026, 11, 25)),
                  self.medico, 'APPROVED')

    def _get_en_la_ventana(self, user):
        with mock.patch('api.serializers.hoy', return_value=self.DENTRO_DE_LA_VENTANA):
            return _get(user)

    def test_el_punto_de_una_carga_completa_deja_faltan_en_cero(self):
        # Control de los tests de abajo: sin pendientes, 0.
        self._todo_aprobado(self.menor)
        self.assertEqual(self._get_en_la_ventana(self.menor)['faltan'], 0)

    def test_un_estudio_rechazado_cuenta_en_faltan(self):
        self._todo_aprobado(self.menor)
        c = StudyBlock.objects.get(user=self.menor, study_code='c')
        _dictamen(c, self.medico, 'REJECTED',
                  rejection_reason='OTHER', content='Falta la firma.')
        cuerpo = self._get_en_la_ventana(self.menor)
        self.assertEqual(_punto(cuerpo, 'c')['estado'], 'REJECTED')
        self.assertEqual(cuerpo['faltan'], 1)

    def test_un_estudio_vencido_cuenta_en_faltan(self):
        self._todo_aprobado(self.menor)
        StudyBlock.objects.filter(user=self.menor, study_code='e').update(
            study_date=date(2025, 12, 1))
        cuerpo = self._get_en_la_ventana(self.menor)
        self.assertEqual(_punto(cuerpo, 'e')['estado'], 'EXPIRED')
        self.assertEqual(cuerpo['faltan'], 1)

    def test_un_estudio_con_fecha_invalida_cuenta_en_faltan(self):
        self._todo_aprobado(self.menor)
        StudyBlock.objects.filter(user=self.menor, study_code='e').update(
            study_date=date(2026, 12, 20))
        cuerpo = self._get_en_la_ventana(self.menor)
        self.assertEqual(_punto(cuerpo, 'e')['estado'], 'DATE_INVALID')
        self.assertEqual(cuerpo['faltan'], 1)

    def test_si_lo_unico_pendiente_es_el_anexo_27_fuera_de_ventana_faltan_es_cero(self):
        # Parece un error y no lo es: no tiene nada que hacer hoy. Cuando la
        # ventana abra, el punto pasa a MISSING y el contador sube a 1.
        for code in 'bcdefg':
            _dictamen(_estudio(self.menor, code), self.medico, 'APPROVED')
        cuerpo = _get(self.menor)
        self.assertEqual(_punto(cuerpo, 'h')['estado'], 'BEFORE_WINDOW')
        self.assertEqual(cuerpo['faltan'], 0)
        self.assertEqual(self._get_en_la_ventana(self.menor)['faltan'], 1)

    def test_faltan_es_igual_a_las_tarjetas_de_falta_subir_sin_el_anexo_27_fuera_de_ventana(self):
        # El invariante de la pantalla: el contador y las tarjetas cuentan lo
        # mismo. b sin subir, c rechazado, d vencido, e fecha invalida, h fuera
        # de ventana, y f y g sin subir.
        _dictamen(_estudio(self.menor, 'c'), self.medico, 'REJECTED',
                  rejection_reason='OTHER', content='Falta la firma.')
        _estudio(self.menor, 'd', study_date=date(2025, 12, 1))
        _estudio(self.menor, 'e', study_date=date(2026, 11, 4) + timedelta(days=1))
        cuerpo = _get(self.menor)
        tarjetas = [e for e in cuerpo['estudios']
                    if e['corresponde'] and e['estado'] in self.ESTADOS]
        self.assertEqual(
            sorted(e['estado'] for e in tarjetas),
            ['DATE_INVALID', 'EXPIRED', 'MISSING', 'MISSING', 'MISSING', 'REJECTED'])
        self.assertEqual(_punto(cuerpo, 'h')['estado'], 'BEFORE_WINDOW')
        self.assertEqual(cuerpo['faltan'], len(tarjetas))


class UnEstudioSinArchivoTests(_ConBuzo):
    # `blank=False` es validacion de formulario, no de base: un bloque creado por
    # la consola, la siembra o el admin puede no tener archivo, y la pantalla no
    # puede caerse por eso. (Los fixtures de arriba siempre adjuntan archivo.)
    def _sin_archivo(self, code='d'):
        bloque = StudyBlock.objects.create(
            user=self.buzo, study_code=code, study_date=ESTUDIO_VIGENTE)
        self.assertFalse(bloque.pdf_attachment)
        return bloque

    def test_responde_200_y_el_archivo_viene_null(self):
        self._sin_archivo()
        respuesta = _client(User.objects.get(pk=self.buzo.pk)).get(URL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(_punto(json.loads(respuesta.content), 'd')['archivo'])

    def test_el_resto_de_la_fila_se_sirve_igual(self):
        bloque = self._sin_archivo()
        punto_d = _punto(_get(self.buzo), 'd')
        self.assertEqual(punto_d['estado'], 'IN_REVIEW')
        self.assertTrue(punto_d['corresponde'])
        self.assertTrue(punto_d['puede_reemplazarse'])
        self.assertEqual(punto_d['vence_el'], str(ESTUDIO_VIGENTE + timedelta(days=365)))
        _dictamen(bloque, self.medico, 'APPROVED')
        punto_d = _punto(_get(self.buzo), 'd')
        self.assertEqual(punto_d['estado'], 'APPROVED')
        self.assertFalse(punto_d['puede_reemplazarse'])

    def test_los_otros_puntos_conservan_su_archivo(self):
        self._sin_archivo()
        cuerpo = _get(self.buzo)
        self.assertTrue(_punto(cuerpo, 'c')['archivo'].startswith('http'))


class ElEstadoEsSoloDelQueLlamaTests(_ConBuzo):
    def test_hay_que_estar_autenticado(self):
        self.assertIn(APIClient().get(URL).status_code, (401, 403))

    def test_devuelve_el_estado_del_que_llama_y_no_el_de_otro(self):
        _estudio(self.mayor, 'b')
        _get_buzo = _get(self.buzo)
        self.assertEqual(_punto(_get_buzo, 'b')['estado'], 'MISSING')
        self.assertEqual(_get_buzo['correo'], 'buzo@armada.example')

    def test_un_id_en_la_consulta_no_cambia_de_buzo(self):
        _estudio(self.mayor, 'b')
        cliente = _client(User.objects.get(pk=self.buzo.pk))
        for parametro in ('user', 'id', 'profile', 'user_id'):
            respuesta = cliente.get(URL, {parametro: self.mayor.pk})
            self.assertEqual(respuesta.status_code, 200, parametro)
            cuerpo = json.loads(respuesta.content)
            self.assertEqual(cuerpo['total_exigidos'], 7, parametro)
            self.assertEqual(_punto(cuerpo, 'b')['estado'], 'MISSING', parametro)

    def test_solo_acepta_get(self):
        cliente = _client(User.objects.get(pk=self.buzo.pk))
        self.assertEqual(cliente.post(URL, {}).status_code, 405)
        self.assertEqual(cliente.put(URL, {}).status_code, 405)
        self.assertEqual(cliente.delete(URL).status_code, 405)


class SinFechaElegidaTests(_ConBuzo):
    # Review Focus 2 — §15.21
    def test_sin_fecha_y_con_fechas_publicadas_marca_que_hay_para_elegir(self):
        cuerpo = _get(self.sin_fecha)
        self.assertIsNone(cuerpo['fecha_elegida'])
        self.assertTrue(cuerpo['hay_fechas_para_elegir'])

    def test_sin_fecha_y_sin_fechas_publicadas_marca_que_no_hay_nada_que_elegir(self):
        _sin_fechas_publicadas()
        self.assertFalse(_get(self.sin_fecha)['hay_fechas_para_elegir'])

    def test_una_fecha_que_ya_paso_no_es_algo_que_elegir(self):
        # La inscripcion la rechaza (400 por `window`), asi que ofrecerla como
        # "hay para elegir" mandaria al buzo a un callejon.
        _sin_fechas_publicadas()
        _fecha(inicio='2026-01-10', fin='2026-01-12')
        self.assertFalse(_get(self.sin_fecha)['hay_fechas_para_elegir'])

    def test_una_fecha_que_termina_hoy_todavia_se_puede_elegir(self):
        _sin_fechas_publicadas()
        _fecha(inicio='2026-11-02', fin='2026-11-04')
        self.assertTrue(_get(self.sin_fecha)['hay_fechas_para_elegir'])

    def test_sin_fecha_no_revienta_por_None(self):
        self.assertEqual(_client(self.sin_fecha).get(URL).status_code, 200)

    def test_sin_fecha_vienen_los_ocho_y_ninguno_corresponde(self):
        cuerpo = _get(self.sin_fecha)
        self.assertEqual([e['code'] for e in cuerpo['estudios']], list('abcdefgh'))
        self.assertEqual(cuerpo['total_exigidos'], 0)
        self.assertFalse(any(e['corresponde'] for e in cuerpo['estudios']))
        for e in cuerpo['estudios']:
            self.assertTrue(e['motivo_no_corresponde'], e['code'])


class SinFechaDeNacimientoTests(_ConBuzo):
    # El motor tiene un DiverState.UNKNOWN_AGE, asi que el caso existe: el
    # registro de la Tarea 5 vuelve birth_date obligatorio, pero los perfiles
    # que ya estan en la base pueden no tenerla y la pantalla no puede caerse.
    def test_sin_birth_date_responde_200(self):
        self.perfil.birth_date = None
        self.perfil.save()
        self.assertEqual(_client(User.objects.get(pk=self.buzo.pk)).get(URL).status_code, 200)

    def test_sin_birth_date_no_adivina_la_edad_ni_exige_el_punto_a(self):
        self.perfil.birth_date = None
        self.perfil.save()
        punto_a = _punto(_get(self.buzo), 'a')
        self.assertFalse(punto_a['corresponde'])
        self.assertTrue(punto_a['motivo_no_corresponde'])

    def test_sin_birth_date_no_hay_exigidos_y_cada_punto_explica_por_que(self):
        self.perfil.birth_date = None
        self.perfil.save()
        cuerpo = _get(self.buzo)
        self.assertEqual(cuerpo['total_exigidos'], 0)
        self.assertEqual(len(cuerpo['estudios']), 8)
        # "cargar" es el verbo de subir un estudio: no se usa para el perfil.
        self.assertEqual(_punto(cuerpo, 'b')['motivo_no_corresponde'],
                         'Se determina al completar la fecha de nacimiento')
        for e in cuerpo['estudios']:
            self.assertTrue(e['motivo_no_corresponde'], e['code'])


class ElAnexo27AntesDeSuVentanaTests(_ConBuzo):
    # Review Focus 3 — §15.19
    def test_antes_de_la_ventana_no_sale_como_faltante(self):
        self.assertEqual(_punto(_get(self.buzo), 'h')['estado'], 'BEFORE_WINDOW')

    def test_antes_de_la_ventana_dice_desde_cuando(self):
        self.assertEqual(_punto(_get(self.buzo), 'h')['desde_cuando'],
                         str(self.fecha.end_date - timedelta(days=30)))

    def test_los_demas_puntos_no_dicen_desde_cuando(self):
        cuerpo = _get(self.buzo)
        for code in 'abcdefg':
            self.assertIsNone(_punto(cuerpo, code)['desde_cuando'], code)

    def test_ya_dentro_de_la_ventana_no_dice_desde_cuando(self):
        with mock.patch('api.serializers.hoy', return_value=date(2026, 12, 1)):
            punto_h = _punto(_get(self.buzo), 'h')
        self.assertEqual(punto_h['estado'], 'MISSING')
        self.assertIsNone(punto_h['desde_cuando'])


class ElRechazoSeMuestraTextualTests(_ConBuzo):
    def test_el_motivo_y_el_detalle_viajan_al_buzo(self):
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='ILLEGIBLE', content='La fotografia esta cortada.')
        rechazo = _punto(_get(self.buzo), 'c')['rechazo']
        self.assertEqual(rechazo['detalle'], 'La fotografia esta cortada.')
        self.assertIn('ilegible', rechazo['motivo'].lower())
        self.assertEqual(set(rechazo), {'motivo', 'detalle'})

    def test_el_rechazo_no_dice_quien_rechazo(self):
        # 15.12
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='ILLEGIBLE', content='Cortada.')
        cuerpo = json.dumps(_get(self.buzo))
        self.assertNotIn(self.medico.last_name, cuerpo)
        self.assertNotIn(self.medico.username, cuerpo)
        self.assertNotIn('DOCTOR', cuerpo)

    def test_un_punto_sin_rechazo_trae_null(self):
        self.assertIsNone(_punto(_get(self.buzo), 'c')['rechazo'])

    def test_un_rechazo_de_un_estudio_que_ya_vencio_no_se_muestra(self):
        # La fecha manda sobre el dictamen: el punto esta EXPIRED y lo que hay
        # que hacer es renovarlo, no leer un motivo de rechazo.
        vencido = _estudio(self.buzo, 'e', study_date=date(2025, 12, 1))
        _dictamen(vencido, self.medico, 'REJECTED',
                  rejection_reason='OTHER', content='Falta la firma.')
        punto_e = _punto(_get(self.buzo), 'e')
        self.assertEqual(punto_e['estado'], 'EXPIRED')
        self.assertIsNone(punto_e['rechazo'])

    def test_un_rechazo_viejo_no_se_muestra_si_despues_lo_aprobaron(self):
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='OTHER', content='Falta la firma.')
        _dictamen(self.estudio_c, self.medico, 'APPROVED')
        punto_c = _punto(_get(self.buzo), 'c')
        self.assertEqual(punto_c['estado'], 'APPROVED')
        self.assertIsNone(punto_c['rechazo'])


class ElReemplazoSeDecideConLaReglaDeLaTarea2Tests(_ConBuzo):
    def test_un_punto_sin_carga_se_puede_cargar(self):
        self.assertTrue(_punto(_get(self.buzo), 'b')['puede_reemplazarse'])

    def test_lo_aprobado_y_vigente_no_se_puede_pisar(self):
        _dictamen(self.estudio_c, self.medico, 'APPROVED')
        self.assertFalse(_punto(_get(self.buzo), 'c')['puede_reemplazarse'])

    def test_lo_rechazado_se_puede_reemplazar(self):
        _dictamen(self.estudio_c, self.medico, 'REJECTED',
                  rejection_reason='OTHER', content='Falta la firma.')
        self.assertTrue(_punto(_get(self.buzo), 'c')['puede_reemplazarse'])

    def test_lo_que_esta_en_revision_se_puede_reemplazar(self):
        self.assertTrue(_punto(_get(self.buzo), 'c')['puede_reemplazarse'])

    def test_sin_fecha_de_nacimiento_lo_aprobado_sigue_protegido(self):
        # Sin edad todo punto es NOT_REQUIRED: derivar el reemplazo del estado
        # del slot dejaria pisar lo que el medico ya aprobo.
        _dictamen(self.estudio_c, self.medico, 'APPROVED')
        self.perfil.birth_date = None
        self.perfil.save()
        punto_c = _punto(_get(self.buzo), 'c')
        self.assertEqual(punto_c['estado'], 'NOT_REQUIRED')
        self.assertFalse(punto_c['puede_reemplazarse'])

    def test_sin_ventana_lo_aprobado_sigue_protegido(self):
        _dictamen(self.estudio_c, self.medico, 'APPROVED')
        self.perfil.habilitation_window = None
        self.perfil.save()
        punto_c = _punto(_get(self.buzo), 'c')
        self.assertEqual(punto_c['estado'], 'NOT_REQUIRED')
        self.assertFalse(punto_c['puede_reemplazarse'])

    def test_lo_aprobado_pero_vencido_se_puede_renovar(self):
        # Vence el 2026-03-01 + 365 dias < fin de la ventana (2026-12-12).
        vencido = _estudio(self.buzo, 'e', study_date=date(2025, 12, 1))
        _dictamen(vencido, self.medico, 'APPROVED')
        punto_e = _punto(_get(self.buzo), 'e')
        self.assertEqual(punto_e['estado'], 'EXPIRED')
        self.assertTrue(punto_e['puede_reemplazarse'])


class SinConsultasDeMasTests(_ConBuzo):
    # §13
    def _consultas(self, user):
        cliente = _client(User.objects.get(pk=user.pk))
        with CaptureQueriesContext(connection) as ctx:
            respuesta = cliente.get(URL)
        self.assertEqual(respuesta.status_code, 200)
        return len(ctx.captured_queries)

    def test_el_estado_no_hace_una_consulta_por_estudio(self):
        with CaptureQueriesContext(connection) as ctx:
            _get(self.buzo)
        self.assertLess(len(ctx.captured_queries), 12)

    def test_cargar_los_ocho_puntos_con_dictamenes_no_agrega_consultas(self):
        # Con un solo estudio ya corren las consultas de los bloques y de sus
        # dictamenes; de ahi en mas, cada punto cargado debe salir gratis.
        _dictamen(_estudio(self.mayor, 'a'), self.medico, 'APPROVED')
        con_uno = self._consultas(self.mayor)
        for code in 'bcdefgh':
            _dictamen(_estudio(self.mayor, code), self.medico, 'APPROVED')
        con_ocho = self._consultas(self.mayor)
        self.assertEqual(con_ocho, con_uno)
        # Perfil con usuario y ventana, bloques vigentes, dictamenes, y la
        # consulta de si hay fechas para elegir: cinco, no una por punto.
        self.assertLessEqual(con_ocho, 5)
