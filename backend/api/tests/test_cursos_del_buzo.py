"""Los cursos de buceo que el buzo declara en su perfil: lista cerrada, y
`Otros` pide escribir cuál (hasta 70 caracteres)."""

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from users.models import UserProfile

ME = "/api/profiles/me/"


def _buzo(username="buzo1"):
    user = User.objects.create(username=username)
    UserProfile.objects.create(user=user, role="USER")
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class CursosDelPerfilTests(APITestCase):
    def setUp(self):
        self.user = _buzo()
        self.client = _client(self.user)

    def guardar(self, **datos):
        return self.client.patch(ME, datos, format="json")

    def test_la_lista_de_opciones_son_las_catorce_en_orden(self):
        r = self.client.get("/api/cursos/")
        self.assertEqual(r.status_code, 200, r.content)
        valores = [c["valor"] for c in r.json()]
        self.assertEqual(len(valores), 14)
        self.assertEqual(valores[0], "BASICO")
        self.assertEqual(valores[-1], "OTROS")
        self.assertEqual(r.json()[0]["etiqueta"],
                         "Curso Básico de Selección y Formación de Buzos de Ejército")

    def test_la_lista_pide_sesion(self):
        self.assertEqual(APIClient().get("/api/cursos/").status_code, 401)

    def test_un_perfil_nuevo_no_tiene_cursos(self):
        cuerpo = self.client.get(ME).json()
        self.assertEqual(cuerpo["courses"], [])
        self.assertEqual(cuerpo["other_course"], "")

    def test_se_guardan_varios_cursos_y_se_leen_de_vuelta(self):
        r = self.guardar(courses=["BASICO", "ALTURA", "C9"])
        self.assertEqual(r.status_code, 200, r.content)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.courses, ["BASICO", "ALTURA", "C9"])
        self.assertEqual(self.client.get(ME).json()["courses"],
                         ["BASICO", "ALTURA", "C9"])

    def test_un_curso_repetido_se_guarda_una_sola_vez(self):
        self.guardar(courses=["ALTURA", "ALTURA", "BASICO"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.courses, ["ALTURA", "BASICO"])

    def test_un_curso_que_no_esta_en_la_lista_se_rechaza(self):
        r = self.guardar(courses=["BASICO", "INVENTADO"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("courses", r.json())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.courses, [])

    def test_courses_tiene_que_ser_una_lista(self):
        self.assertEqual(self.guardar(courses="BASICO").status_code, 400)

    def test_otros_pide_escribir_cual(self):
        r = self.guardar(courses=["OTROS"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("other_course", r.json())
        r = self.guardar(courses=["OTROS"], other_course="   ")
        self.assertEqual(r.status_code, 400, r.content)

    def test_otros_con_texto_se_guarda_sin_espacios_de_mas(self):
        r = self.guardar(courses=["BASICO", "OTROS"],
                         other_course="  Buceo técnico  ")
        self.assertEqual(r.status_code, 200, r.content)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.other_course, "Buceo técnico")

    def test_el_otro_curso_admite_setenta_caracteres_y_no_setenta_y_uno(self):
        self.assertEqual(
            self.guardar(courses=["OTROS"], other_course="x" * 70).status_code, 200)
        r = self.guardar(courses=["OTROS"], other_course="x" * 71)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("other_course", r.json())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.other_course, "x" * 70)

    def test_sin_otros_no_queda_ningun_texto_guardado(self):
        self.guardar(courses=["OTROS"], other_course="Buceo técnico")
        r = self.guardar(courses=["BASICO"], other_course="Buceo técnico")
        self.assertEqual(r.status_code, 200, r.content)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.other_course, "")

    def test_sacar_otros_con_un_patch_que_no_manda_el_texto_tambien_lo_limpia(self):
        self.guardar(courses=["OTROS"], other_course="Buceo técnico")
        self.guardar(courses=["ALTURA"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.other_course, "")

    def test_guardar_otra_cosa_no_toca_los_cursos(self):
        self.guardar(courses=["OTROS", "C9"], other_course="Buceo técnico")
        r = self.guardar(destination="Base Naval")
        self.assertEqual(r.status_code, 200, r.content)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.courses, ["OTROS", "C9"])
        self.assertEqual(self.user.profile.other_course, "Buceo técnico")

    def test_se_pueden_sacar_todos(self):
        self.guardar(courses=["C9"])
        self.assertEqual(self.guardar(courses=[]).status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.courses, [])

    def test_nadie_escribe_los_cursos_de_otro_perfil(self):
        otro = _buzo("buzo2")
        r = self.client.patch(f"/api/profiles/{otro.profile.pk}/",
                              {"courses": ["C9"]}, format="json")
        self.assertIn(r.status_code, (403, 404), r.content)
        otro.profile.refresh_from_db()
        self.assertEqual(otro.profile.courses, [])
