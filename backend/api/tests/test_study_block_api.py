"""Tests del endpoint de estudios: quién los ve, quién los borra, y el historial.

Dos reglas distintas conviven acá y conviene no confundirlas:

- **§6**: el estudio reemplazado "no es visible en la vista normal". La rama creó
  la distinción (`is_current`) y dejó al viewset sirviendo las dos cargas. El
  historial se pide aparte y a propósito, con `?historico=1`.
- **§5**: el acceso sale del rol que designa el admin. El buzo "ve y gestiona sus
  propios estudios, nada más"; el médico y los enfermeros auxiliares "ven los
  estudios de todos"; nadie más ve los de nadie. Antes el acceso lo otorgaba el
  propio buzo con una concesión de `Permission`, que es el circuito inverso: el
  médico designado no veía nada y un buzo podía compartir sus estudios médicos
  con cualquier usuario registrado. `Permission` sigue en pie (§5) y no rige.
"""

from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import Comment, Permission, StudyBlock
from users.models import UserProfile

URL = "/api/blocks/"


def _user(username, role=None):
    """Un usuario con su perfil, o sin perfil si `role` es None.

    Un `UserProfile` no está garantizado para todo `User`: se crea aparte, y
    `/api/profiles/me/` lo hace con `get_or_create`. Sin perfil no hay rol, y la
    falta de rol nunca puede querer decir "ve todo".
    """
    user = User.objects.create(username=username)
    if role is not None:
        UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class StudyBlockVisibilityTests(APITestCase):
    def setUp(self):
        self.diver = _user("buzo1", "USER")
        # La segunda carga degrada a la primera: queda una vigente y un
        # historial, que es lo que pasa cuando el buzo reemplaza un estudio.
        self.replaced = StudyBlock.objects.create(
            user=self.diver, study_code="d", study_date=date(2026, 8, 1))
        self.current = StudyBlock.objects.create(
            user=self.diver, study_code="d", study_date=date(2026, 10, 30))
        self.client = APIClient()
        self.client.force_authenticate(self.diver)

    def _ids(self, query=""):
        response = self.client.get(f"{URL}{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()}

    def test_the_fixture_really_has_one_current_and_one_replaced(self):
        self.replaced.refresh_from_db()
        self.assertFalse(self.replaced.is_current)
        self.assertTrue(self.current.is_current)

    def test_the_normal_view_serves_only_the_current_upload(self):
        self.assertEqual(self._ids(), {self.current.pk})

    def test_the_history_can_be_asked_for_explicitly(self):
        # Sin pantalla ninguna: el plan 2 la va a necesitar.
        self.assertEqual(self._ids("?historico=1"),
                         {self.current.pk, self.replaced.pk})

    def test_any_other_value_of_the_parameter_keeps_the_normal_view(self):
        for query in ("?historico=0", "?historico=", "?historico=si",
                      "?otro=1"):
            with self.subTest(query=query):
                self.assertEqual(self._ids(query), {self.current.pk})

    def test_a_point_with_a_single_current_upload_is_served_either_way(self):
        only = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 9, 1))
        self.assertIn(only.pk, self._ids())
        self.assertIn(only.pk, self._ids("?historico=1"))

    def test_another_divers_uploads_are_not_served(self):
        someone_else = _user("buzo2", "USER")
        theirs = StudyBlock.objects.create(
            user=someone_else, study_code="b", study_date=date(2026, 9, 1))
        self.assertNotIn(theirs.pk, self._ids())
        self.assertNotIn(theirs.pk, self._ids("?historico=1"))

    def test_the_reviewers_wider_view_is_filtered_the_same_way(self):
        # Antes este caso montaba una concesión VIEW del buzo al revisor, que es
        # el circuito que el §5 deroga; lo que sigue siendo verdad, y es lo que
        # el test cuida, es que el filtro del §6 no se escape por la rama amplia.
        reviewer = _user("medico", "DOCTOR")
        client = _client(reviewer)
        response = client.get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual({row["id"] for row in response.json()},
                         {self.current.pk})
        response = client.get(f"{URL}?historico=1")
        self.assertEqual({row["id"] for row in response.json()},
                         {self.current.pk, self.replaced.pk})


class StudyBlockAccessByRoleTests(APITestCase):
    """§5: el acceso lo da el rol, no una concesión entre usuarios."""

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.other_diver = _user("buzo2", "USER")
        self.mine = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.theirs = StudyBlock.objects.create(
            user=self.other_diver, study_code="b", study_date=date(2026, 10, 1))

    def _ids(self, user):
        response = _client(user).get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()}

    def test_a_diver_sees_their_own_studies_and_not_another_divers(self):
        served = self._ids(self.diver)
        self.assertIn(self.mine.pk, served)
        self.assertNotIn(self.theirs.pk, served)

    def test_the_designated_doctor_sees_every_divers_studies(self):
        # Sin esto el médico designado no ve nada: no tiene estudios propios ni
        # concesiones, así que su listado salía vacío.
        self.assertEqual(self._ids(_user("medico", "DOCTOR")),
                         {self.mine.pk, self.theirs.pk})

    def test_a_designated_nurse_sees_every_divers_studies(self):
        self.assertEqual(self._ids(_user("enfermero", "NURSE")),
                         {self.mine.pk, self.theirs.pk})

    def test_a_grant_no_longer_shows_another_divers_studies(self):
        # Cambio de comportamiento deliberado: la concesión existe y no rige.
        Permission.objects.create(
            grantor=self.other_diver, grantee=self.diver,
            access_level="MODIFY", shared_items=["ALL"])
        self.assertNotIn(self.theirs.pk, self._ids(self.diver))

    def test_a_grant_of_a_single_study_no_longer_shows_it_either(self):
        Permission.objects.create(
            grantor=self.other_diver, grantee=self.diver,
            access_level="VIEW", shared_items=[self.theirs.pk])
        self.assertNotIn(self.theirs.pk, self._ids(self.diver))

    def test_a_user_without_a_profile_row_gets_no_access_and_no_500(self):
        # Sin perfil no hay rol: no es revisor. Nunca lo contrario.
        self.assertEqual(self._ids(_user("sin_perfil")), set())

    def test_an_admin_role_is_not_a_reviewer_of_studies(self):
        # §5: el admin ve la lista de usuarios y designa; no revisa estudios.
        self.assertEqual(self._ids(_user("admin", "ADMIN")), set())


class StudyBlockDeletionTests(APITestCase):
    """La mitad de la regla que no se restringe, y la que sí.

    El dueño del producto: "cada usuario puede borrar sus estudios si quiere, si
    despues vuelve a subir otro de todas maneras tiene que aprobarlo el medico
    para quedar apto". Borrar el estudio propio es diseño: el dictamen se va en
    cascada, el punto queda faltante y el buzo queda incompleto, nunca apto.
    """

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.other_diver = _user("buzo2", "USER")
        self.doctor = _user("medico", "DOCTOR")
        self.mine = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.verdict = Comment.objects.create(
            block=self.mine, doctor=self.doctor, reviewer_role="DOCTOR",
            status="APPROVED")

    def test_the_diver_can_delete_their_own_study_and_the_verdict_cascades(self):
        response = _client(self.diver).delete(f"{URL}{self.mine.pk}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(StudyBlock.objects.filter(pk=self.mine.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.verdict.pk).exists())

    def test_a_diver_cannot_delete_another_divers_study(self):
        response = _client(self.other_diver).delete(f"{URL}{self.mine.pk}/")
        self.assertEqual(response.status_code, 404, response.content)
        self.assertTrue(StudyBlock.objects.filter(pk=self.mine.pk).exists())

    def test_a_grant_does_not_let_a_diver_delete_another_divers_study(self):
        # Verificado contra el código anterior: con una concesión de sólo
        # lectura esto devolvía 204 y borraba el registro médico del grantor.
        Permission.objects.create(
            grantor=self.diver, grantee=self.other_diver,
            access_level="VIEW", shared_items=["ALL"])
        response = _client(self.other_diver).delete(f"{URL}{self.mine.pk}/")
        self.assertEqual(response.status_code, 404, response.content)
        self.assertTrue(StudyBlock.objects.filter(pk=self.mine.pk).exists())

    def test_a_reviewer_who_does_see_the_study_still_cannot_delete_it(self):
        # §5 le da al revisor ver, aprobar y rechazar; no borrar. Acá el 403 lo
        # da la regla y no el queryset, porque el médico sí ve el estudio.
        response = _client(self.doctor).delete(f"{URL}{self.mine.pk}/")
        self.assertEqual(response.status_code, 403, response.content)
        self.assertTrue(StudyBlock.objects.filter(pk=self.mine.pk).exists())

    def test_a_reviewer_who_does_see_the_study_still_cannot_edit_it(self):
        response = _client(self.doctor).patch(
            f"{URL}{self.mine.pk}/", {"study_date": "2020-01-01"},
            format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.study_date, date(2026, 10, 1))


class CommentSelfDictamenApiTests(APITestCase):
    """§15.9 y §5 en la única vía de escritura viva: POST /api/comments/."""

    URL = "/api/comments/"

    def setUp(self):
        self.doctor = _user("medico", "DOCTOR")
        self.other = _user("buzo1", "USER")
        self.client = APIClient()
        self.client.force_authenticate(self.doctor)

    def _block(self, user):
        return StudyBlock.objects.create(
            user=user, study_code="b", study_date=date(2026, 10, 18))

    def _post(self, block, client=None):
        return (client or self.client).post(self.URL, {
            "block": block.id, "status": "APPROVED", "reviewer_role": "DOCTOR",
        }, format="json")

    def test_ruling_on_ones_own_study_is_refused_with_400_on_block(self):
        # El médico de este caso sí está designado: lo que lo detiene es el
        # §15.9, no la falta de rol.
        response = self._post(self._block(self.doctor))
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(list(response.json()), ["block"])
        self.assertEqual(
            response.json()["block"],
            ["Nadie puede dictaminar sobre sus propios estudios."])
        self.assertEqual(Comment.objects.count(), 0)

    def test_a_doctor_ruling_on_another_divers_study_still_works(self):
        # Antes hacía falta una concesión MODIFY del propio buzo; ahora alcanza
        # —y hace falta— que el admin lo haya designado médico.
        response = self._post(self._block(self.other))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Comment.objects.get().doctor, self.doctor)

    def test_a_nurse_can_pre_approve_another_divers_study(self):
        nurse = _user("enfermero", "NURSE")
        response = _client(nurse).post(self.URL, {
            "block": self._block(self.other).id,
            "status": "PRE_APPROVED", "reviewer_role": "NURSE",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Comment.objects.get().doctor, nurse)

    def test_the_serializer_without_a_request_does_not_crash(self):
        from api.serializers import CommentSerializer
        serializer = CommentSerializer(data={
            "block": self._block(self.doctor).id,
            "status": "APPROVED", "reviewer_role": "DOCTOR"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_someone_who_is_not_a_designated_reviewer_is_refused_with_403(self):
        # Antes este caso era "un revisor sin concesión": lo que rechazaba era
        # la falta de permiso del buzo. Ahora, la falta de designación.
        plain = _user("buzo2", "USER")
        response = self._post(self._block(self.other), _client(plain))
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(Comment.objects.count(), 0)

    def test_a_grant_does_not_let_a_plain_diver_rule_on_another_study(self):
        # Antes este caso medía la granularidad de la concesión, que ya no rige.
        # Lo que hay que fijar ahora es que la concesión no habilita a dictaminar.
        plain = _user("buzo2", "USER")
        block = self._block(self.other)
        Permission.objects.create(
            grantor=self.other, grantee=plain,
            access_level="MODIFY", shared_items=["ALL"])
        response = self._post(block, _client(plain))
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(Comment.objects.count(), 0)

    def test_a_user_without_a_profile_row_cannot_rule_and_does_not_500(self):
        response = self._post(self._block(self.other), _client(_user("nadie")))
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(Comment.objects.count(), 0)
