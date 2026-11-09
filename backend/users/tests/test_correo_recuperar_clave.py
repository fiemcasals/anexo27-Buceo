from django.core import mail
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   DEFAULT_FROM_EMAIL='casilla@example.com',
                   FRONTEND_URL='https://sitio.example')
class CorreoRecuperarClaveTests(TestCase):
    def test_sale_en_castellano_con_el_enlace_y_desde_la_misma_casilla(self):
        get_user_model().objects.create_user(
            username='buzo@example.com', email='buzo@example.com', password='Clave-12345')
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(user=get_user_model().objects.get(email='buzo@example.com'),
                                    email='buzo@example.com', primary=True, verified=True)
        r = APIClient().post('/api/auth/password/reset/', {'email': 'buzo@example.com'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.subject, 'Recuperación de contraseña')
        self.assertEqual(m.from_email, 'casilla@example.com')
        self.assertIn('https://sitio.example/password-reset/', m.body)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   DEFAULT_FROM_EMAIL='casilla@example.com',
                   FRONTEND_URL='https://sitio.example')
class RecuperarLaClaveDepunta_a_puntaTests(TestCase):
    """Pedir el correo, abrir el enlace y poner la clave nueva. Antes el enlace
    codificaba al usuario en base64 y el servidor lo decodifica en base36: la
    pantalla respondía "Invalid value" aunque el enlace fuera recién pedido."""

    def _enlace(self, email):
        r = APIClient().post('/api/auth/password/reset/', {'email': email}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        enlace = next(l for l in mail.outbox[-1].body.splitlines()
                      if 'password-reset/' in l)
        _, uid, token = enlace.strip().rsplit('/', 2)
        return uid, token

    def _usuario(self, pk=None, email='buzo@example.com'):
        from allauth.account.models import EmailAddress
        datos = {'pk': pk} if pk else {}
        user = get_user_model().objects.create_user(
            username=email, email=email, password='Clave-vieja-12345', **datos)
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
        return user

    def test_el_enlace_del_correo_sirve_para_poner_la_clave_nueva(self):
        user = self._usuario()
        uid, token = self._enlace(user.email)
        r = APIClient().post('/api/auth/password/reset/confirm/', {
            'uid': uid, 'token': token,
            'new_password1': 'Clave-nueva-67890', 'new_password2': 'Clave-nueva-67890',
        }, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Clave-nueva-67890'))

    def test_funciona_con_cualquier_numero_de_usuario(self):
        # En base64 y en base36 un id de una cifra se parecen; con tres cifras
        # y con letras en base36 ya no: probamos varios.
        for pk in (7, 36, 1234, 99999):
            user = self._usuario(pk=pk, email=f'u{pk}@example.com')
            uid, token = self._enlace(user.email)
            r = APIClient().post('/api/auth/password/reset/confirm/', {
                'uid': uid, 'token': token,
                'new_password1': 'Clave-nueva-67890', 'new_password2': 'Clave-nueva-67890',
            }, format='json')
            self.assertEqual(r.status_code, 200, (pk, r.content))

    def test_un_enlace_ya_usado_no_sirve_otra_vez(self):
        user = self._usuario()
        uid, token = self._enlace(user.email)
        cuerpo = {'uid': uid, 'token': token,
                  'new_password1': 'Clave-nueva-67890', 'new_password2': 'Clave-nueva-67890'}
        self.assertEqual(APIClient().post('/api/auth/password/reset/confirm/', cuerpo, format='json').status_code, 200)
        self.assertEqual(APIClient().post('/api/auth/password/reset/confirm/', cuerpo, format='json').status_code, 400)
