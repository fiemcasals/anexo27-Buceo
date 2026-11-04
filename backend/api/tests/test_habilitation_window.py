from datetime import date
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
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

    def _enrolled_diver(self, window, username="buzo"):
        from django.contrib.auth.models import User
        from users.models import UserProfile
        user = User.objects.create_user(username, password="x")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        self.assertIsNone(profile.habilitation_window)   # la inscripción es opcional
        profile.habilitation_window = window
        profile.save()
        return profile

    def test_deleting_a_window_with_divers_on_it_is_refused(self):
        # El administrador acá es un oficial de la unidad, y perder 50
        # inscripciones sin rastro es peor que recibir "corregí las fechas".
        # Además el §4.1 dice que las fechas se completan después, o sea que el
        # flujo real es editar, no borrar y recrear.
        w = _november_2026()
        profile = self._enrolled_diver(w)
        self.assertEqual(list(w.divers.all()), [profile])
        with self.assertRaises(ProtectedError):
            w.delete()
        self.assertTrue(HabilitationWindow.objects.filter(pk=w.pk).exists())
        profile.refresh_from_db()
        self.assertEqual(profile.habilitation_window, w)

    def test_deleting_a_window_with_nobody_on_it_still_works(self):
        # Borrar una ventana recién creada por error sigue funcionando, que es
        # justo cuando borrar es inofensivo.
        w = _november_2026()
        w.delete()
        self.assertFalse(HabilitationWindow.objects.filter(pk=w.pk).exists())

    def test_a_window_is_deletable_once_its_divers_un_enrol(self):
        w = _november_2026()
        profile = self._enrolled_diver(w)
        profile.habilitation_window = None
        profile.save()
        w.delete()
        self.assertFalse(HabilitationWindow.objects.filter(pk=w.pk).exists())
