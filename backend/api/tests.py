from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase

from api.models import AuditorScope, StudyBlock
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


class AuditorScopeTests(APITestCase):
    """Habilitacion por rango de edad desde el panel de administracion."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@ejercito.mil.ar', password='x')
        self.medico = User.objects.create_user(
            username='medico', email='medico@ejercito.mil.ar', password='x')
        self.joven = self._buzo('joven', 23)
        self.veterano = self._buzo('veterano', 40)
        self.sin_edad = self._buzo('sinedad', None)

    def _buzo(self, name, age):
        user = User.objects.create_user(
            username=name, email=f'{name}@ejercito.mil.ar', password='x')
        UserProfile.objects.create(user=user, age=age)
        StudyBlock.objects.create(user=user, title=f'Estudio {name}',
                                  study_date='2026-01-01', pdf_attachment='studies/x.pdf')
        return user

    def _scope(self, level='VIEW', low=22, high=25):
        self.client.force_authenticate(self.admin)
        res = self.client.post('/api/auditor-scopes/', {
            'grantee_email': 'medico@ejercito.mil.ar',
            'access_level': level, 'age_min': low, 'age_max': high,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def test_admin_grants_reader_over_an_age_range_and_only_sees_that_range(self):
        self._scope()

        self.client.force_authenticate(self.medico)
        titles = [b['title'] for b in self.client.get('/api/blocks/').data]

        self.assertEqual(titles, ['Estudio joven'])

    def test_a_diver_who_registers_later_inside_the_range_is_covered(self):
        self._scope()
        nuevo = self._buzo('recluta', 24)

        self.client.force_authenticate(self.medico)
        owners = [b['user'] for b in self.client.get('/api/blocks/').data]

        self.assertIn(nuevo.id, owners)

    def test_profile_without_age_is_not_covered_by_a_bounded_range(self):
        self._scope(low=22, high=None)

        self.client.force_authenticate(self.medico)
        owners = [b['user'] for b in self.client.get('/api/blocks/').data]

        self.assertNotIn(self.sin_edad.id, owners)
        self.assertIn(self.veterano.id, owners)

    def test_reader_level_cannot_write_a_dictamen(self):
        self._scope(level='VIEW')
        block = StudyBlock.objects.get(user=self.joven)

        self.client.force_authenticate(self.medico)
        res = self.client.post('/api/comments/',
                               {'block': block.id, 'content': 'ok', 'status': 'APPROVED'},
                               format='json')

        self.assertEqual(res.status_code, 403)

    def test_auditor_level_can_write_a_dictamen_inside_its_range(self):
        self._scope(level='MODIFY')
        propio = StudyBlock.objects.get(user=self.joven)
        ajeno = StudyBlock.objects.get(user=self.veterano)

        self.client.force_authenticate(self.medico)
        ok = self.client.post('/api/comments/',
                              {'block': propio.id, 'content': 'Apto', 'status': 'APPROVED'},
                              format='json')
        fuera = self.client.post('/api/comments/',
                                 {'block': ajeno.id, 'content': 'Apto', 'status': 'APPROVED'},
                                 format='json')

        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(fuera.status_code, 403)

    def test_the_diver_sees_who_was_enabled_over_them_and_nobody_elses_scope(self):
        self._scope(level='MODIFY')

        self.client.force_authenticate(self.joven)
        visto = self.client.get('/api/auditor-scopes/').data
        self.client.force_authenticate(self.veterano)
        no_visto = self.client.get('/api/auditor-scopes/').data

        self.assertEqual(len(visto), 1)
        self.assertEqual(visto[0]['grantee_details']['email'], 'medico@ejercito.mil.ar')
        self.assertEqual(visto[0]['access_level'], 'MODIFY')
        self.assertEqual(no_visto, [])

    def test_a_regular_user_cannot_grant_or_revoke_scopes(self):
        scope = self._scope()

        self.client.force_authenticate(self.medico)
        creado = self.client.post('/api/auditor-scopes/', {
            'grantee_email': 'medico@ejercito.mil.ar', 'access_level': 'MODIFY',
        }, format='json')
        borrado = self.client.delete(f"/api/auditor-scopes/{scope['id']}/")

        self.assertEqual(creado.status_code, 403)
        self.assertEqual(borrado.status_code, 403)
        self.assertEqual(AuditorScope.objects.count(), 1)

    def test_unknown_email_and_inverted_range_are_rejected(self):
        self.client.force_authenticate(self.admin)

        desconocido = self.client.post('/api/auditor-scopes/', {
            'grantee_email': 'nadie@ejercito.mil.ar', 'access_level': 'VIEW'}, format='json')
        invertido = self.client.post('/api/auditor-scopes/', {
            'grantee_email': 'medico@ejercito.mil.ar', 'access_level': 'VIEW',
            'age_min': 40, 'age_max': 20}, format='json')

        self.assertEqual(desconocido.status_code, 400)
        self.assertEqual(invertido.status_code, 400)
        self.assertEqual(AuditorScope.objects.count(), 0)
