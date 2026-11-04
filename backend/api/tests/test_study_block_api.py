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
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from api.images import ArchivoRechazado, comprimir
from api.models import Comment, HabilitationWindow, Permission, StudyBlock
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
        # Desde que el viewset no admite PATCH ni PUT, lo que lo impide es el
        # método (405) y no el permiso de objeto.
        response = _client(self.doctor).patch(
            f"{URL}{self.mine.pk}/", {"study_date": "2020-01-01"},
            format="json")
        self.assertEqual(response.status_code, 405, response.content)
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


class AccessLevelSaleDelRolTests(APITestCase):
    """`access_level` informa el acceso, así que tiene que informar el del §5.

    `get_access_level` quedó resolviendo por `Permission` después de que el ítem
    4 sacara las concesiones del circuito, así que al revisor designado le
    informaba `"NONE"` sobre los estudios que la propia respuesta le estaba
    sirviendo. No es sólo un campo inexacto: `Dashboard.jsx:477` abre el botón
    "Revisar Auditoría" con `s.access_level === 'MODIFY'`, de modo que el único
    camino de interfaz para escribir un dictamen quedaba oculto justo para el
    médico designado — el backend le aceptaba el dictamen y la pantalla no se lo
    ofrecía.

    `MODIFY` es el valor que en el vocabulario de este código significa "puede
    dictaminar": `Permissions.jsx:262` lo rotula literalmente "Médico". Cuando el
    plan 3 construya la pantalla del médico conviene reemplazar este campo por
    uno honesto; mientras tanto tiene que decir la verdad.
    """

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 18))

    def _level_for(self, user):
        response = _client(user).get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        rows = [r for r in response.json() if r["id"] == self.block.pk]
        self.assertEqual(len(rows), 1, response.content)
        return rows[0]["access_level"]

    def test_the_designated_doctor_is_told_they_can_rule(self):
        self.assertEqual(self._level_for(_user("medico", "DOCTOR")), "MODIFY")

    def test_the_designated_nurse_is_told_they_can_rule(self):
        self.assertEqual(self._level_for(_user("enfermero", "NURSE")), "MODIFY")

    def test_the_owner_is_still_the_owner(self):
        self.assertEqual(self._level_for(self.diver), "OWNER")

    def test_the_reviewer_costs_no_permission_query_per_study(self):
        # El rol alcanza, así que no hace falta preguntarle a `Permission` una
        # vez por fila. Eran N+1 consultas y el listado del médico pasó de 0 a
        # ~1.200 filas, que es lo que el §13 marca como la cosa a vigilar.
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        doctor = _user("medico", "DOCTOR")
        for n in range(3):
            StudyBlock.objects.create(
                user=self.diver, study_code="cdef"[n],
                study_date=date(2026, 10, 18))
        with CaptureQueriesContext(connection) as captured:
            _client(doctor).get(URL)
        sobre_permisos = [q["sql"] for q in captured.captured_queries
                          if "api_permission" in q["sql"]]
        self.assertEqual(sobre_permisos, [])


# Los helpers de archivos se importan de test_images y no se duplican: son los
# que ya fijan qué es una foto, un PDF y un archivo que no es ninguno de los dos,
# y una copia podría desviarse sin que ningún test lo note. Importar sólo los
# helpers (no las clases) evita que el runner corra los tests de imágenes dos veces.
from api.tests.test_images import _archivo, _imagen, _pdf  # noqa: E402


def _estudio(buzo, code, study_date=date(2026, 9, 1)):
    """La carga vigente de un punto, sin dictamen."""
    return StudyBlock.objects.create(
        user=buzo, study_code=code, study_date=study_date)


def _dictamen(block, reviewer, status):
    role = reviewer.profile.role
    extra = ({"content": "Falta la firma.", "rejection_reason": "OTHER"}
             if status == "REJECTED" else {})
    return Comment.objects.create(
        block=block, doctor=reviewer, reviewer_role=role, status=status, **extra)


def _carga(code):
    return {"study_code": code, "study_date": "2026-10-01",
            "pdf_attachment": _pdf()}


class _ConBuzoYRevisores(APITestCase):
    def setUp(self):
        self.buzo = _user("buzo1", "USER")
        self.medico = _user("medico", "DOCTOR")
        self.enfermero = _user("enfermero", "NURSE")
        # Con ventana y fecha de nacimiento los ocho puntos tienen estado: sin
        # ellos todo es NOT_REQUIRED y nada se podría proteger.
        self.ventana = HabilitationWindow.objects.create(
            cycle=2026, slot="FIRST",
            start_date=date(2026, 11, 18), end_date=date(2026, 11, 20))
        UserProfile.objects.filter(user=self.buzo).update(
            birth_date=date(1988, 6, 15), habilitation_window=self.ventana)


class ElPuntoLoDecideElBotonTests(_ConBuzoYRevisores):
    def test_crear_sin_study_code_da_400(self):
        r = _client(self.buzo).post(URL, {
            "study_date": "2026-10-01", "pdf_attachment": _pdf()})
        self.assertEqual(r.status_code, 400)
        self.assertIn("study_code", r.data)

    def test_el_title_que_manda_el_cliente_se_ignora(self):
        r = _client(self.buzo).post(URL, {
            "study_code": "c", "study_date": "2026-10-01",
            "title": "Electrocardiograma de esfuerzo", "pdf_attachment": _pdf()})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(StudyBlock.objects.get(pk=r.data["id"]).title,
                         "Electroencefalograma")

    def test_se_puede_crear_sin_mandar_title(self):
        # El title lo pone el catálogo: el cliente no tiene por qué mandarlo.
        r = _client(self.buzo).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 201, r.content)


class LaFotoSeComprimeAlRecibirlaTests(_ConBuzoYRevisores):
    def test_una_foto_grande_queda_guardada_en_2000_pixeles(self):
        r = _client(self.buzo).post(URL, {
            "study_code": "c", "study_date": "2026-10-01",
            "pdf_attachment": _imagen(4032, 3024, "JPEG")})
        self.assertEqual(r.status_code, 201, r.content)
        bloque = StudyBlock.objects.get(pk=r.data["id"])
        self.addCleanup(bloque.pdf_attachment.delete, save=False)
        with Image.open(bloque.pdf_attachment) as guardada:
            self.assertEqual(max(guardada.size), 2000)

    def test_un_archivo_rechazado_sale_como_400_y_no_como_500(self):
        r = _client(self.buzo).post(URL, {
            "study_code": "c", "study_date": "2026-10-01",
            "pdf_attachment": _archivo(b"PK\x03\x04", "informe.docx")})
        self.assertEqual(r.status_code, 400)
        # El 400 tiene que ser por el archivo y llevar el mensaje de `images`
        # tal cual, no por cualquier otro campo.
        with self.assertRaises(ArchivoRechazado) as ctx:
            comprimir(_archivo(b"PK\x03\x04", "informe.docx"))
        self.assertEqual(str(r.data["pdf_attachment"]), ctx.exception.mensaje)
        self.assertEqual(StudyBlock.objects.count(), 0)


class ElReemplazoTests(_ConBuzoYRevisores):
    def test_se_puede_reemplazar_un_estudio_en_revision(self):
        anterior = _estudio(self.buzo, "c")            # sin dictamen
        self.assertEqual(_client(self.buzo).post(URL, _carga("c")).status_code, 201)
        anterior.refresh_from_db()
        self.assertFalse(anterior.is_current)

    def test_se_puede_reemplazar_uno_pre_revisado(self):
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.enfermero, "PRE_APPROVED")
        self.assertEqual(_client(self.buzo).post(URL, _carga("c")).status_code, 201)

    def test_NO_se_puede_reemplazar_uno_aprobado_por_el_medico(self):
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.medico, "APPROVED")
        r = _client(self.buzo).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 400)
        # Por el punto aprobado y no por otro campo mal armado.
        self.assertIn("study_code", r.data)
        anterior.refresh_from_db()
        self.assertTrue(anterior.is_current)

    def test_el_rechazo_por_aprobado_es_un_error_del_study_code(self):
        _dictamen(_estudio(self.buzo, "c"), self.medico, "APPROVED")
        r = _client(self.buzo).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(list(r.data), ["study_code"])

    def test_el_estudio_aprobado_sigue_siendo_el_vigente_despues_del_rechazo(self):
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.medico, "APPROVED")
        r = _client(self.buzo).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("study_code", r.data)
        # Una sola carga en el punto, y es la aprobada: la nueva no se guardó.
        self.assertEqual(
            list(StudyBlock.objects.filter(user=self.buzo, study_code="c")
                 .values_list("pk", "is_current")),
            [(anterior.pk, True)])

    def test_se_puede_reemplazar_uno_aprobado_pero_vencido(self):
        # La fecha manda sobre el dictamen: el aprobado que venció es EXPIRED y
        # la pantalla le ofrece subirlo; el servidor no puede contestar 400.
        anterior = _estudio(self.buzo, "c", date(2025, 1, 10))
        _dictamen(anterior, self.medico, "APPROVED")
        r = _client(self.buzo).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 201, r.content)
        anterior.refresh_from_db()
        self.assertFalse(anterior.is_current)

    def test_sin_fecha_de_nacimiento_NO_se_puede_reemplazar_uno_aprobado(self):
        # Vaciar un dato del perfil no puede ser la llave para pisar lo que el
        # médico aprobó: sin edad todo punto sería NOT_REQUIRED.
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.medico, "APPROVED")
        UserProfile.objects.filter(user=self.buzo).update(birth_date=None)
        r = _client(User.objects.get(pk=self.buzo.pk)).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("study_code", r.data)
        anterior.refresh_from_db()
        self.assertTrue(anterior.is_current)

    def test_sin_ventana_NO_se_puede_reemplazar_uno_aprobado(self):
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.medico, "APPROVED")
        UserProfile.objects.filter(user=self.buzo).update(habilitation_window=None)
        r = _client(User.objects.get(pk=self.buzo.pk)).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("study_code", r.data)
        anterior.refresh_from_db()
        self.assertTrue(anterior.is_current)

    def test_sin_ventana_se_puede_reemplazar_uno_no_aprobado(self):
        _estudio(self.buzo, "c")
        UserProfile.objects.filter(user=self.buzo).update(habilitation_window=None)
        r = _client(User.objects.get(pk=self.buzo.pk)).post(URL, _carga("c"))
        self.assertEqual(r.status_code, 201, r.content)

    def test_se_puede_reemplazar_uno_rechazado(self):
        _dictamen(_estudio(self.buzo, "c"), self.medico, "REJECTED")
        self.assertEqual(_client(self.buzo).post(URL, _carga("c")).status_code, 201)

    def test_la_aprobacion_de_un_punto_no_frena_la_carga_de_otro(self):
        _dictamen(_estudio(self.buzo, "c"), self.medico, "APPROVED")
        self.assertEqual(_client(self.buzo).post(URL, _carga("d")).status_code, 201)

    def test_la_aprobacion_de_otro_buzo_no_frena_la_carga(self):
        otro = _user("buzo2", "USER")
        _dictamen(_estudio(otro, "c"), self.medico, "APPROVED")
        self.assertEqual(_client(self.buzo).post(URL, _carga("c")).status_code, 201)

    def test_el_dictamen_anterior_queda_en_el_historial(self):
        anterior = _estudio(self.buzo, "c")
        _dictamen(anterior, self.enfermero, "PRE_APPROVED")
        self.assertEqual(_client(self.buzo).post(URL, _carga("c")).status_code, 201)
        anterior.refresh_from_db()
        self.assertFalse(anterior.is_current)
        self.assertTrue(Comment.objects.filter(block=anterior).exists())


class UnEstudioNoSeEditaTests(_ConBuzoYRevisores):
    """Un reemplazo es un POST al mismo punto. PATCH y PUT no existen."""

    def test_el_dueno_no_puede_pisar_su_estudio_aprobado_con_un_patch(self):
        estudio = _estudio(self.buzo, "c")
        _dictamen(estudio, self.medico, "APPROVED")
        r = _client(self.buzo).patch(
            f"{URL}{estudio.pk}/", {"pdf_attachment": _pdf()})
        self.assertEqual(r.status_code, 405, r.content)
        estudio.refresh_from_db()
        self.assertFalse(estudio.pdf_attachment)

    def test_un_patch_sobre_un_estudio_propio_da_405(self):
        estudio = _estudio(self.buzo, "c")
        r = _client(self.buzo).patch(
            f"{URL}{estudio.pk}/", {"study_date": "2026-10-02"}, format="json")
        self.assertEqual(r.status_code, 405, r.content)

    def test_un_put_sobre_un_estudio_propio_da_405(self):
        estudio = _estudio(self.buzo, "c")
        r = _client(self.buzo).put(f"{URL}{estudio.pk}/", _carga("c"))
        self.assertEqual(r.status_code, 405, r.content)

    def test_borrar_y_listar_siguen_andando(self):
        estudio = _estudio(self.buzo, "c")
        self.assertEqual(_client(self.buzo).get(URL).status_code, 200)
        self.assertEqual(
            _client(self.buzo).delete(f"{URL}{estudio.pk}/").status_code, 204)
