"""Tests de la fila del plantel: un buzo convertido en lo que el médico lista."""

from datetime import date, datetime, time

from django.db.models import Prefetch
from django.test import TestCase
from django.utils import timezone

from api import plantel
from api.models import StudyBlock
from api.tests.test_fitness import (
    TODAY, VALID_FOR_EVERY_POINT, _diver, _november_2026, _upload,
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
        # 39 años hoy pero 40 en el año del turno: le corresponden ocho.
        perfil = _diver(birth_year=1986, birth_month=12, birth_day=31,
                        window=_november_2026())
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
        # Un estudio viejo ya dictaminado no puede encabezar la pila cruda.
        perfil = _diver(birth_year=1988, window=_november_2026())
        viejo = _upload(perfil, 'b', VALID_FOR_EVERY_POINT,
                        dictamenes=[('APPROVED', 'DOCTOR')])
        nuevo = _upload(perfil, 'c', VALID_FOR_EVERY_POINT)
        StudyBlock.objects.filter(pk=viejo.pk).update(
            created_at=timezone.make_aware(datetime.combine(date(2026, 1, 1), time(9, 0))))
        nuevo.refresh_from_db()
        fila = self._fila(perfil)
        self.assertEqual(fila['subida_mas_vieja_sin_dictamen'], nuevo.created_at)

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
