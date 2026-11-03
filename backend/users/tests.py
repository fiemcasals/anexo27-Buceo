from datetime import date

from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase

from api.serializers import UserProfileSerializer
from users.models import UserProfile


def _profile(username, **kwargs):
    user = User.objects.create(username=username)
    return UserProfile.objects.create(user=user, **kwargs)


class UserProfileTests(TestCase):
    def test_age_is_a_year_subtraction_not_a_birthday(self):
        # Cumple 40 en diciembre de 2026: en 2026 ya debe los ocho estudios.
        p = _profile("a", dni="1", birth_date=date(1986, 12, 31))
        self.assertEqual(p.age_in_year(2026), 40)

    def test_age_is_none_without_a_birth_date(self):
        self.assertIsNone(_profile("b", dni="2").age_in_year(2026))

    def test_dni_is_unique(self):
        _profile("c", dni="30111222")
        with self.assertRaises(IntegrityError):
            _profile("d", dni="30111222")

    def test_profiles_without_dni_coexist(self):
        # Camino de get_or_create(user=...) en /api/profiles/me/: sin DNI.
        a = UserProfile.objects.get_or_create(user=User.objects.create(username="f"))[0]
        b = UserProfile.objects.get_or_create(user=User.objects.create(username="g"))[0]
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertIsNone(a.dni)
        self.assertIsNone(b.dni)

    def test_nurse_is_a_role(self):
        self.assertIn("NURSE", dict(UserProfile.ROLE_CHOICES))

    def test_rank_is_the_closed_hierarchical_list(self):
        self.assertEqual(
            UserProfile.RANK_VALUES,
            ("GD", "GB", "CY", "CR", "TC", "MY", "CT", "TP", "TT", "ST",
             "SM", "SP", "SA", "SI", "SG", "CI", "CB"),
        )

    def test_ranks_are_grouped_into_officers_and_ncos(self):
        groups = [g for g, _ in UserProfile.RANK_CHOICES]
        self.assertEqual(groups, ["Oficiales", "Suboficiales"])

    def test_profile_is_registered_in_the_django_admin(self):
        from django.contrib import admin
        self.assertIn(UserProfile, admin.site._registry)

    def test_serializer_exposes_birth_date_and_not_age(self):
        p = _profile("e", dni="3", birth_date=date(1990, 5, 1))
        data = UserProfileSerializer(p).data
        self.assertEqual(data["birth_date"], "1990-05-01")
        self.assertNotIn("age", data)
