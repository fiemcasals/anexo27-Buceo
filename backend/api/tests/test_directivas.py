from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from api.models import Directiva
from users.models import UserProfile
from .media_temporal import MEDIA_TEMPORAL

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF'


def _client(role):
    u = User.objects.create(username=role.lower(), email=f'{role}@x.ar')
    UserProfile.objects.create(user=u, role=role)
    c = APIClient()
    c.force_authenticate(u)
    return c


def _pdf(nombre='d.pdf', datos=PDF):
    return SimpleUploadedFile(nombre, datos, content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class DirectivasTests(APITestCase):
    def test_sin_sesion_da_401(self):
        self.assertEqual(APIClient().get('/api/directivas/').status_code, 401)

    def test_admin_carga_y_el_buzo_la_ve_con_titulo_y_enlace(self):
        r = _client('ADMIN').post('/api/directivas/',
                                  {'title': 'Directiva de inmersión', 'file': _pdf()},
                                  format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        lista = _client('USER').get('/api/directivas/').data
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]['title'], 'Directiva de inmersión')
        self.assertTrue(lista[0]['url'].startswith('/media/directivas/'))
        self.assertNotIn('file', lista[0])

    def test_buzo_y_medico_no_cargan_ni_borran(self):
        d = Directiva.objects.create(title='X', file=_pdf())
        for rol in ('USER', 'DOCTOR'):
            c = _client(rol)
            self.assertEqual(c.post('/api/directivas/', {'title': 'Y', 'file': _pdf()},
                                    format='multipart').status_code, 403)
            self.assertEqual(c.delete(f'/api/directivas/{d.pk}/').status_code, 403)
        self.assertEqual(Directiva.objects.count(), 1)

    def test_solo_pdf(self):
        c = _client('ADMIN')
        for nombre, datos in (('a.txt', PDF), ('a.pdf', b'no soy un pdf')):
            r = c.post('/api/directivas/', {'title': 'T', 'file': _pdf(nombre, datos)},
                       format='multipart')
            self.assertEqual(r.status_code, 400)
        self.assertEqual(Directiva.objects.count(), 0)

    def test_titulo_obligatorio(self):
        r = _client('ADMIN').post('/api/directivas/', {'title': '  ', 'file': _pdf()},
                                  format='multipart')
        self.assertEqual(r.status_code, 400)

    def test_admin_borra(self):
        d = Directiva.objects.create(title='X', file=_pdf())
        self.assertEqual(_client('ADMIN').delete(f'/api/directivas/{d.pk}/').status_code, 204)
        self.assertEqual(Directiva.objects.count(), 0)
