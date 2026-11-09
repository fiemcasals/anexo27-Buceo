"""Lo que el administrador de la unidad hace desde la webapp.

Dos cosas, y nada mas: designar al medico y a los enfermeros auxiliares, y
cargar las fechas de habilitacion del ciclo. Hasta ahora las dos vivian solo en
el admin de Django, y lo unico que la webapp ofrecia era dar permisos de
instructor y de superusuario, que son de la bitacora de buceo y no de la
aptitud.

Dos invariantes sostienen este archivo:

1. **El rol `ADMIN` no se asigna por la API.** Un administrador designa
   revisores; no se fabrica otro administrador ni se degrada a si mismo desde
   una pantalla. Eso sigue siendo del admin de Django, que es el unico lugar
   donde el oficial de la unidad tiene esa potestad.

2. **Una fecha de habilitacion cargada aca es un dia solo**, o sea
   `start_date == end_date`. El modelo guarda un rango porque toda vigencia se
   mide contra `end_date`, y el formulario tiene un solo input por lugar del
   ciclo. Si la igualdad se rompe, la habilitacion abarca dias que el
   administrador nunca escribio, y los estudios se evaluan contra un cierre
   invisible.

`hoy` se fija para que ningun caso dependa del dia en que corra la suite.
"""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api.models import HabilitationWindow
from users.models import UserProfile

HOY = date(2026, 11, 4)


def _user(username, role=None, email=None, **kwargs):
    user = User.objects.create(
        username=username, email=email or f'{username}@ara.mil.ar', **kwargs)
    if role is not None:
        UserProfile.objects.create(user=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class _ConAdmin(APITestCase):
    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=HOY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.admin = _user('jefe', 'ADMIN')
        self.buzo = _user('buzo1', 'USER')
        self.medico = _user('doc', 'DOCTOR')
        self.enfermero = _user('vera', 'NURSE')


# --------------------------------------------------------------------------
# Quien entra
# --------------------------------------------------------------------------
class SoloElAdministradorEntraTests(_ConAdmin):
    """El §5 reparte el circuito; estas dos pantallas son del administrador.

    El medico es la maxima autoridad sobre un dictamen y aun asi no designa
    revisores: si pudiera, el reparto de roles dejaria de salir del oficial de
    la unidad. Cada rol se prueba por separado porque un 403 generico no
    distingue "no es administrador" de "no hay sesion".
    """

    def test_el_buzo_no_ve_los_roles(self):
        self.assertEqual(_client(self.buzo).get('/api/admin/roles/').status_code, 403)

    def test_el_medico_no_ve_los_roles(self):
        self.assertEqual(_client(self.medico).get('/api/admin/roles/').status_code, 403)

    def test_el_enfermero_no_ve_los_roles(self):
        self.assertEqual(_client(self.enfermero).get('/api/admin/roles/').status_code, 403)

    def test_sin_sesion_pide_sesion_y_no_prohibe(self):
        # 401 y no 403: la diferencia importa porque el frontend manda al login
        # con el 401 y muestra un mensaje con el 403.
        self.assertEqual(APIClient().get('/api/admin/roles/').status_code, 401)

    def test_el_buzo_no_designa_revisores(self):
        r = _client(self.buzo).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'DOCTOR'})
        self.assertEqual(r.status_code, 403)
        # Y no lo hizo igual: un 403 que ya escribio es peor que ninguno.
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'USER')

    def test_el_buzo_no_carga_fechas(self):
        self.assertEqual(_client(self.buzo).get('/api/admin/fechas/').status_code, 403)

    def test_el_buzo_no_escribe_fechas(self):
        r = _client(self.buzo).put(
            '/api/admin/fechas/', {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(HabilitationWindow.objects.count(), 0)

    def test_un_usuario_sin_perfil_no_es_administrador(self):
        # El perfil se crea aparte del User, asi que la falta de perfil es un
        # estado real. Nunca puede significar "puede todo".
        huerfano = User.objects.create(username='sinperfil')
        self.assertEqual(_client(huerfano).get('/api/admin/roles/').status_code, 403)


# --------------------------------------------------------------------------
# Designar medico y enfermero
# --------------------------------------------------------------------------
class DesignarRevisoresTests(_ConAdmin):
    def test_el_listado_dice_quien_es_medico_y_quien_enfermero(self):
        datos = _client(self.admin).get('/api/admin/roles/').data
        self.assertEqual(
            [u['email'] for u in datos['DOCTOR']], [self.medico.email])
        self.assertEqual(
            [u['email'] for u in datos['NURSE']], [self.enfermero.email])

    def test_el_listado_trae_las_dos_llaves_aunque_no_haya_nadie(self):
        # La pantalla muestra las dos filas siempre; si la llave faltara, la
        # fila del enfermero desapareceria en lugar de decir que no hay.
        UserProfile.objects.filter(role__in=('DOCTOR', 'NURSE')).update(role='USER')
        datos = _client(self.admin).get('/api/admin/roles/').data
        self.assertEqual(datos['DOCTOR'], [])
        self.assertEqual(datos['NURSE'], [])

    def test_el_listado_no_trae_buzos_ni_administradores(self):
        datos = _client(self.admin).get('/api/admin/roles/').data
        correos = {u['email'] for fila in datos.values() for u in fila}
        self.assertNotIn(self.buzo.email, correos)
        self.assertNotIn(self.admin.email, correos)

    def test_el_listado_trae_el_nombre_para_mostrar(self):
        # Por correo no se reconoce a nadie en una unidad de 150 personas.
        self.medico.first_name, self.medico.last_name = 'Elena', 'Ferreyra'
        self.medico.save()
        datos = _client(self.admin).get('/api/admin/roles/').data
        self.assertEqual(datos['DOCTOR'][0]['nombre'], 'Elena FERREYRA')

    def test_el_nombre_para_mostrar_lleva_el_grado_primero(self):
        self.medico.first_name, self.medico.last_name = 'Elena', 'Ferreyra'
        self.medico.save()
        self.medico.profile.rank = 'CT'
        self.medico.profile.save()
        datos = _client(self.admin).get('/api/admin/roles/').data
        self.assertEqual(datos['DOCTOR'][0]['nombre'], 'CT Elena FERREYRA')

    def test_designar_medico_cambia_el_rol(self):
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'DOCTOR'})
        self.assertEqual(r.status_code, 200)
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'DOCTOR')

    def test_designar_enfermero_cambia_el_rol(self):
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'NURSE'})
        self.assertEqual(r.status_code, 200)
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'NURSE')

    def test_volver_a_buzo_es_como_se_quita_el_permiso(self):
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': self.medico.email, 'role': 'USER'})
        self.assertEqual(r.status_code, 200)
        self.medico.profile.refresh_from_db()
        self.assertEqual(self.medico.profile.role, 'USER')

    def test_el_correo_no_distingue_mayusculas(self):
        # El administrador lo escribe a mano mirando una lista en papel.
        r = _client(self.admin).post(
            '/api/admin/roles/',
            {'email': self.buzo.email.upper(), 'role': 'DOCTOR'})
        self.assertEqual(r.status_code, 200)
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'DOCTOR')

    def test_designar_a_alguien_que_no_existe_da_400_por_el_correo(self):
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': 'nadie@ara.mil.ar', 'role': 'DOCTOR'})
        self.assertEqual(r.status_code, 400)
        # Atado a `email` y no suelto: es el campo que el administrador corrige,
        # y un 400 generico no distingue "ese correo no existe" de "ese rol no
        # se puede asignar".
        self.assertIn('email', r.data)

    def test_un_rol_inventado_da_400_por_el_rol(self):
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'JEFE'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('role', r.data)
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'USER')

    def test_el_rol_de_administrador_NO_se_asigna_por_la_api(self):
        """La invariante 1. Es la unica forma de escalar privilegios desde aca.

        Sin esta guarda, cualquier administrador fabrica administradores por
        correo, y el reparto de roles deja de salir del oficial de la unidad.
        """
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'ADMIN'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('role', r.data)
        self.buzo.profile.refresh_from_db()
        self.assertEqual(self.buzo.profile.role, 'USER')

    def test_designar_a_alguien_sin_perfil_le_crea_el_perfil(self):
        huerfano = User.objects.create(
            username='nuevo', email='nuevo@ara.mil.ar')
        r = _client(self.admin).post(
            '/api/admin/roles/', {'email': huerfano.email, 'role': 'DOCTOR'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(huerfano.profile.role, 'DOCTOR')

    def test_designar_no_toca_is_staff_ni_is_superuser(self):
        """Ser medico es del §5; `is_staff` es la puerta del admin de Django.

        Son dos cosas distintas y esta pantalla solo mueve la primera. Si
        designar al medico le abriera el admin de Django, tendria acceso a los
        datos de los 150 buzos por fuera del circuito.
        """
        _client(self.admin).post(
            '/api/admin/roles/', {'email': self.buzo.email, 'role': 'DOCTOR'})
        self.buzo.refresh_from_db()
        self.assertFalse(self.buzo.is_staff)
        self.assertFalse(self.buzo.is_superuser)


# --------------------------------------------------------------------------
# Las fechas de habilitacion
# --------------------------------------------------------------------------
class CargarLasFechasTests(_ConAdmin):
    URL = '/api/admin/fechas/'

    def test_el_listado_trae_los_tres_lugares_del_ciclo(self):
        datos = _client(self.admin).get(self.URL).data
        self.assertEqual(datos['cycle'], HOY.year)
        self.assertEqual(
            [f['slot'] for f in datos['fechas']],
            ['FIRST', 'SECOND', 'COMPLEMENTARY'])

    def test_un_lugar_sin_cargar_viene_en_null_y_no_falta(self):
        # Un ciclo incompleto es el estado normal. Si el lugar sin cargar no
        # viniera, el formulario tendria dos inputs un dia y tres otro.
        datos = _client(self.admin).get(self.URL).data
        self.assertEqual([f['fecha'] for f in datos['fechas']], [None, None, None])

    def test_el_listado_trae_la_etiqueta_en_castellano(self):
        datos = _client(self.admin).get(self.URL).data
        self.assertEqual(
            [f['etiqueta'] for f in datos['fechas']],
            ['1.ª fecha', '2.ª fecha', 'Complementaria'])

    def test_cargar_una_fecha_la_crea(self):
        r = _client(self.admin).put(
            self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        self.assertEqual(r.status_code, 200)
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        self.assertEqual(ventana.start_date, date(2026, 11, 18))

    def test_una_fecha_cargada_aca_es_UN_DIA(self):
        """La invariante 2, y es la que sostiene todo el motor de vigencia.

        El formulario tiene un solo input por lugar del ciclo. El modelo guarda
        un rango y mide cada estudio contra `end_date`. Si `end_date` quedara en
        otro dia, la habilitacion abarcaria dias que nadie escribio.
        """
        _client(self.admin).put(
            self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        self.assertEqual(ventana.start_date, ventana.end_date)
        self.assertEqual(ventana.end_date, date(2026, 11, 18))

    def test_cargar_las_tres_de_una_vez(self):
        r = _client(self.admin).put(self.URL, {
            'cycle': 2026,
            'FIRST': '2026-11-18',
            'SECOND': '2027-04-20',
            'COMPLEMENTARY': '2027-08-05',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            list(HabilitationWindow.objects.filter(cycle=2026)
                 .order_by('start_date').values_list('slot', flat=True)),
            ['FIRST', 'SECOND', 'COMPLEMENTARY'])

    def test_volver_a_cargar_el_mismo_lugar_lo_corrige_y_no_duplica(self):
        # `cycle` + `slot` es unico, asi que un create a secas explotaria con
        # un 500 la segunda vez que el administrador corrige un error de tipeo.
        cliente = _client(self.admin)
        cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        r = cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-25'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(HabilitationWindow.objects.filter(cycle=2026).count(), 1)
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        self.assertEqual(ventana.start_date, date(2026, 11, 25))
        self.assertEqual(ventana.end_date, date(2026, 11, 25))

    def test_corregir_una_fecha_no_desinscribe_a_los_buzos(self):
        """Corregir un tipeo no puede vaciarle la fecha elegida a 150 personas.

        Por eso se actualiza la fila en lugar de borrarla y volver a crearla:
        `habilitation_window` es una FK, y un borrado se la lleva puesta.
        """
        cliente = _client(self.admin)
        cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        perfil = self.buzo.profile
        perfil.habilitation_window = ventana
        perfil.save(update_fields=['habilitation_window'])

        cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-25'}, format='json')

        perfil.refresh_from_db()
        self.assertEqual(perfil.habilitation_window_id, ventana.pk)
        self.assertEqual(perfil.habilitation_window.start_date, date(2026, 11, 25))

    def test_un_lugar_que_no_viene_queda_como_estaba(self):
        cliente = _client(self.admin)
        cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        cliente.put(self.URL, {'cycle': 2026, 'SECOND': '2027-04-20'}, format='json')
        self.assertEqual(
            HabilitationWindow.objects.get(cycle=2026, slot='FIRST').start_date,
            date(2026, 11, 18))

    def test_un_lugar_vacio_no_borra_lo_que_ya_estaba(self):
        """Un input en blanco es "todavia no la cargue", no "borrala".

        Borrar una fecha desinscribe a todos los buzos anotados en ella, y eso
        no puede pasar porque el administrador dejo un campo sin tocar.
        """
        cliente = _client(self.admin)
        cliente.put(self.URL, {'cycle': 2026, 'FIRST': '2026-11-18'}, format='json')
        r = cliente.put(
            self.URL, {'cycle': 2026, 'FIRST': '', 'SECOND': '2027-04-20'},
            format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            HabilitationWindow.objects.filter(cycle=2026, slot='FIRST').exists())

    def test_una_fecha_mal_escrita_da_400_por_ese_lugar(self):
        r = _client(self.admin).put(
            self.URL, {'cycle': 2026, 'FIRST': '18/11/2026'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('FIRST', r.data)
        self.assertEqual(HabilitationWindow.objects.count(), 0)

    def test_un_ciclo_que_no_es_un_año_da_400_por_el_ciclo(self):
        r = _client(self.admin).put(
            self.URL, {'cycle': 'dos mil', 'FIRST': '2026-11-18'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('cycle', r.data)

    def test_sin_ningun_lugar_da_400_y_lo_explica(self):
        # Un PUT que no trae ninguna fecha es un formulario mandado en blanco.
        r = _client(self.admin).put(self.URL, {'cycle': 2026}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_el_listado_de_otro_ciclo_se_pide_por_parametro(self):
        _client(self.admin).put(
            self.URL, {'cycle': 2030, 'FIRST': '2030-11-18'}, format='json')
        datos = _client(self.admin).get(self.URL, {'cycle': 2030}).data
        self.assertEqual(datos['cycle'], 2030)
        self.assertEqual(datos['fechas'][0]['fecha'], '2030-11-18')


class LaFechaCargadaSirveAlBuzoTests(_ConAdmin):
    """Una fecha de un dia tiene que funcionar en la pantalla del buzo.

    Es la costura entre esta pantalla y todo el plan 2: si una ventana de un
    solo dia rompe el motor de vigencia, el administrador carga la fecha y 150
    buzos ven una pantalla equivocada. Se prueba de punta a punta, no por
    unidad, porque el defecto estaria justo en el medio.
    """

    def test_el_buzo_se_puede_inscribir_a_una_fecha_de_un_dia(self):
        _client(self.admin).put(
            '/api/admin/fechas/', {'cycle': 2026, 'FIRST': '2026-12-10'},
            format='json')
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        r = _client(self.buzo).put('/api/mi-fecha/', {'window': ventana.pk})
        self.assertEqual(r.status_code, 200)

    def test_el_estado_del_buzo_se_calcula_contra_esa_fecha(self):
        _client(self.admin).put(
            '/api/admin/fechas/', {'cycle': 2026, 'FIRST': '2026-12-10'},
            format='json')
        ventana = HabilitationWindow.objects.get(cycle=2026, slot='FIRST')
        _client(self.buzo).put('/api/mi-fecha/', {'window': ventana.pk})

        datos = _client(self.buzo).get('/api/mi-estado/').data
        # La fecha elegida llega a la pantalla, y el contador se calculo: sin
        # `end_date` el motor no habria podido medir vigencia ninguna.
        self.assertEqual(datos['fecha_elegida']['start_date'], '2026-12-10')
        self.assertEqual(datos['fecha_elegida']['end_date'], '2026-12-10')
        self.assertIsInstance(datos['faltan'], int)


class ElSuperusuarioNoSeDaPorLaApiTests(_ConAdmin):
    """`POST /api/superusers/promote/` le daba `is_superuser` a quien sea.

    Lo llamaba un formulario de la bitácora de buceo, que es una sección
    aparte del circuito de aptitud. `is_superuser` + `is_staff` es acceso
    total al admin de Django y a los datos de los 150 buzos, y se da desde
    el admin de Django, que es donde el oficial de la unidad lo controla.

    El test existe para que nadie lo reponga sin discutirlo: un endpoint sin
    pantalla que entrega acceso total sigue estando abierto.
    """

    def test_la_ruta_de_superusuario_ya_no_existe(self):
        staff = _user('sistemas', 'ADMIN', is_staff=True)
        r = _client(staff).post(
            '/api/superusers/promote/', {'email': self.buzo.email})
        self.assertIn(r.status_code, (404, 405))

    def test_y_nadie_quedo_superusuario(self):
        staff = _user('sistemas2', 'ADMIN', is_staff=True)
        _client(staff).post('/api/superusers/promote/', {'email': self.buzo.email})
        self.buzo.refresh_from_db()
        self.assertFalse(self.buzo.is_superuser)
        self.assertFalse(self.buzo.is_staff)
