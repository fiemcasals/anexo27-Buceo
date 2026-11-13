from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from users.models import UserProfile


def _user(nombre, role, **extra):
    u = User.objects.create(username=nombre, email=f'{nombre}@x.ar',
                            first_name=nombre.title(), last_name='Ape')
    UserProfile.objects.create(user=u, role=role, **extra)
    return u


def _c(u):
    c = APIClient()
    c.force_authenticate(u)
    return c


class AdminCursosTests(APITestCase):
    def setUp(self):
        self.admin = _user('jefe', 'ADMIN')
        self.valores = [v for v, _ in UserProfile.COURSE_CHOICES]
        a, b = self.valores[0], self.valores[1]
        self.b1 = _user('uno', 'USER', courses=[a, b])
        self.b2 = _user('dos', 'USER', courses=[a])
        self.b3 = _user('tres', 'USER')
        self.medico = _user('doc', 'DOCTOR', courses=[a])

    def test_resumen_cuenta_solo_buzos(self):
        r = _c(self.admin).get('/api/admin/cursos/resumen/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_buzos'], 3)
        self.assertEqual(r.data['sin_cursos'], 1)
        por = {c['valor']: c for c in r.data['cursos']}
        self.assertEqual(por[self.valores[0]]['cantidad'], 2)
        self.assertEqual(por[self.valores[1]]['cantidad'], 1)
        self.assertEqual(len(r.data['cursos']), len(self.valores))

    def test_perfil_del_buzo_marca_los_cursos_hechos(self):
        r = _c(self.admin).get(f'/api/admin/buzos/{self.b1.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c['valor'] for c in r.data['cursos']], self.valores[:2])

    def test_perfil_de_un_no_buzo_da_404(self):
        self.assertEqual(
            _c(self.admin).get(f'/api/admin/buzos/{self.medico.pk}/').status_code, 404)

    def test_solo_el_administrador(self):
        for u in (self.b1, self.medico):
            c = _c(u)
            self.assertEqual(c.get('/api/admin/cursos/resumen/').status_code, 403)
            self.assertEqual(c.get(f'/api/admin/buzos/{self.b2.pk}/').status_code, 403)
        self.assertEqual(APIClient().get('/api/admin/cursos/resumen/').status_code, 401)
