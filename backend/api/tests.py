from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import UserProfile


class SupportReportTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buzo', email='buzo@ejercito.mil.ar', password='x')
        self.client.force_authenticate(self.user)

    def test_report_mails_support_with_reporter_step_text_and_date(self):
        res = self.client.post('/api/support/', {
            'step': '5. Se puede compartir por correo',
            'message': 'Puse el correo del medico y dice que no existe.',
        }, format='json')

        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(sorted(msg.to), ['mauriciocasals90@gmail.com', 'mheborro@gmail.com'])
        self.assertEqual(msg.reply_to, ['buzo@ejercito.mil.ar'])
        self.assertIn('buzo@ejercito.mil.ar', msg.body)
        self.assertIn('5. Se puede compartir por correo', msg.body)
        self.assertIn('Puse el correo del medico y dice que no existe.', msg.body)
        self.assertIn(timezone.localtime().strftime('%d/%m/%Y'), msg.body)

    def test_report_without_text_is_rejected_and_mails_nobody(self):
        res = self.client.post('/api/support/', {
            'step': '5. Se puede compartir por correo',
            'message': '   ',
        }, format='json')

        self.assertEqual(res.status_code, 400)
        self.assertEqual(mail.outbox, [])


class TermsAcceptanceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buzo2', email='buzo2@ejercito.mil.ar', password='x')
        self.client.force_authenticate(self.user)

    def test_profile_starts_without_terms_accepted(self):
        res = self.client.get('/api/profiles/me/')

        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data['terms_accepted_at'])

    def test_accepting_terms_stamps_the_date_on_the_profile(self):
        res = self.client.post('/api/profiles/accept-terms/')

        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data['terms_accepted_at'])
        self.assertIsNotNone(UserProfile.objects.get(user=self.user).terms_accepted_at)

    def test_terms_date_cannot_be_forged_from_the_profile_form(self):
        self.client.patch('/api/profiles/me/',
                          {'terms_accepted_at': '2020-01-01T00:00:00Z'}, format='json')

        self.assertIsNone(UserProfile.objects.get(user=self.user).terms_accepted_at)
