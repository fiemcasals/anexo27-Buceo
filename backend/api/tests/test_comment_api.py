"""El dictamen es la palabra final del médico: nadie más puede fabricarla.

La invariante, como la enunció el dueño del producto: "cada usuario puede borrar
sus estudios si quiere, si despues vuelve a subir otro de todas maneras tiene que
aprobarlo el medico para quedar apto. no hay forma de que queda apto si el medico
no da la palabra final".

El motor de aptitud no guarda la aptitud, la deriva: una fila que dice
``status=APPROVED, reviewer_role=DOCTOR`` **es** la palabra final del médico, y no
hay segunda fuente contra la que cotejarla. `CommentViewSet` no tenía ningún
control en `update` ni en `destroy`, así que el §15.9 —cerrado en la creación— se
eludía por otra puerta, y el registro es abierto y sin verificación de correo.

Cada caso afirma el código de estado **y** el estado de la fila después: un 403
con la fila ya modificada sería un test que pasa por la razón equivocada.
"""

from datetime import date
from smtplib import SMTPException
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from rest_framework.test import APIClient, APITestCase

from api.models import Comment, StudyBlock
from users.models import UserProfile

URL = "/api/comments/"


def _user(username, role):
    user = User.objects.create(username=username)
    UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class DictamenNoSeFabricaTests(APITestCase):
    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.doctor = _user("medico", "DOCTOR")
        self.nurse = _user("enfermero", "NURSE")
        self.stranger = _user("tercero", "USER")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.verdict = Comment.objects.create(
            block=self.block, doctor=self.doctor, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="ILLEGIBLE",
            content="La foto está cortada.")

    def _assert_untouched(self):
        self.verdict.refresh_from_db()
        self.assertEqual(self.verdict.status, "REJECTED")
        self.assertEqual(self.verdict.reviewer_role, "DOCTOR")
        self.assertEqual(self.verdict.rejection_reason, "ILLEGIBLE")
        self.assertEqual(self.verdict.content, "La foto está cortada.")
        self.assertEqual(self.verdict.block_id, self.block.pk)

    FORGERY = {"status": "APPROVED", "reviewer_role": "DOCTOR",
               "rejection_reason": "", "content": ""}

    def test_a_third_party_cannot_forge_the_doctors_approval(self):
        # El agujero tal como se verificó: la fila pasaba de REJECTED a APPROVED
        # con `doctor` todavía apuntando al médico real. 404 porque un tercero no
        # alcanza siquiera a ver el dictamen.
        response = _client(self.stranger).patch(
            f"{URL}{self.verdict.pk}/", self.FORGERY, format="json")
        self.assertEqual(response.status_code, 404, response.content)
        self._assert_untouched()

    def test_a_nurse_who_does_see_the_verdict_still_cannot_rewrite_it(self):
        # El enfermero auxiliar ve los estudios de todos (§5), así que acá el 403
        # lo da la regla y no el queryset: el dictamen del médico no se toca.
        response = _client(self.nurse).patch(
            f"{URL}{self.verdict.pk}/", self.FORGERY, format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self._assert_untouched()

    def test_the_diver_cannot_delete_the_rejection_on_their_own_study(self):
        # No produce aptitud, pero destruye el motivo y el detalle que el §9
        # manda por correo y le permite al buzo ocultar que fue rechazado.
        response = _client(self.diver).delete(f"{URL}{self.verdict.pk}/")
        self.assertEqual(response.status_code, 403, response.content)
        self.assertTrue(Comment.objects.filter(pk=self.verdict.pk).exists())
        self._assert_untouched()

    def test_the_diver_cannot_rewrite_the_rejection_on_their_own_study(self):
        response = _client(self.diver).patch(
            f"{URL}{self.verdict.pk}/", self.FORGERY, format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self._assert_untouched()

    def test_a_verdict_cannot_be_re_pointed_at_another_divers_study(self):
        # Mover una aprobación que el médico sí firmó al estudio de otro buzo le
        # da a ese buzo una palabra final que nadie le dio. `block` es de sólo
        # lectura después de la creación, así que no hay dónde apuntar: lo
        # intenta quien dictaminó, que es el único que puede editar la fila.
        other_block = StudyBlock.objects.create(
            user=_user("buzo2", "USER"), study_code="b",
            study_date=date(2026, 10, 1))
        response = _client(self.doctor).patch(
            f"{URL}{self.verdict.pk}/", {"block": other_block.pk},
            format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["block"], self.block.pk)
        self.verdict.refresh_from_db()
        self.assertEqual(self.verdict.block_id, self.block.pk)

    def test_whoever_ruled_can_correct_their_own_verdict(self):
        response = _client(self.doctor).patch(
            f"{URL}{self.verdict.pk}/", {"content": "Ilegible el renglón 4."},
            format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.verdict.refresh_from_db()
        self.assertEqual(self.verdict.content, "Ilegible el renglón 4.")

    def test_whoever_ruled_can_delete_their_own_verdict(self):
        response = _client(self.doctor).delete(f"{URL}{self.verdict.pk}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(Comment.objects.filter(pk=self.verdict.pk).exists())

    def test_a_third_party_is_not_served_another_divers_verdicts(self):
        # El motivo y el detalle de un rechazo son la revisión médica: §5, nadie
        # más que el revisor designado y el propio buzo los ve.
        response = _client(self.stranger).get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [])

    def test_the_diver_is_served_the_verdicts_on_their_own_studies(self):
        # §6: el detalle se le muestra textual al buzo, es lo que le dice qué
        # tiene que arreglar.
        response = _client(self.diver).get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["id"] for row in response.json()],
                         [self.verdict.pk])


class ExRevisorTests(APITestCase):
    """§5: la facultad es de quien está designado, no de quien lo estuvo.

    El §5 abre con "Cuatro roles. El admin los designa." y condiciona la
    facultad a la designación en presente: el médico y el enfermero auxiliar son
    "designado por el admin". La tabla tiene cuatro filas y no tiene una para
    "ex-médico": a quien el admin le saca la designación, el §5 lo pone en la
    fila "Buzo | Ve y gestiona sus propios estudios. **Nada más.**", que es la
    única del cuadro que cierra con una negación.

    `SoloQuienDictamino` dejaba editar y borrar el propio dictamen sin volver a
    comprobar la designación. Lo que eso habilitaba no era corregir una errata:
    el enfermero al que le sacaron la designación convertía su pre-aprobación en
    la aprobación del médico, y el motor la lee como tal. La asimetría era la
    pista de que algo estaba mal — el ex-revisor ya no podía **ver** el estudio
    pero sí reescribir el dictamen sobre ese estudio.

    El argumento de "que pueda corregir lo que firmó" se conserva entero para
    todo el que siga designado (`test_whoever_ruled_can_correct_their_own_verdict`)
    y para la lectura, que no se toca.
    """

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.nurse = _user("enfermero", "NURSE")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.verdict = Comment.objects.create(
            block=self.block, doctor=self.nurse, reviewer_role="NURSE",
            status="PRE_APPROVED")

    def _undesignate(self):
        """El admin le saca la designación, y devuelve un cliente nuevo.

        Nuevo a propósito: el `User` que `force_authenticate` guarda cachea su
        `profile` en la primera lectura, así que reusar el cliente mediría el
        caché y el test pasaría con el agujero abierto.
        """
        profile = UserProfile.objects.get(user=self.nurse)
        profile.role = "USER"
        profile.save()
        return _client(User.objects.get(pk=self.nurse.pk))

    def _assert_untouched(self):
        self.verdict.refresh_from_db()
        self.assertEqual(self.verdict.status, "PRE_APPROVED")
        self.assertEqual(self.verdict.reviewer_role, "NURSE")

    def test_an_ex_reviewer_cannot_turn_their_pre_approval_into_an_approval(self):
        response = self._undesignate().patch(
            f"{URL}{self.verdict.pk}/",
            {"status": "APPROVED", "reviewer_role": "DOCTOR"}, format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self._assert_untouched()

    def test_an_ex_reviewer_cannot_delete_the_verdict_they_signed(self):
        response = self._undesignate().delete(f"{URL}{self.verdict.pk}/")
        self.assertEqual(response.status_code, 403, response.content)
        self.assertTrue(Comment.objects.filter(pk=self.verdict.pk).exists())

    def test_an_ex_reviewer_is_still_shown_what_they_signed(self):
        # La lectura no se toca: lo que uno firmó es parte del registro y
        # ocultárselo no protege a nadie. `get_queryset` conserva `Q(doctor=user)`.
        response = self._undesignate().get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["id"] for row in response.json()],
                         [self.verdict.pk])


class ElRolDelDictamenEsElRealTests(APITestCase):
    """§6: "Lo único que el médico no puede delegar es decir que alguien está apto."

    `reviewer_role` lo mandaba el cliente y nada lo cotejaba contra el rol real
    del perfil: `perform_create` comprobaba que el usuario fuera **uno de los
    dos** roles revisores y después confiaba en el cuerpo del pedido. Un
    enfermero designado posteaba `{status: APPROVED, reviewer_role: DOCTOR}` y la
    fila quedaba indistinguible de la palabra final del médico — el §5 le dice
    expresamente "**No puede declarar apto.**", y `fitness.py` deriva el estado
    de esa fila contando `reviewer_role == DOCTOR`.

    La `CheckConstraint verdict_matches_reviewer_role` no lo atrapaba porque
    acopla el estado con el rol **declarado**, no con el real.
    """

    URL = "/api/comments/"

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.doctor = _user("medico", "DOCTOR")
        self.nurse = _user("enfermero", "NURSE")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))

    def _post(self, user, **payload):
        payload.setdefault("block", self.block.pk)
        return _client(user).post(self.URL, payload, format="json")

    def test_a_nurse_cannot_declare_a_diver_fit_by_declaring_themselves_doctor(self):
        response = self._post(
            self.nurse, status="APPROVED", reviewer_role="DOCTOR")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Comment.objects.count(), 0)

    def test_the_stored_role_is_the_designated_one_not_the_declared_one(self):
        response = self._post(
            self.nurse, status="PRE_APPROVED", reviewer_role="DOCTOR")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Comment.objects.get().reviewer_role, "NURSE")

    def test_a_nurse_cannot_pre_approve_the_same_study_twice(self):
        primera = self._post(self.nurse, status="PRE_APPROVED")
        self.assertEqual(primera.status_code, 201, primera.content)
        segunda = self._post(self.nurse, status="PRE_APPROVED")
        self.assertEqual(segunda.status_code, 400, segunda.content)
        self.assertEqual(Comment.objects.count(), 1)

    def test_after_a_reversion_the_study_can_be_pre_approved_again(self):
        Comment.objects.create(
            block=self.block, doctor=self.nurse, reviewer_role="NURSE",
            status="PRE_APPROVED")
        Comment.objects.create(
            block=self.block, doctor=self.doctor, reviewer_role="DOCTOR",
            status="REVERTED")
        respuesta = self._post(self.nurse, status="PRE_APPROVED")
        self.assertEqual(respuesta.status_code, 201, respuesta.content)

    def test_the_doctor_cannot_pre_approve(self):
        # La pre-aprobación es el acto del enfermero (§6). Con el rol derivado
        # del perfil, el pareo lo tiene que rechazar la API con 400, no la
        # CheckConstraint con un 500.
        response = self._post(
            self.doctor, status="PRE_APPROVED", reviewer_role="NURSE")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Comment.objects.count(), 0)

    def test_the_doctors_approval_still_works_and_is_signed_as_doctor(self):
        response = self._post(self.doctor, status="APPROVED")
        self.assertEqual(response.status_code, 201, response.content)
        verdict = Comment.objects.get()
        self.assertEqual(verdict.reviewer_role, "DOCTOR")
        self.assertEqual(verdict.doctor, self.doctor)

    def test_a_nurse_can_still_reject(self):
        # Rechazar lo pueden los dos (§5): el pareo no se pasó de restrictivo.
        response = self._post(
            self.nurse, status="REJECTED", rejection_reason="ILLEGIBLE",
            content="La foto está cortada.")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Comment.objects.get().reviewer_role, "NURSE")


class UnRechazoExigeMotivoYDetalleTests(APITestCase):
    """Hoy un rechazo sin motivo pasaba el serializador y reventaba contra la
    CheckConstraint `rejection_has_reason_and_detail` como IntegrityError, o
    sea un 500. Es el POST exacto que manda el diálogo de rechazo."""

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.doctor = _user("medico", "DOCTOR")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))

    def post(self, **payload):
        payload.setdefault("block", self.block.pk)
        return _client(self.doctor).post(URL, payload, format="json")

    def test_rechazar_sin_motivo_da_400_y_no_500(self):
        r = self.post(status="REJECTED", rejection_reason="", content="")
        self.assertEqual(r.status_code, 400)
        self.assertIn("rejection_reason", r.data)
        self.assertEqual(Comment.objects.count(), 0)

    def test_rechazar_sin_detalle_da_400(self):
        r = self.post(
            status="REJECTED", rejection_reason="ILLEGIBLE", content="")
        self.assertEqual(r.status_code, 400)
        self.assertIn("content", r.data)

    def test_un_detalle_en_blanco_no_es_un_detalle(self):
        r = self.post(
            status="REJECTED", rejection_reason="ILLEGIBLE", content="   ")
        self.assertEqual(r.status_code, 400)
        self.assertIn("content", r.data)

    def test_rechazar_sin_mandar_los_campos_da_400(self):
        r = self.post(status="REJECTED")
        self.assertEqual(r.status_code, 400)
        self.assertIn("rejection_reason", r.data)

    def test_una_aprobacion_no_lleva_motivo(self):
        r = self.post(status="APPROVED", rejection_reason="ILLEGIBLE")
        self.assertEqual(r.status_code, 400)
        self.assertIn("rejection_reason", r.data)

    def test_un_patch_no_puede_dejar_un_rechazo_sin_detalle(self):
        verdict = Comment.objects.create(
            block=self.block, doctor=self.doctor, reviewer_role="DOCTOR",
            status="REJECTED", rejection_reason="ILLEGIBLE", content="Cortada.")
        r = _client(self.doctor).patch(
            f"{URL}{verdict.pk}/", {"content": ""}, format="json")
        self.assertEqual(r.status_code, 400)
        verdict.refresh_from_db()
        self.assertEqual(verdict.content, "Cortada.")


class ElCorreoDeRechazoTests(APITestCase):
    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.diver.email = "buzo1@example.com"
        self.diver.save()
        self.doctor = _user("medico", "DOCTOR")
        self.nurse = _user("enfermero", "NURSE")
        self.block = StudyBlock.objects.create(
            user=self.diver, study_code="b", study_date=date(2026, 10, 1))
        self.titulo_del_estudio = self.block.title

    def rechazar(self, como=None, **extra):
        payload = {
            "block": self.block.pk, "status": "REJECTED",
            "rejection_reason": "ILLEGIBLE", "content": "Salió cortada.",
        }
        payload.update(extra)
        return _client(como or self.doctor).post(URL, payload, format="json")

    def aprobar(self):
        return _client(self.doctor).post(
            URL, {"block": self.block.pk, "status": "APPROVED"}, format="json")

    def dictamenes_del_punto(self):
        return Comment.objects.filter(block=self.block)

    def test_un_rechazo_manda_un_correo_al_buzo(self):
        self.rechazar()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.diver.email])

    def test_dice_que_estudio_el_motivo_y_el_detalle(self):
        self.rechazar(rejection_reason="ILLEGIBLE", content="Salió cortada.")
        cuerpo = mail.outbox[0].body
        self.assertIn("Documento ilegible", cuerpo)
        self.assertIn("Salió cortada.", cuerpo)
        self.assertIn(self.titulo_del_estudio, cuerpo)

    def test_no_dice_quien_reviso(self):
        # Ni el rol ni el usuario de quien revisó, sea médico o enfermero.
        # "médico" en minúscula no se busca: está en el asunto, que es el
        # nombre del estudio y no el revisor.
        for revisor, datos in (
            (self.doctor, ("medico", "Médico", "DOCTOR")),
            (self.nurse, ("enfermero", "Enfermero", "NURSE")),
        ):
            with self.subTest(revisor=revisor.username):
                mail.outbox.clear()
                self.dictamenes_del_punto().delete()
                self.rechazar(como=revisor)
                correo = mail.outbox[0]
                texto = correo.subject + "\n" + correo.body
                for dato in datos + ("REJECTED", "ILLEGIBLE"):
                    self.assertNotIn(dato, texto)

    def test_el_enlace_sale_de_frontend_url(self):
        with self.settings(FRONTEND_URL="https://ejemplo.test"):
            self.rechazar()
        self.assertIn("https://ejemplo.test", mail.outbox[0].body)

    def test_una_aprobacion_no_manda_nada(self):
        self.aprobar()
        self.assertEqual(len(mail.outbox), 0)

    def test_una_pre_aprobacion_no_manda_nada(self):
        r = _client(self.nurse).post(
            URL, {"block": self.block.pk, "status": "PRE_APPROVED"},
            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(mail.outbox), 0)

    def test_el_rechazo_del_enfermero_tambien_avisa(self):
        self.rechazar(como=self.nurse)
        self.assertEqual(len(mail.outbox), 1)

    def test_si_el_correo_falla_el_rechazo_se_guarda_igual(self):
        # El dictamen es lo importante: un servidor de correo caído no puede
        # impedir que el médico trabaje.
        with mock.patch("api.correo.send_mail", side_effect=SMTPException):
            r = self.rechazar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.dictamenes_del_punto().count(), 1)

    def test_el_texto_va_en_impersonal(self):
        self.rechazar()
        correo = mail.outbox[0]
        for palabra in (" tu ", " tus ", "podés", "tenés", "Tu ", "Tus "):
            self.assertNotIn(palabra, correo.body)
            self.assertNotIn(palabra, correo.subject)

    def test_un_buzo_sin_correo_no_rompe_el_rechazo(self):
        self.diver.email = ""
        self.diver.save()
        r = self.rechazar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)

    def test_un_patch_que_convierte_en_rechazo_avisa(self):
        # Un enfermero pre-aprueba y después corrige: rechaza.
        v = Comment.objects.create(
            block=self.block, doctor=self.nurse, reviewer_role="NURSE",
            status="PRE_APPROVED")
        r = _client(self.nurse).patch(
            f"{URL}{v.pk}/",
            {"status": "REJECTED", "rejection_reason": "OTHER",
             "content": "Falta la firma."}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Falta la firma.", mail.outbox[0].body)

    def test_un_patch_que_solo_corrige_el_detalle_no_vuelve_a_avisar(self):
        self.rechazar()
        v = self.dictamenes_del_punto().get()
        r = _client(self.doctor).patch(
            f"{URL}{v.pk}/", {"content": "Salió cortada arriba."},
            format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(mail.outbox), 1)
