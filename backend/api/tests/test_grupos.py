"""Grupos del CBSFBE: a cuál pertenece cada año, el campeón vigente y su carga."""
from datetime import date
from unittest import mock

from users import grupos
from api.models import GrupoCampeon
from api.tests.test_admin_api import _ConAdmin, _client


class GrupoDeUnAnioTests(_ConAdmin):
    def test_la_tabla_de_la_unidad(self):
        self.assertEqual(grupos.grupo_de(1974), 'INMORTALES')
        self.assertEqual(grupos.grupo_de(1978), 'LEGIONARIOS')
        self.assertEqual(grupos.grupo_de(1989), 'PRETORIANOS')
        self.assertEqual(grupos.grupo_de(2026), 'GLADIADORES')

    def test_un_anio_sin_grupo_no_tiene(self):
        for anio in (1991, 1992, 1997, None):
            self.assertIsNone(grupos.grupo_de(anio))

    def test_el_perfil_trae_el_grupo_y_el_badge_del_campeon(self):
        c = _client(self.buzo)
        perfil = self.buzo.profile
        r = c.patch(f'/api/profiles/{perfil.pk}/', {'basic_course_year': 2020}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['grupo']['codigo'], 'LEGIONARIOS')
        self.assertIsNone(r.data['grupo_campeon'])
        GrupoCampeon.objects.create(year=2025, group='LEGIONARIOS')
        r = c.get('/api/profiles/me/')
        self.assertEqual(r.data['grupo_campeon'], {'anio': 2025})

    def test_el_campeon_vigente_es_el_del_anio_mas_reciente(self):
        GrupoCampeon.objects.create(year=2024, group='LEGIONARIOS')
        GrupoCampeon.objects.create(year=2025, group='INMORTALES')
        perfil = self.buzo.profile
        perfil.basic_course_year = 2020
        perfil.save()
        r = _client(self.buzo).get('/api/profiles/me/')
        self.assertIsNone(r.data['grupo_campeon'])

    def test_el_anio_del_curso_se_valida(self):
        perfil = self.buzo.profile
        for malo in (1950, 2100):
            r = _client(self.buzo).patch(
                f'/api/profiles/{perfil.pk}/', {'basic_course_year': malo}, format='json')
            self.assertEqual(r.status_code, 400)


class CampeonesAdminTests(_ConAdmin):
    URL = '/api/admin/campeones/'

    def test_el_admin_carga_y_corrige_un_anio(self):
        c = _client(self.admin)
        c.put(self.URL, {'year': 2025, 'group': 'PRETORIANOS'}, format='json')
        r = c.put(self.URL, {'year': 2025, 'group': 'GLADIADORES'}, format='json')
        self.assertEqual(r.data['campeones'], [{'year': 2025, 'group': 'GLADIADORES'}])
        self.assertEqual(len(r.data['grupos']), 4)

    def test_un_grupo_inexistente_se_rechaza(self):
        r = _client(self.admin).put(self.URL, {'year': 2025, 'group': 'X'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_un_buzo_no_puede(self):
        r = _client(self.buzo).put(self.URL, {'year': 2025, 'group': 'INMORTALES'}, format='json')
        self.assertEqual(r.status_code, 403)
