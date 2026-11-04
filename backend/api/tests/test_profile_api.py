"""El rol lo designa el admin: nadie se designa a sí mismo.

El §5 abre con "Cuatro roles. **El admin los designa.**", y la fila del buzo dice
"Ve y gestiona sus propios estudios. **Nada más.**"

Hasta el cierre del plan 1, `UserProfile.role` no se leía en ninguna parte de la
API (D-5: `grep "DOCTOR\\|NURSE"` daba cero), así que un campo de rol escribible
por su dueño era cosmético. El acceso por rol lo convirtió en la **única
credencial de autorización del sistema** — y dejó su puerta de escritura abierta:
un `PATCH /api/profiles/me/ {"role": "DOCTOR"}` devolvía 200 y con eso cualquiera,
desde un registro abierto y sin verificación de correo, se hacía médico, leía el
legajo de todos los buzos y firmaba la palabra final.

Lo mismo por la otra cara: `UserProfileViewSet` no tenía permiso a nivel de
objeto y su queryset incluía los perfiles de quien te hubiera concedido
`PERSONAL_DATA`, así que un grantee con una concesión de **sólo lectura** podía
reescribir y borrar el perfil del grantor.

Cada caso afirma el código de estado **y** la fila después: un 200 que no guardó
nada y un 403 con la fila ya cambiada son el mismo test inútil.
"""

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import Permission
from api.views import SoloElDuenoDelPerfil
from users.models import UserProfile

URL = "/api/profiles/"
ME = "/api/profiles/me/"


def _user(username, role="USER"):
    user = User.objects.create(username=username)
    UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class ElRolLoDesignaElAdminTests(APITestCase):
    """§5: el rol no es un dato que el usuario edite de su propio perfil."""

    def setUp(self):
        self.diver = _user("buzo1", "USER")
        self.client = _client(self.diver)

    def _role(self):
        return UserProfile.objects.get(user=self.diver).role

    def test_a_diver_cannot_make_themselves_the_doctor(self):
        response = self.client.patch(ME, {"role": "DOCTOR"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self._role(), "USER")
        self.assertEqual(response.json()["role"], "USER")

    def test_a_diver_cannot_make_themselves_a_nurse_by_the_detail_route(self):
        # `Profile.jsx` guarda con PUT sobre /api/profiles/<pk>/, así que la ruta
        # de detalle es tan real como `me` y necesita la misma cerradura.
        profile = UserProfile.objects.get(user=self.diver)
        response = self.client.patch(
            f"{URL}{profile.pk}/", {"role": "NURSE"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self._role(), "USER")

    def test_a_diver_cannot_make_themselves_an_instructor(self):
        # `is_instructor` lo da el admin por `promote-instructor` (IsAdminUser) y
        # habilita a firmar la bitácora de otros (`Bitacora.jsx:198`).
        response = self.client.patch(ME, {"is_instructor": True}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(UserProfile.objects.get(user=self.diver).is_instructor)

    def test_making_oneself_the_doctor_does_not_open_the_other_divers_studies(self):
        # La consecuencia, no sólo el campo: es por esto que el campo importa.
        from datetime import date

        from api.models import StudyBlock
        other = _user("buzo2", "USER")
        StudyBlock.objects.create(
            user=other, study_code="b", study_date=date(2026, 10, 1))
        self.client.patch(ME, {"role": "DOCTOR"}, format="json")
        # Con un cliente nuevo: el `User` que `force_authenticate` guarda cachea
        # su `profile` en la primera lectura, así que reusar el cliente mide el
        # caché y no la base, y el test pasaría con el agujero abierto.
        response = _client(User.objects.get(pk=self.diver.pk)).get("/api/blocks/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [])

    def test_the_diver_can_still_edit_their_own_real_data(self):
        # La cerradura es sobre el rol, no sobre el perfil: si esto se rompe, el
        # arreglo se pasó de largo y dejó a `Profile.jsx` sin poder guardar.
        response = self.client.patch(
            ME, {"phone": "1122334455", "rank": "SG"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        profile = UserProfile.objects.get(user=self.diver)
        self.assertEqual(profile.phone, "1122334455")
        self.assertEqual(profile.rank, "SG")


class ElPerfilAjenoNoSeTocaTests(APITestCase):
    """El perfil lo escribe y lo borra sólo su dueño.

    Es el hermano de `SoloElDuenoDelEstudio`: el mismo agujero que el cierre del
    plan 1 tapó en `StudyBlock` seguía abierto en `UserProfile`, y acá la fila que
    se podía reescribir era la que ahora decide el acceso de todo el sistema.
    """

    def setUp(self):
        self.grantor = _user("buzo1", "USER")
        self.grantee = _user("buzo2", "USER")
        self.profile = UserProfile.objects.get(user=self.grantor)
        self.profile.dni = "30111222"
        self.profile.save()
        # Una concesión de sólo lectura, la más chica que existe.
        Permission.objects.create(
            grantor=self.grantor, grantee=self.grantee,
            access_level="VIEW", shared_items=["PERSONAL_DATA"])
        self.client = _client(self.grantee)

    def _url(self):
        return f"{URL}{self.profile.pk}/"

    def test_a_grantee_cannot_rewrite_the_grantors_profile(self):
        response = self.client.patch(
            self._url(), {"role": "DOCTOR", "dni": "999"}, format="json")
        self.assertEqual(response.status_code, 404, response.content)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.role, "USER")
        self.assertEqual(self.profile.dni, "30111222")

    def test_a_grantee_cannot_delete_the_grantors_profile(self):
        response = self.client.delete(self._url())
        self.assertEqual(response.status_code, 404, response.content)
        self.assertTrue(UserProfile.objects.filter(pk=self.profile.pk).exists())

    def test_a_grant_no_longer_hands_over_the_profile_either(self):
        # D-5 sacó el mecanismo de concesiones del acceso a los estudios; para
        # los perfiles seguía rigiendo, y es la ruta que D-5 condena: el buzo le
        # entregaba su DNI y su fecha de nacimiento a cualquier usuario
        # registrado.
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            [row["id"] for row in response.json()],
            [UserProfile.objects.get(user=self.grantee).pk])

    def test_the_owner_still_reaches_their_own_profile_by_the_detail_route(self):
        own = UserProfile.objects.get(user=self.grantee)
        response = self.client.patch(
            f"{URL}{own.pk}/", {"phone": "1199887766"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        own.refresh_from_db()
        self.assertEqual(own.phone, "1199887766")


class SoloElDuenoDelPerfilTests(APITestCase):
    """La regla de objeto, aparte del queryset que hoy la hace inalcanzable.

    El queryset sirve sólo el perfil propio, así que por la API un perfil ajeno
    da 404 antes de llegar a la regla. La regla igual tiene que existir y
    discriminar: el §8.1 pide un listado de 150 buzos para el médico, y el plan
    que lo construya va a ensanchar este queryset. Que entonces el médico pueda
    **ver** 150 perfiles no puede significar que pueda reescribirlos.
    """

    def setUp(self):
        self.owner = _user("buzo1", "USER")
        self.other = _user("medico", "DOCTOR")
        self.profile = UserProfile.objects.get(user=self.owner)
        self.regla = SoloElDuenoDelPerfil()

    def _request(self, user, method):
        request = APIClient().request().wsgi_request
        request.user = user
        request.method = method
        return request

    def test_the_owner_may_write_their_own_profile(self):
        self.assertTrue(self.regla.has_object_permission(
            self._request(self.owner, "PATCH"), None, self.profile))

    def test_a_doctor_may_not_write_another_profile(self):
        self.assertFalse(self.regla.has_object_permission(
            self._request(self.other, "PATCH"), None, self.profile))

    def test_a_doctor_may_not_delete_another_profile(self):
        self.assertFalse(self.regla.has_object_permission(
            self._request(self.other, "DELETE"), None, self.profile))

    def test_reading_another_profile_is_not_what_this_rule_governs(self):
        self.assertTrue(self.regla.has_object_permission(
            self._request(self.other, "GET"), None, self.profile))
