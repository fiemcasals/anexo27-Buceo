"""La lista de usuarios del administrador: ver, borrar, cambiar la clave.

Se gestionan buzos y revisores. Una cuenta de administracion (rol ADMIN o
superusuario) no se borra ni se le cambia la clave desde la webapp: es la forma
mas corta de quedarse con ella.
"""

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from users.models import UserProfile


def _user(username, role=None, **kwargs):
    user = User.objects.create(
        username=username, email=f'{username}@ara.mil.ar',
        first_name=username.title(), last_name='Apellido', **kwargs)
    if role is not None:
        UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class _Base(APITestCase):
    def setUp(self):
        self.admin = _user('jefe', 'ADMIN')
        self.buzo = _user('buzo1', 'USER')
        self.medico = _user('doc', 'DOCTOR')


class QuienEntraTests(_Base):
    def test_sin_sesion_da_401(self):
        self.assertEqual(APIClient().get('/api/admin/usuarios/').status_code, 401)

    def test_buzo_y_medico_reciben_403_en_las_tres(self):
        for quien in (self.buzo, self.medico):
            c = _client(quien)
            self.assertEqual(c.get('/api/admin/usuarios/').status_code, 403)
            self.assertEqual(
                c.delete(f'/api/admin/usuarios/{self.buzo.pk}/').status_code, 403)
            self.assertEqual(
                c.post(f'/api/admin/usuarios/{self.buzo.pk}/clave/',
                       {'password': 'Clave-Nueva-9182'}).status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.buzo.pk).exists())


class ListaTests(_Base):
    def test_lista_a_todos_con_rol_y_marca_de_proteccion(self):
        res = _client(self.admin).get('/api/admin/usuarios/')
        self.assertEqual(res.status_code, 200)
        por_mail = {u['email']: u for u in res.data}
        self.assertEqual(len(res.data), 3)
        self.assertEqual(por_mail['buzo1@ara.mil.ar']['role'], 'USER')
        self.assertFalse(por_mail['buzo1@ara.mil.ar']['protegido'])
        self.assertTrue(por_mail['jefe@ara.mil.ar']['protegido'])

    def test_usuario_sin_perfil_aparece(self):
        _user('sinperfil')
        res = _client(self.admin).get('/api/admin/usuarios/')
        self.assertEqual(len(res.data), 4)


class OrdenTests(_Base):
    def _emails(self, orden=None):
        url = '/api/admin/usuarios/' + (f'?orden={orden}' if orden else '')
        res = _client(self.admin).get(url)
        self.assertEqual(res.status_code, 200)
        return [u['email'].split('@')[0] for u in res.data]

    def test_por_defecto_ordena_por_tipo(self):
        _user('enf', 'NURSE')
        self.assertEqual(self._emails(), ['jefe', 'doc', 'enf', 'buzo1'])

    def test_por_creacion_primero_el_mas_reciente(self):
        from django.utils import timezone
        from datetime import timedelta
        ahora = timezone.now()
        for nombre, dias in (('jefe', 3), ('buzo1', 1), ('doc', 2)):
            User.objects.filter(username=nombre).update(
                date_joined=ahora - timedelta(days=dias))
        self.assertEqual(self._emails('creacion'), ['buzo1', 'doc', 'jefe'])

    def test_por_grado_antiguo_y_moderno_con_los_sin_grado_al_final(self):
        antiguo, moderno = UserProfile.RANK_VALUES[0], UserProfile.RANK_VALUES[-1]
        UserProfile.objects.filter(user=self.buzo).update(rank=moderno)
        UserProfile.objects.filter(user=self.medico).update(rank=antiguo)
        self.assertEqual(self._emails('grado_antiguo'), ['doc', 'buzo1', 'jefe'])
        self.assertEqual(self._emails('grado_moderno'), ['buzo1', 'doc', 'jefe'])

    def test_orden_desconocido_es_400(self):
        res = _client(self.admin).get('/api/admin/usuarios/?orden=raro')
        self.assertEqual(res.status_code, 400)

    def test_la_lista_trae_grado_y_fecha_de_creacion(self):
        res = _client(self.admin).get('/api/admin/usuarios/')
        self.assertIn('grado', res.data[0])
        self.assertRegex(res.data[0]['creado'], r'^\d{4}-\d{2}-\d{2}$')


class BorrarTests(_Base):
    def test_borra_a_un_buzo(self):
        res = _client(self.admin).delete(f'/api/admin/usuarios/{self.buzo.pk}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.buzo.pk).exists())

    def test_no_se_borra_a_si_mismo(self):
        res = _client(self.admin).delete(f'/api/admin/usuarios/{self.admin.pk}/')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_no_borra_a_otro_administrador_ni_a_un_superusuario(self):
        otro = _user('jefe2', 'ADMIN')
        sistemas = _user('sistemas', 'USER', is_superuser=True)
        for victima in (otro, sistemas):
            res = _client(self.admin).delete(f'/api/admin/usuarios/{victima.pk}/')
            self.assertEqual(res.status_code, 403)
            self.assertTrue(User.objects.filter(pk=victima.pk).exists())

    def test_usuario_inexistente_da_404(self):
        self.assertEqual(
            _client(self.admin).delete('/api/admin/usuarios/99999/').status_code, 404)


class ClaveTests(_Base):
    def test_cambia_la_clave_y_cierra_las_sesiones(self):
        Token.objects.create(user=self.buzo)
        res = _client(self.admin).post(
            f'/api/admin/usuarios/{self.buzo.pk}/clave/',
            {'password': 'Clave-Nueva-9182'})
        self.assertEqual(res.status_code, 200)
        self.buzo.refresh_from_db()
        self.assertTrue(self.buzo.check_password('Clave-Nueva-9182'))
        self.assertFalse(Token.objects.filter(user=self.buzo).exists())

    def test_clave_debil_se_rechaza_y_no_cambia_nada(self):
        antes = self.buzo.password
        for mala in ('', '123', 'password'):
            res = _client(self.admin).post(
                f'/api/admin/usuarios/{self.buzo.pk}/clave/', {'password': mala})
            self.assertEqual(res.status_code, 400)
            self.assertIn('password', res.data)
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.password, antes)

    def test_no_toca_la_clave_de_un_administrador(self):
        otro = _user('jefe2', 'ADMIN')
        antes = otro.password
        res = _client(self.admin).post(
            f'/api/admin/usuarios/{otro.pk}/clave/', {'password': 'Clave-Nueva-9182'})
        self.assertEqual(res.status_code, 403)
        otro.refresh_from_db()
        self.assertEqual(otro.password, antes)


class UnaCuentaQueDictaminoNoSeBorraTests(_Base):
    def test_borrar_a_un_medico_con_dictamenes_se_rechaza_y_los_conserva(self):
        from datetime import date
        from api.models import Comment, StudyBlock
        medico = _user('medicoreal', 'DOCTOR')
        buzo = _user('buzoreal', 'USER')
        bloque = StudyBlock.objects.create(
            user=buzo, study_code='b', study_date=date(2026, 10, 1))
        Comment.objects.create(block=bloque, doctor=medico, reviewer_role='DOCTOR',
                               status='APPROVED')
        r = _client(self.admin).delete(f'/api/admin/usuarios/{medico.pk}/')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertTrue(User.objects.filter(pk=medico.pk).exists())
        self.assertEqual(Comment.objects.count(), 1)

    def test_un_medico_sin_dictamenes_se_borra_igual(self):
        medico = _user('medicolibre', 'DOCTOR')
        r = _client(self.admin).delete(f'/api/admin/usuarios/{medico.pk}/')
        self.assertEqual(r.status_code, 204, r.content)
