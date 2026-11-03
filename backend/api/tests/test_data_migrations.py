"""Tests de las dos migraciones de datos que habilitan las constraints.

Las dos rellenan datos preexistentes que, sin ellas, hacen que el `migrate` se
corte a mitad de camino: tanto SQLite como Postgres validan las filas que ya
están cuando se agrega una CHECK o un índice único parcial.

Se prueban con el ejecutor de migraciones de verdad, porque el estado que estas
funciones arreglan es exactamente el que la constraint prohíbe: no se puede
armar con la constraint puesta. Cada caso lleva la base al estado anterior a la
constraint, mete las filas con el modelo histórico de ese estado (que no tiene
el `save()` de hoy, igual que los datos que ya estaban en producción), y después
corre el `migrate` hacia adelante. Que no levante es la mitad del test; la otra
mitad es qué quedó en las filas.

`tearDown` devuelve la base al final del grafo, así que el resto de la suite no
se entera.
"""

from datetime import date
from importlib import import_module
from unittest import mock

from django.db import connection
from django.db.utils import IntegrityError, OperationalError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TransactionTestCase

DEMOTE_MIGRATION = "0014_demote_duplicate_current_studies"
BACKFILL_MIGRATION = "0015_backfill_rejection_reason_and_detail"
ONE_CURRENT_CONSTRAINT = "0009_studyblock_one_current_study_per_diver_and_point"
REJECTION_CONSTRAINT = "0013_comment_verdict_matches_reviewer_role_and_more"
STUDY_CODE_FIELDS = "0008_studyblock_is_current_studyblock_study_code"
REJECTION_REASON_FIELD = (
    "0010_comment_rejection_reason_comment_reviewer_role_and_more"
)


class MigrationTestCase(TransactionTestCase):
    """Base: posiciona la base en `migrate_from` y la deja como estaba."""

    migrate_from: str
    migrate_to: str

    def setUp(self):
        self.target = ("api", self.migrate_to)
        executor = MigrationExecutor(connection)
        executor.migrate([("api", self.migrate_from)])
        executor.loader.build_graph()
        self.old_apps = executor.loader.project_state(
            [("api", self.migrate_from)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def migrate_forward(self):
        """Corre el `migrate` hasta la constraint. Si falla, falla el test."""
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([self.target])
        executor.loader.build_graph()
        return executor.loader.project_state([self.target]).apps

    def _user(self, username):
        return self.old_apps.get_model("auth", "User").objects.create(
            username=username, password="x", is_superuser=False,
            is_staff=False, is_active=True, date_joined="2026-01-01 00:00:00",
        )


class DemoteDuplicateCurrentStudiesTests(MigrationTestCase):
    """0014: deja una sola carga vigente por (buzo, punto)."""

    migrate_from = STUDY_CODE_FIELDS
    migrate_to = ONE_CURRENT_CONSTRAINT

    def setUp(self):
        super().setUp()
        self.StudyBlock = self.old_apps.get_model("api", "StudyBlock")
        self.diver = self._user("buzo1")

    def _row(self, day, code="g", user=None, is_current=True):
        """Carga vigente del punto, sin el `save()` que degrada a la anterior.

        El modelo histórico no lleva métodos, así que esto arma el estado que
        dejó `0008` al marcar `is_current=True` en toda fila preexistente.
        """
        return self.StudyBlock.objects.create(
            user=user or self.diver, study_code=code, study_date=day,
            is_current=is_current, title="", description="", pdf_attachment="",
        )

    def _current_pks(self, code="g", user=None):
        return set(self.StudyBlock.objects.filter(
            user=user or self.diver, study_code=code, is_current=True,
        ).values_list("pk", flat=True))

    def test_without_the_demotion_the_migrate_breaks(self):
        """El hallazgo del revisor: sin el relleno, el `migrate` se corta.

        Vacía las operaciones de 0014 y corre el mismo `migrate`: 0009 levanta
        sobre las filas que ya están. Es lo que prueba que el resto de este
        caso no pasa por casualidad.
        """
        self._row(date(2026, 1, 10))
        self._row(date(2026, 10, 30))
        migration = import_module(f"api.migrations.{DEMOTE_MIGRATION}").Migration
        with mock.patch.object(migration, "operations", []):
            with self.assertRaises((IntegrityError, OperationalError)):
                self.migrate_forward()
        # El `migrate` quedó cortado antes de 0009 y las filas en falta siguen
        # ahí: se las saca para que `tearDown` pueda llevar la base al final.
        self.StudyBlock.objects.all().delete()

    def test_the_migrate_does_not_fail_and_leaves_the_newest_current(self):
        old = self._row(date(2026, 1, 10))
        newest = self._row(date(2026, 10, 30))
        middle = self._row(date(2026, 5, 1))
        self.migrate_forward()
        self.assertEqual(self._current_pks(), {newest.pk})
        for row in (old, middle):
            row.refresh_from_db()
            self.assertFalse(row.is_current)

    def test_a_tie_on_study_date_is_broken_by_the_highest_pk(self):
        self._row(date(2026, 10, 30))
        second = self._row(date(2026, 10, 30))
        self.migrate_forward()
        self.assertEqual(self._current_pks(), {second.pk})

    def test_nothing_is_deleted(self):
        self._row(date(2026, 1, 10))
        self._row(date(2026, 10, 30))
        self.migrate_forward()
        self.assertEqual(self.StudyBlock.objects.count(), 2)

    def test_another_point_and_another_diver_keep_their_current_row(self):
        someone_else = self._user("buzo2")
        other_point = self._row(date(2026, 1, 10), code="b")
        other_diver = self._row(date(2026, 1, 10), user=someone_else)
        self._row(date(2026, 1, 10))
        self._row(date(2026, 10, 30))
        self.migrate_forward()
        for row in (other_point, other_diver):
            row.refresh_from_db()
            self.assertTrue(row.is_current)

    def test_a_slot_with_a_single_current_row_is_left_alone(self):
        only = self._row(date(2026, 1, 10))
        self.migrate_forward()
        only.refresh_from_db()
        self.assertTrue(only.is_current)

    def test_a_row_already_demoted_is_not_promoted(self):
        current = self._row(date(2026, 1, 10))
        demoted = self._row(date(2026, 10, 30), is_current=False)
        self.migrate_forward()
        self.assertEqual(self._current_pks(), {current.pk})
        demoted.refresh_from_db()
        self.assertFalse(demoted.is_current)

    def test_it_is_idempotent(self):
        self._row(date(2026, 1, 10))
        newest = self._row(date(2026, 10, 30))
        apps_after = self.migrate_forward()
        module = import_module(f"api.migrations.{DEMOTE_MIGRATION}")
        module.demote_duplicate_current_studies(apps_after, None)
        self.assertEqual(self._current_pks(), {newest.pk})


class BackfillRejectionReasonTests(MigrationTestCase):
    """0015: todo rechazo preexistente queda con motivo y detalle."""

    # Arranca en 0010 y no en 0012: `migrate` hacia atrás sólo des-aplica los
    # descendientes del destino, y 0015 depende de 0010. Puesto en 0012, 0015
    # quedaría ya aplicada y el test no reproduciría la base vieja de verdad.
    migrate_from = REJECTION_REASON_FIELD
    migrate_to = REJECTION_CONSTRAINT

    def setUp(self):
        super().setUp()
        self.Comment = self.old_apps.get_model("api", "Comment")
        self.reviewer = self._user("medico")
        self.block = self.old_apps.get_model("api", "StudyBlock").objects.create(
            user=self._user("buzo1"), study_code="f",
            study_date=date(2026, 10, 18), title="", description="",
            is_current=True, pdf_attachment="",
        )

    def _dictamen(self, status="REJECTED", reason="", content=""):
        return self.Comment.objects.create(
            block=self.block, doctor=self.reviewer, reviewer_role="DOCTOR",
            status=status, rejection_reason=reason, content=content,
            verified_signature=True,
        )

    def _detail(self):
        return import_module(
            f"api.migrations.{BACKFILL_MIGRATION}").MISSING_DETAIL

    def test_without_the_backfill_the_migrate_breaks(self):
        """El hallazgo del revisor: sin el relleno, el `migrate` se corta.

        Vacía las operaciones de 0015 y corre el mismo `migrate`: la CHECK de
        0013 levanta sobre el rechazo que ya está. Es lo que prueba que el
        resto de este caso no pasa por casualidad.
        """
        self._dictamen(reason="", content="")
        migration = import_module(f"api.migrations.{BACKFILL_MIGRATION}").Migration
        with mock.patch.object(migration, "operations", []):
            with self.assertRaises((IntegrityError, OperationalError)):
                self.migrate_forward()
        # El `migrate` quedó cortado antes de 0013 y el rechazo en falta sigue
        # ahí: se lo saca para que `tearDown` pueda llevar la base al final.
        self.Comment.objects.all().delete()

    def test_a_rejection_without_a_reason_gets_other(self):
        rejection = self._dictamen(reason="", content="Ilegible.")
        self.migrate_forward()
        rejection.refresh_from_db()
        self.assertEqual(rejection.rejection_reason, "OTHER")
        self.assertEqual(rejection.content, "Ilegible.")   # no se pisa

    def test_a_rejection_without_a_detail_says_so_in_spanish(self):
        rejection = self._dictamen(reason="ILLEGIBLE", content="")
        self.migrate_forward()
        rejection.refresh_from_db()
        self.assertEqual(rejection.content, self._detail())
        self.assertIn("no quedó registrado", rejection.content)
        # Registro impersonal: no se dirige al lector.
        self.assertNotIn("Te ", rejection.content)
        self.assertNotIn("tenés", rejection.content)
        self.assertEqual(rejection.rejection_reason, "ILLEGIBLE")  # no se pisa

    def test_a_rejection_with_neither_gets_both(self):
        rejection = self._dictamen(reason="", content="")
        self.migrate_forward()
        rejection.refresh_from_db()
        self.assertEqual(rejection.rejection_reason, "OTHER")
        self.assertEqual(rejection.content, self._detail())

    def test_an_approval_is_left_untouched(self):
        approval = self._dictamen(status="APPROVED", reason="", content="")
        self.migrate_forward()
        approval.refresh_from_db()
        self.assertEqual(approval.rejection_reason, "")
        self.assertEqual(approval.content, "")

    def test_it_is_idempotent(self):
        rejection = self._dictamen(reason="", content="")
        apps_after = self.migrate_forward()
        module = import_module(f"api.migrations.{BACKFILL_MIGRATION}")
        module.backfill_rejection_reason_and_detail(apps_after, None)
        rejection.refresh_from_db()
        self.assertEqual(rejection.rejection_reason, "OTHER")
        self.assertEqual(rejection.content, self._detail())


class MigrationOrderTests(SimpleTestCase):
    """Cada relleno corre antes de la constraint que lo necesita."""

    def setUp(self):
        graph = MigrationLoader(None).graph
        plan = graph.forwards_plan(graph.leaf_nodes("api")[0])
        self.order = [name for app, name in plan if app == "api"]

    def _assert_before(self, first, second):
        self.assertIn(first, self.order)
        self.assertIn(second, self.order)
        self.assertLess(self.order.index(first), self.order.index(second),
                        f"{first} tiene que correr antes que {second}")

    def test_the_demotion_runs_before_the_one_current_constraint(self):
        self._assert_before(DEMOTE_MIGRATION, ONE_CURRENT_CONSTRAINT)

    def test_the_backfill_runs_before_the_rejection_constraint(self):
        self._assert_before(BACKFILL_MIGRATION, REJECTION_CONSTRAINT)

    def test_the_backfill_runs_after_the_field_it_fills_exists(self):
        self._assert_before(REJECTION_REASON_FIELD, BACKFILL_MIGRATION)

    def test_the_demotion_runs_after_the_fields_it_reads_exist(self):
        self._assert_before(STUDY_CODE_FIELDS, DEMOTE_MIGRATION)
