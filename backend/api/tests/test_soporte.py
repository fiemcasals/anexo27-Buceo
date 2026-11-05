"""El boton Soporte manda el reporte por correo y no lo guarda en la base.

Lo que se reporta es que la aplicacion no funciona, asi que el camino de salida
no puede depender de la aplicacion.
"""
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SUPPORT_RECIPIENTS=['soporte@ejemplo.com', 'otro@ejemplo.com'],
)
class SoporteTests(TestCase):
    def setUp(self):
        self.buzo = User.objects.create_user(
            username='buzo@ejemplo.com', email='buzo@ejemplo.com', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.buzo)

    def test_manda_el_correo_a_todos_los_destinatarios(self):
        r = self.client.post('/api/support/', {
            'message': 'No puedo subir el electrocardiograma',
            'step': 'Cargar un estudio',
        }, format='json')

        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertEqual(enviado.to, ['soporte@ejemplo.com', 'otro@ejemplo.com'])
        self.assertIn('Cargar un estudio', enviado.subject)
        # Quien reporta y que reporto tienen que viajar en el cuerpo: sin eso el
        # correo llega sin con quien contestar.
        self.assertIn('buzo@ejemplo.com', enviado.body)
        self.assertIn('No puedo subir el electrocardiograma', enviado.body)
        self.assertEqual(enviado.reply_to, ['buzo@ejemplo.com'])

    def test_un_mensaje_vacio_se_rechaza_y_no_manda_nada(self):
        r = self.client.post('/api/support/', {'message': '   '}, format='json')

        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_sin_paso_elegido_el_asunto_igual_dice_algo(self):
        r = self.client.post('/api/support/', {'message': 'algo raro'}, format='json')

        self.assertEqual(r.status_code, 201)
        self.assertIn('Otro', mail.outbox[0].subject)

    def test_sin_sesion_no_se_puede_reportar(self):
        r = APIClient().post('/api/support/', {'message': 'hola'}, format='json')

        self.assertEqual(r.status_code, 401)
        self.assertEqual(len(mail.outbox), 0)
