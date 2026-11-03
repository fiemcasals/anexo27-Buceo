from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from api import catalog
from api.models import StudyBlock


class StudyBlockTests(TestCase):
    def setUp(self):
        self.diver = User.objects.create(username="buzo1")

    def _block(self, code="g", day=date(2026, 10, 28)):
        return StudyBlock.objects.create(
            user=self.diver, study_code=code, study_date=day
        )

    def test_uploading_a_replacement_demotes_the_previous_one(self):
        first = self._block()
        second = self._block(day=date(2026, 11, 3))
        first.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_a_replacement_does_not_delete_the_previous_one(self):
        first = self._block()
        self._block(day=date(2026, 11, 3))
        self.assertTrue(StudyBlock.objects.filter(pk=first.pk).exists())

    def test_a_replacement_does_not_touch_another_point(self):
        other = self._block(code="b")
        self._block(code="g")
        self._block(code="g")
        other.refresh_from_db()
        self.assertTrue(other.is_current)

    def test_a_replacement_does_not_touch_another_diver(self):
        someone_else = StudyBlock.objects.create(
            user=User.objects.create(username="buzo2"),
            study_code="g", study_date=date(2026, 10, 1),
        )
        self._block(code="g")
        someone_else.refresh_from_db()
        self.assertTrue(someone_else.is_current)

    def test_resaving_an_old_instance_does_not_demote_the_current_one(self):
        first = self._block()
        second = self._block(day=date(2026, 11, 3))
        # `first` was demoted in the database, but this in-memory copy is stale.
        self.assertTrue(first.is_current)
        first.description = "edited"
        first.save(update_fields=["description"])
        second.refresh_from_db()
        self.assertTrue(second.is_current)

    def test_database_rejects_a_second_current_row_for_the_same_point(self):
        first = self._block()
        self._block(day=date(2026, 11, 3))
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudyBlock.objects.filter(pk=first.pk).update(is_current=True)

    def test_title_comes_from_the_catalog_not_from_free_text(self):
        self.assertEqual(self._block(code="f").title, catalog.get("f").text)

    def test_saving_an_off_catalog_code_refuses_instead_of_storing_a_blank(self):
        # El serializador valida las choices, asi que la API esta a salvo; la
        # consola y la siembra no. Un codigo fuera del catalogo es un error de
        # programacion, no un dato del usuario: corresponde levantar.
        with self.assertRaises(ValueError) as cm:
            StudyBlock.objects.create(
                user=self.diver, study_code="z", study_date=date(2026, 1, 1)
            )
        self.assertIn("z", str(cm.exception))
        self.assertFalse(StudyBlock.objects.filter(study_code="z").exists())

    def test_every_catalog_code_still_saves(self):
        # El contrapunto: la guarda no puede bloquear los ocho codigos reales.
        for code in catalog.CODES:
            with self.subTest(code=code):
                block = StudyBlock.objects.create(
                    user=self.diver, study_code=code, study_date=date(2026, 1, 1)
                )
                self.assertEqual(block.title, catalog.get(code).text)

    def test_study_code_must_be_one_of_the_eight(self):
        with self.assertRaises(ValidationError) as cm:
            StudyBlock(
                user=self.diver, study_code="z", study_date=date(2026, 1, 1)
            ).full_clean()
        self.assertIn("study_code", cm.exception.message_dict)

    def test_every_catalog_code_is_accepted(self):
        for code in catalog.CODES:
            with self.subTest(code=code):
                try:
                    StudyBlock(
                        user=self.diver, study_code=code,
                        study_date=date(2026, 1, 1),
                    ).full_clean()
                except ValidationError as e:
                    self.assertNotIn("study_code", e.message_dict)
