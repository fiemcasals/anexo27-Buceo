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
