from datetime import date
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from api.models import HabilitationWindow


def _november_2026():
    return HabilitationWindow.objects.create(
        cycle=2026, slot="FIRST",
        start_date=date(2026, 11, 18), end_date=date(2026, 11, 20),
    )


class HabilitationWindowTests(TestCase):
    def test_anexo_27_window_opens_thirty_days_before_the_last_day(self):
        self.assertEqual(_november_2026().anexo27_earliest_date, date(2026, 10, 21))

    def test_a_single_day_window_is_valid(self):
        w = HabilitationWindow(
            cycle=2026, slot="SECOND",
            start_date=date(2026, 12, 5), end_date=date(2026, 12, 5),
        )
        w.full_clean()  # no levanta

    def test_end_before_start_is_rejected(self):
        w = HabilitationWindow(
            cycle=2026, slot="SECOND",
            start_date=date(2026, 12, 5), end_date=date(2026, 12, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            w.full_clean()
        # Solo falla por el rango: los demás campos son válidos.
        self.assertEqual(set(ctx.exception.message_dict), {"__all__"})

    def test_database_rejects_an_inverted_range(self):
        # El respaldo vale para cualquier vía que se salte full_clean().
        with self.assertRaises(IntegrityError):
            HabilitationWindow.objects.create(
                cycle=2026, slot="SECOND",
                start_date=date(2026, 12, 5), end_date=date(2026, 12, 1),
            )

    def test_duplicate_slot_has_a_spanish_message(self):
        _november_2026()
        dup = HabilitationWindow(
            cycle=2026, slot="FIRST",
            start_date=date(2026, 11, 25), end_date=date(2026, 11, 27),
        )
        with self.assertRaises(ValidationError) as ctx:
            dup.full_clean()
        self.assertIn(
            "Ya existe una fecha con ese lugar en el ciclo.",
            ctx.exception.messages,
        )

    def test_one_window_per_slot_per_cycle(self):
        _november_2026()
        with self.assertRaises(IntegrityError):
            HabilitationWindow.objects.create(
                cycle=2026, slot="FIRST",
                start_date=date(2026, 11, 25), end_date=date(2026, 11, 27),
            )

    def test_an_incomplete_cycle_is_normal(self):
        # Solo la primera cargada: el ciclo incompleto no es un error (spec §4.1).
        w = _november_2026()
        w.full_clean()
        self.assertEqual(HabilitationWindow.objects.filter(cycle=2026).count(), 1)

    def test_the_three_slots_of_a_cycle(self):
        self.assertEqual(
            list(dict(HabilitationWindow.SLOT_CHOICES)),
            ["FIRST", "SECOND", "COMPLEMENTARY"],
        )

    def test_window_is_registered_in_the_django_admin(self):
        from django.contrib import admin
        self.assertIn(HabilitationWindow, admin.site._registry)

    def test_diver_enrolment_is_optional_and_cleared_when_window_is_deleted(self):
        from django.contrib.auth.models import User
        from users.models import UserProfile
        w = _november_2026()
        user = User.objects.create_user("buzo", password="x")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        self.assertIsNone(profile.habilitation_window)
        profile.habilitation_window = w
        profile.save()
        self.assertEqual(list(w.divers.all()), [profile])
        w.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.habilitation_window)
