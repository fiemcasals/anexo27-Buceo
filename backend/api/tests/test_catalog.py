from django.test import SimpleTestCase
from api import catalog


class CatalogTests(SimpleTestCase):
    def test_holds_the_eight_directive_points_in_order(self):
        self.assertEqual([s.code for s in catalog.ALL], list("abcdefgh"))
        self.assertEqual(catalog.CODES, tuple("abcdefgh"))

    def test_point_f_excludes_chagas_and_lasts_a_year(self):
        f = catalog.get("f")
        self.assertNotIn("CHAGAS", f.text.upper())
        self.assertEqual(f.validity_days, 365)

    def test_only_the_anexo_27_lasts_thirty_days(self):
        self.assertEqual(catalog.get("h").validity_days, 30)
        self.assertTrue(
            all(s.validity_days == 365 for s in catalog.ALL if s.code != "h")
        )

    def test_only_point_a_is_age_conditional(self):
        self.assertEqual(catalog.get("a").min_age, 40)
        self.assertTrue(
            all(s.min_age is None for s in catalog.ALL if s.code != "a")
        )

    def test_under_forty_owes_seven_points(self):
        self.assertEqual(
            [s.code for s in catalog.required_for_age(39)], list("bcdefgh")
        )

    def test_exactly_forty_owes_all_eight(self):
        self.assertEqual(
            [s.code for s in catalog.required_for_age(40)], list("abcdefgh")
        )

    def test_compound_points_carry_an_upload_hint(self):
        self.assertIn("frente y perfil", catalog.get("d").upload_hint)
        self.assertIn("cinco análisis", catalog.get("f").upload_hint)
        self.assertEqual(catalog.get("b").upload_hint, "")

    def test_unknown_code_raises(self):
        with self.assertRaises(KeyError):
            catalog.get("z")
