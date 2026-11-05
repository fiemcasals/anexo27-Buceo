"""Tests de la fila del plantel: un buzo convertido en lo que el médico lista."""

from datetime import date, datetime, time

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
