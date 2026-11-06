"""Tests de la fila del plantel: un buzo convertido en lo que el médico lista."""

from datetime import date, datetime, time
from datetime import timezone as dt_timezone

from django.db.models import Prefetch
from django.test import TestCase
from django.utils import timezone

from api import plantel
from api.models import StudyBlock
from api.tests.test_fitness import (
    TODAY, VALID_FOR_EVERY_POINT, _diver, _july_2027, _november_2026, _upload,
)
from users.models import UserProfile

CLAVES = {
    'id', 'grado', 'apellido', 'nombre', 'unidad', 'dni', 'edad', 'turno',
    'presentados', 'exigidos', 'a_revisar', 'sin_tocar', 'pre_revisados',
    'vencidos', 'rechazados', 'ultima_revision', 'estado',
    'subida_mas_vieja_sin_dictamen',
}


def _traido(profile):
    """El perfil como lo trae el listado: todo precargado, sin consultas después."""
    return UserProfile.objects.select_related("user", "habilitation_window").prefetch_related(
        Prefetch(
            "user__study_blocks",
            queryset=StudyBlock.objects.filter(is_current=True).prefetch_related("comments"),
        )
    ).get(pk=profile.pk)


class FilaDeUnBuzoTests(TestCase):
    hoy = TODAY

    def _fila(self, profile):
        profile = _traido(profile)
        with self.assertNumQueries(0):
            return plantel.fila(profile, self.hoy)

    def test_el_denominador_sale_de_la_edad_contra_el_año_del_turno(self):
        # Hoy es 2026 y el turno es de julio de 2027. Nacido en 1987 tiene 39 en
        # el año de hoy y 40 en el del turno: le corresponden ocho. Medir contra
        # hoy daría siete.
        perfil = _diver(birth_year=1987, window=_july_2027())
        fila = self._fila(perfil)
        self.assertEqual(fila['exigidos'], 8)
        self.assertEqual(fila['edad'], 40)

    def test_a_revisar_suma_lo_sin_tocar_y_lo_pre_revisado(self):
        perfil = _diver(birth_year=1988, window=_november_2026())
        _upload(perfil, 'b', VALID_FOR_EVERY_POINT)
        _upload(perfil, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        fila = self._fila(perfil)
        self.assertEqual(fila['a_revisar'], 2)
        self.assertEqual(fila['sin_tocar'], 1)
        self.assertEqual(fila['pre_revisados'], 1)

    def test_sin_turno_no_dice_cero_sobre_cero(self):
        # Subió los ocho pero no se inscribió: el exigido no se puede determinar.
        perfil = _diver(birth_year=1980, window=None)
        for code in 'abcdefgh':
            _upload(perfil, code, VALID_FOR_EVERY_POINT)
        fila = self._fila(perfil)
        self.assertEqual(fila['presentados'], 8)
        self.assertIsNone(fila['exigidos'])
        self.assertIsNone(fila['turno'])
        self.assertIsNone(fila['edad'])
        self.assertEqual(fila['estado'], 'NO_WINDOW')

    def test_sin_fecha_de_nacimiento_el_exigido_queda_sin_determinar(self):
        perfil = _diver(birth_year=None, window=_november_2026())
        fila = self._fila(perfil)
        self.assertIsNone(fila['exigidos'])
        self.assertIsNone(fila['edad'])
        self.assertEqual(fila['estado'], 'UNKNOWN_AGE')

    def test_la_ultima_revision_cuenta_solo_dictamenes_del_medico(self):
        # Un enfermero pre-aprobó hoy; el médico no miró nunca.
        perfil = _diver(birth_year=1988, window=_november_2026())
        _upload(perfil, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('PRE_APPROVED', 'NURSE')])
        self.assertIsNone(self._fila(perfil)['ultima_revision'])

    def test_la_subida_mas_vieja_mira_solo_lo_que_no_tiene_dictamen(self):
        # Hay un aprobado viejísimo (no cuenta), un pre-revisado y uno sin tocar.
        # El pre-revisado es el más viejo de los dos candidatos: una cuenta que
        # mirara sólo lo sin tocar, o que tomara el máximo, falla.
        perfil = _diver(birth_year=1988, window=_november_2026())
        aprobado = _upload(perfil, 'b', VALID_FOR_EVERY_POINT,
                           dictamenes=[('APPROVED', 'DOCTOR')])
        pre = _upload(perfil, 'c', VALID_FOR_EVERY_POINT,
                      dictamenes=[('PRE_APPROVED', 'NURSE')])
        sin_tocar = _upload(perfil, 'd', VALID_FOR_EVERY_POINT)
        for bloque, dia in ((aprobado, date(2026, 1, 1)), (pre, date(2026, 2, 1)),
                            (sin_tocar, date(2026, 3, 1))):
            StudyBlock.objects.filter(pk=bloque.pk).update(
                created_at=timezone.make_aware(datetime.combine(dia, time(9, 0))))
        pre.refresh_from_db()
        fila = self._fila(perfil)
        self.assertEqual(fila['subida_mas_vieja_sin_dictamen'], pre.created_at)

    def test_sin_nada_sin_dictamen_la_subida_mas_vieja_es_none(self):
        perfil = _diver(birth_year=1988, window=_november_2026())
        self.assertIsNone(self._fila(perfil)['subida_mas_vieja_sin_dictamen'])

    def test_las_claves_son_exactamente_las_del_contrato(self):
        perfil = _diver(birth_year=1988, window=_november_2026())
        perfil.rank, perfil.destination = 'CT', 'Escuela de Buceo'
        perfil.save()
        perfil.user.first_name, perfil.user.last_name = 'Ana', 'Gómez'
        perfil.user.save()
        fila = self._fila(perfil)
        self.assertEqual(set(fila), CLAVES)
        self.assertEqual((fila['id'], fila['grado'], fila['apellido'], fila['nombre'],
                          fila['unidad'], fila['dni']),
                         (perfil.pk, 'CT', 'Gómez', 'Ana', 'Escuela de Buceo', perfil.dni))
        self.assertEqual(fila['turno']['id'], perfil.habilitation_window.pk)
        self.assertEqual(fila['turno']['slot'], 'FIRST')
        self.assertEqual(fila['turno']['end_date'], date(2026, 11, 20))

    def test_con_turno_un_estudio_no_exigido_no_se_cuenta_como_presentado(self):
        # A los 38 no le corresponde el punto a: subirlo no suma.
        perfil = _diver(birth_year=1988, window=_november_2026())
        _upload(perfil, 'a', VALID_FOR_EVERY_POINT)
        _upload(perfil, 'b', VALID_FOR_EVERY_POINT)
        fila = self._fila(perfil)
        self.assertEqual(fila['exigidos'], 7)
        self.assertEqual(fila['presentados'], 1)

    def test_con_turno_y_sin_fecha_de_nacimiento_presentados_cuenta_lo_subido(self):
        perfil = _diver(birth_year=None, window=_november_2026())
        _upload(perfil, 'a', VALID_FOR_EVERY_POINT)
        _upload(perfil, 'b', VALID_FOR_EVERY_POINT)
        fila = self._fila(perfil)
        self.assertIsNone(fila['exigidos'])
        self.assertEqual(fila['presentados'], 2)

    def test_vencidos_y_un_rechazado_a_la_vez_van_a_su_columna_y_gana_rechazado(self):
        perfil = _diver(birth_year=1988, window=_november_2026())
        _upload(perfil, 'b', VALID_FOR_EVERY_POINT, dictamenes=[('REJECTED', 'DOCTOR')])
        # Vence el 19/11/2026 y el turno cierra el 20: aprobado pero vencido.
        _upload(perfil, 'c', date(2025, 11, 19), dictamenes=[('APPROVED', 'DOCTOR')])
        # Un segundo vencido, para que los dos conteos sean distintos y un cruce
        # entre columnas no pase inadvertido.
        _upload(perfil, 'd', date(2025, 11, 19), dictamenes=[('APPROVED', 'DOCTOR')])
        for code in 'efgh':
            _upload(perfil, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('APPROVED', 'DOCTOR')])
        fila = self._fila(perfil)
        self.assertEqual(fila['vencidos'], 2)
        self.assertEqual(fila['rechazados'], 1)
        self.assertEqual(fila['estado'], 'REJECTED')


def _f(**kw):
    """Una fila a mano, con las claves de ``fila()``; sólo se pisa lo que importa."""
    base = {
        'id': 0, 'grado': 'Marinero', 'apellido': 'Zeta', 'nombre': 'Ana',
        'unidad': 'Base', 'dni': '1', 'edad': 30, 'turno': None,
        'presentados': 0, 'exigidos': None, 'a_revisar': 0, 'sin_tocar': 0,
        'pre_revisados': 0, 'vencidos': 0, 'rechazados': 0,
        'ultima_revision': None, 'estado': 'NO_WINDOW',
        'subida_mas_vieja_sin_dictamen': None,
    }
    base.update(kw)
    return base


def _turno(pk):
    return {'id': pk, 'slot': 'S', 'slot_display': 'S',
            'start_date': date(2026, 11, 1), 'end_date': date(2026, 11, 30)}


def _ts(dia):
    return datetime(2026, 10, dia, 12, 0, tzinfo=dt_timezone.utc)


class _Plantel:
    """Ocho buzos armados a mano, sin base: las funciones son puras."""

    def setUp(self):
        self.turno_1ra, self.turno_2da = 1, 2
        # Apto, turno 1, todo presentado.
        self.fila_gomez = _f(
            id=1, grado='Cabo', apellido='Gómez', nombre='María',
            dni='12.345.675', turno=_turno(1), presentados=8, exigidos=8,
            estado='APTO', ultima_revision=date(2026, 10, 1))
        # Apto, turno 2.
        self.fila_apto_2 = _f(
            id=2, apellido='Álvarez', nombre='Luis', dni='20000000',
            turno=_turno(2), presentados=8, exigidos=8, estado='APTO',
            ultima_revision=date(2026, 9, 1))
        # Todo subido y un estudio rechazado: el papel está presentado.
        self.fila_con_todo_subido_y_uno_rechazado = _f(
            id=3, apellido='Benítez', turno=_turno(1), presentados=8,
            exigidos=8, rechazados=1, estado='REJECTED',
            ultima_revision=date(2026, 10, 20))
        # Subió ocho sin inscribirse: exigidos desconocido.
        self.fila_sin_turno = _f(
            id=4, apellido='Cruz', presentados=8, exigidos=None,
            estado='NO_WINDOW')
        # Tres con pendientes, seis estudios entre todos.
        self.fila_pre = _f(
            id=5, apellido='Díaz', turno=_turno(1), presentados=3, exigidos=8,
            a_revisar=3, sin_tocar=1, pre_revisados=2, estado='TO_REVIEW',
            subida_mas_vieja_sin_dictamen=_ts(10),
            ultima_revision=date(2026, 8, 1))
        self.fila_con_la_subida_mas_vieja = _f(
            id=6, apellido='Ferrari', turno=_turno(2), presentados=2,
            exigidos=8, a_revisar=2, sin_tocar=2, estado='TO_REVIEW',
            subida_mas_vieja_sin_dictamen=_ts(2))
        self.fila_cruda_2 = _f(
            id=7, apellido='Gil', turno=_turno(2), presentados=1, exigidos=8,
            a_revisar=1, sin_tocar=1, estado='TO_REVIEW',
            subida_mas_vieja_sin_dictamen=_ts(5))
        # Nada esperando, incompleto.
        self.fila_sin_nada_pendiente = _f(
            id=8, apellido='Herrera', turno=_turno(1), presentados=4,
            exigidos=8, estado='INCOMPLETE')
        self.fila_con_vencido_y_rechazado = _f(
            id=9, apellido='Ibarra', turno=_turno(1), presentados=8,
            exigidos=8, vencidos=1, rechazados=1, estado='REJECTED')
        self.filas = [
            self.fila_gomez, self.fila_apto_2,
            self.fila_con_todo_subido_y_uno_rechazado, self.fila_sin_turno,
            self.fila_pre, self.fila_con_la_subida_mas_vieja,
            self.fila_cruda_2, self.fila_sin_nada_pendiente]


def _ids(filas):
    return [f['id'] for f in filas]


class BuscarTests(_Plantel, TestCase):
    def test_busca_por_apellido_nombre_dni_y_grado_en_un_solo_campo(self):
        for texto in ('gomez', 'María', '12.345.675', 'Cabo'):
            self.assertIn(self.fila_gomez, plantel.buscar(self.filas, texto))

    def test_ignora_mayusculas_acentos_y_puntos_del_dni(self):
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, 'GOMEZ'))
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, 'gómez'))
        self.assertIn(self.fila_gomez, plantel.buscar(self.filas, '12345675'))

    def test_no_devuelve_los_que_no_coinciden(self):
        self.assertEqual(plantel.buscar(self.filas, 'gomez'), [self.fila_gomez])

    def test_texto_vacio_o_en_blanco_devuelve_todo(self):
        self.assertEqual(plantel.buscar(self.filas, ''), self.filas)
        self.assertEqual(plantel.buscar(self.filas, '   '), self.filas)
        self.assertEqual(plantel.buscar(self.filas, None), self.filas)

    def test_varias_palabras_deben_coincidir_todas(self):
        self.assertEqual(plantel.buscar(self.filas, 'cabo maria'),
                         [self.fila_gomez])
        self.assertEqual(plantel.buscar(self.filas, 'cabo luis'), [])

    def test_un_dni_parcial_sin_puntos_encuentra(self):
        self.assertEqual(plantel.buscar(self.filas, '2345'), [self.fila_gomez])

    def test_conserva_el_orden_de_entrada(self):
        # 'a' está en Álvarez, Gómez (María), Cruz (Ana)...: más de uno.
        self.assertEqual(_ids(plantel.buscar(self.filas, 'ana')),
                         [3, 4, 5, 6, 7, 8])


class FiltrarTests(_Plantel, TestCase):
    def test_documentacion_completa_no_mira_el_dictamen(self):
        # Spec §8.1: un rechazado cuenta como completo, el papel está presentado.
        completas = plantel.filtrar(self.filas, filtro='completa')
        self.assertIn(self.fila_con_todo_subido_y_uno_rechazado, completas)

    def test_sin_turno_se_filtra_con_el_literal_sin(self):
        self.assertEqual(plantel.filtrar(self.filas, turno='sin'),
                         [self.fila_sin_turno])

    def test_el_de_exigidos_desconocido_no_cuenta_como_completo(self):
        self.assertNotIn(self.fila_sin_turno,
                         plantel.filtrar(self.filas, filtro='completa'))

    def test_el_de_exigidos_desconocido_es_incompleto(self):
        self.assertIn(self.fila_sin_turno,
                      plantel.filtrar(self.filas, filtro='incompleta'))

    def test_completa_e_incompleta_se_reparten_todo(self):
        c = plantel.filtrar(self.filas, filtro='completa')
        i = plantel.filtrar(self.filas, filtro='incompleta')
        self.assertEqual(len(c) + len(i), len(self.filas))
        self.assertEqual(_ids(c), [1, 2, 3])

    def test_pendientes_son_los_de_a_revisar_mayor_a_cero(self):
        self.assertEqual(
            _ids(plantel.filtrar(self.filas, filtro='pendientes')), [5, 6, 7])

    def test_todos_o_sin_filtro_no_filtra(self):
        self.assertEqual(plantel.filtrar(self.filas, filtro='todos'), self.filas)
        self.assertEqual(plantel.filtrar(self.filas), self.filas)

    def test_por_turno_compara_el_id(self):
        self.assertEqual(_ids(plantel.filtrar(self.filas, turno=2)), [2, 6, 7])

    def test_filtro_y_turno_se_combinan(self):
        self.assertEqual(
            _ids(plantel.filtrar(self.filas, filtro='pendientes', turno=2)),
            [6, 7])

    def test_filtro_desconocido_falla(self):
        with self.assertRaises(ValueError):
            plantel.filtrar(self.filas, filtro='inventado')


class ContarTests(_Plantel, TestCase):
    def test_cuenta_buzos_y_no_estudios(self):
        # Tres buzos con pendientes, que entre todos suman seis estudios.
        self.assertEqual(plantel.contar(self.filas)['a_revisar'], 3)

    def test_un_buzo_cae_en_un_solo_contador(self):
        # Con un vencido y un rechazado, DiverState lo manda a REJECTED:
        # sale de "vencidos" y no hay doble conteo.
        c = plantel.contar([self.fila_con_vencido_y_rechazado])
        self.assertEqual(c['vencidos'], 0)

    def test_vencidos_cuenta_buzos_de_estado_expired_y_no_estudios(self):
        vencido = _f(id=10, estado='EXPIRED', vencidos=2)
        self.assertEqual(plantel.contar(self.filas + [vencido])['vencidos'], 1)

    def test_contar_sobre_lo_filtrado_da_lo_filtrado(self):
        del_turno = plantel.filtrar(self.filas, turno=self.turno_1ra)
        self.assertEqual(plantel.contar(del_turno)['aptos'], 1)
        self.assertEqual(plantel.contar(self.filas)['aptos'], 2)

    def test_por_filtro_trae_los_cuatro_conteos(self):
        self.assertEqual(plantel.contar(self.filas)['por_filtro'], {
            'todos': 8, 'completa': 3, 'incompleta': 5, 'pendientes': 3})

    def test_lista_vacia_da_ceros(self):
        self.assertEqual(plantel.contar([]), {
            'aptos': 0, 'a_revisar': 0, 'vencidos': 0,
            'por_filtro': {'todos': 0, 'completa': 0, 'incompleta': 0,
                           'pendientes': 0}})


class OrdenarTests(_Plantel, TestCase):
    def test_pila_rapida_pone_primero_lo_pre_revisado(self):
        primera = plantel.ordenar(self.filas, 'pila_rapida')[0]
        self.assertGreater(primera['pre_revisados'], 0)

    def test_pila_rapida_pone_mas_pre_revisados_antes(self):
        menos = _f(id=11, apellido='Aaa', a_revisar=1, pre_revisados=1,
                   estado='TO_REVIEW')
        orden = plantel.ordenar(self.filas + [menos], 'pila_rapida')
        self.assertEqual(_ids(orden[:2]), [5, 11])

    def test_pila_cruda_pone_primero_la_subida_mas_vieja_sin_dictamen(self):
        primera = plantel.ordenar(self.filas, 'pila_cruda')[0]
        self.assertEqual(primera, self.fila_con_la_subida_mas_vieja)

    def test_los_que_no_tienen_nada_esperando_van_al_fondo_en_pila_cruda(self):
        self.assertEqual(plantel.ordenar(self.filas, 'pila_cruda')[-1],
                         self.fila_sin_nada_pendiente)

    def test_pila_cruda_ordena_las_fechas_de_mas_vieja_a_mas_nueva(self):
        orden = plantel.ordenar(self.filas, 'pila_cruda')
        self.assertEqual(_ids(orden[:3]), [6, 7, 5])

    def test_apellido_ignora_acentos_y_mayusculas(self):
        orden = plantel.ordenar(
            [_f(id=1, apellido='Zeta'), _f(id=2, apellido='álvarez'),
             _f(id=3, apellido='Bravo')], 'apellido')
        self.assertEqual(_ids(orden), [2, 3, 1])

    def test_apellido_desempata_por_nombre(self):
        orden = plantel.ordenar(
            [_f(id=1, apellido='Paz', nombre='Zoe'),
             _f(id=2, apellido='Paz', nombre='Ana')], 'apellido')
        self.assertEqual(_ids(orden), [2, 1])

    def test_pendientes_pone_primero_al_de_mas_estudios_por_revisar(self):
        orden = plantel.ordenar(self.filas, 'pendientes')
        self.assertEqual(_ids(orden[:3]), [5, 6, 7])

    def test_ultima_revision_pone_primero_al_que_nunca_fue_revisado(self):
        orden = plantel.ordenar(self.filas, 'ultima_revision')
        self.assertIsNone(orden[0]['ultima_revision'])
        con_fecha = [f['ultima_revision'] for f in orden
                     if f['ultima_revision'] is not None]
        self.assertEqual(con_fecha, sorted(con_fecha))
        self.assertEqual(len(con_fecha), 4)

    def test_criterio_desconocido_falla(self):
        with self.assertRaises(ValueError):
            plantel.ordenar(self.filas, 'inventado')

    def test_no_modifica_la_lista_de_entrada(self):
        copia = list(self.filas)
        plantel.ordenar(self.filas, 'pila_cruda')
        self.assertEqual(self.filas, copia)
