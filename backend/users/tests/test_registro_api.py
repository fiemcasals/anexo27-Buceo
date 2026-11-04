"""El registro abierto: captura lo que la directiva exige para identificar al buzo.

Cada negativo afirma el código de estado **y la clave del error**: un registro con
seis campos devuelve 400 por cualquiera de ellos, y un test que sólo mira el
código pasa con el campo que dice probar funcionando perfecto y otro roto.
`test_un_registro_completo_se_acepta` es el positivo que impide que los negativos
pasen con un endpoint que rechaza todo.
"""

from datetime import date
from unittest import mock

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from users.models import UserProfile

REGISTRO = '/api/auth/registration/'
CLAVE = 'Clave-Segura-2026'


def _client(user):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def _registrar(**cambios):
    """Registra con un cuerpo completo; `clave=None` quita el campo del cuerpo."""
    datos = {
        'email': 'buzo@b.com',
        'password1': CLAVE,
        'password2': CLAVE,
        'first_name': 'Juan',
        'last_name': 'Perez',
        'dni': '30111222',
        'rank': 'SG',
        'destination': 'Escuela de Buceo',
        'birth_date': '1990-05-01',
    }
    datos.update(cambios)
    if 'email2' not in cambios:
        datos['email2'] = datos['email']
    datos = {k: v for k, v in datos.items() if v is not None}
    return APIClient().post(REGISTRO, datos, format='json')


class LoQueElRegistroExigeTests(APITestCase):
    def test_un_registro_completo_se_acepta(self):
        # El positivo primero: sin esto los negativos de abajo pasarian
        # igual con un endpoint que rechaza todo.
        self.assertEqual(_registrar().status_code, 201)

    def test_un_registro_completo_guarda_los_datos_en_el_perfil_y_el_usuario(self):
        _registrar()
        user = User.objects.get(email='buzo@b.com')
        perfil = user.profile
        self.assertEqual(
            (user.first_name, user.last_name), ('Juan', 'Perez'))
        self.assertEqual(
            (perfil.dni, perfil.rank, perfil.destination, perfil.birth_date),
            ('30111222', 'SG', 'Escuela de Buceo', date(1990, 5, 1)))

    def test_sin_dni_da_400_por_ese_campo(self):
        r = _registrar(dni=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)

    def test_sin_grado_da_400_por_ese_campo(self):
        r = _registrar(rank=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('rank', r.data)

    def test_sin_fecha_de_nacimiento_da_400_por_ese_campo(self):
        r = _registrar(birth_date=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('birth_date', r.data)

    def test_sin_unidad_da_400_por_ese_campo(self):
        r = _registrar(destination=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('destination', r.data)

    def test_sin_nombre_da_400_por_ese_campo(self):
        r = _registrar(first_name=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('first_name', r.data)

    def test_sin_apellido_da_400_por_ese_campo(self):
        r = _registrar(last_name=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('last_name', r.data)

    def test_un_dato_en_blanco_tampoco_cuenta_como_completado(self):
        for campo in ('dni', 'destination', 'first_name', 'last_name'):
            with self.subTest(campo=campo):
                r = _registrar(**{campo: '   '})
                self.assertEqual(r.status_code, 400)
                self.assertIn(campo, r.data)

    def test_una_fecha_de_nacimiento_futura_da_400_por_ese_campo(self):
        with mock.patch('api.serializers.hoy', return_value=date(2026, 11, 4)):
            r = _registrar(birth_date='2026-11-05')
            self.assertEqual(r.status_code, 400)
            self.assertIn('birth_date', r.data)

    def test_nacer_hoy_no_es_futuro(self):
        # El borde: la fecha de hoy se acepta, la de mañana no.
        with mock.patch('api.serializers.hoy', return_value=date(2026, 11, 4)):
            self.assertEqual(_registrar(birth_date='2026-11-04').status_code, 201)

    def test_los_mensajes_salen_en_castellano(self):
        # LANGUAGE_CODE es 'en-us': todo mensaje sin pisar sale en ingles.
        r = _registrar(
            dni=None, rank='Sgto.', birth_date='no-es-fecha', destination=None,
            first_name=None, last_name=None, email='no-es-correo')
        self.assertEqual(r.status_code, 400)
        esperado = {
            'dni': 'Falta completar este dato.',
            'destination': 'Falta completar este dato.',
            'first_name': 'Falta completar este dato.',
            'last_name': 'Falta completar este dato.',
            'rank': 'El grado debe elegirse de la lista.',
            'birth_date': 'La fecha de nacimiento debe indicarse como AAAA-MM-DD.',
            'email': 'Debe indicarse una dirección de correo válida.',
        }
        for campo, mensaje in esperado.items():
            with self.subTest(campo=campo):
                self.assertEqual([str(m) for m in r.data[campo]], [mensaje])

    def test_si_las_contrasenas_no_coinciden_da_400_por_la_segunda(self):
        r = _registrar(password1=CLAVE, password2=CLAVE + 'x')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            [str(m) for m in r.data['password2']],
            ['Las dos contraseñas deben coincidir.'])
        self.assertFalse(User.objects.filter(email='buzo@b.com').exists())

    def test_el_segundo_correo_obligatorio_sale_en_castellano(self):
        r = _registrar(email2=None)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            [str(m) for m in r.data['email2']], ['Falta completar este dato.'])


class ElDniNoSeRepiteTests(APITestCase):
    def test_un_dni_ya_registrado_da_400_y_no_un_500(self):
        # §5: es lo que hace viable el cotejo manual del admin
        _registrar(dni='30111222')
        r = _registrar(dni='30111222', email='otro@b.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)

    def test_el_dni_repetido_no_deja_un_usuario_huerfano(self):
        _registrar(dni='30111222')
        antes = User.objects.count()
        _registrar(dni='30111222', email='otro@b.com')
        self.assertEqual(User.objects.count(), antes)

    def test_el_dni_con_espacios_sobrantes_es_el_mismo_dni(self):
        _registrar(dni='30111222')
        r = _registrar(dni=' 30111222 ', email='otro@b.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)

    def test_si_la_base_rechaza_el_dni_en_la_carrera_tampoco_hay_huerfano(self):
        # Dos registros simultaneos pasan los dos la validacion y chocan en la
        # restriccion unica: eso es un 400 por el DNI, no un 500, y el `User` ya
        # creado se deshace con la transaccion. Se anula la validacion para
        # llegar a esa rama.
        _registrar(dni='30111222')
        antes = User.objects.count()
        from users.serializers import RegistroSerializer
        with mock.patch.object(
                RegistroSerializer, 'validate_dni', lambda self, valor: valor):
            r = _registrar(dni='30111222', email='otro@b.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('dni', r.data)
        self.assertEqual(User.objects.count(), antes)
        self.assertFalse(User.objects.filter(email='otro@b.com').exists())


class ElCorreoSePideDosVecesTests(APITestCase):
    # §15.11
    def test_si_los_dos_correos_no_coinciden_da_400_por_el_segundo(self):
        r = _registrar(email='a@b.com', email2='c@d.com')
        self.assertEqual(r.status_code, 400)
        # Atado a `email2` y no a `non_field_errors`: el §15.11 pide el correo
        # dos veces justamente para atajar el error de tipeo, y el que se
        # corrige es el segundo.
        self.assertIn('email2', r.data)
        self.assertEqual(
            [str(m) for m in r.data['email2']], ['Los dos correos deben coincidir.'])

    def test_si_los_dos_correos_no_coinciden_no_se_crea_el_usuario(self):
        antes = User.objects.count()
        _registrar(email='a@b.com', email2='c@d.com')
        self.assertEqual(User.objects.count(), antes)

    def test_si_coinciden_se_registra(self):
        self.assertEqual(_registrar(email='a@b.com', email2='a@b.com').status_code, 201)

    def test_las_mayusculas_no_hacen_distintos_a_los_dos_correos(self):
        self.assertEqual(
            _registrar(email='Ana@B.com', email2='ana@b.com').status_code, 201)

    def test_un_correo_ya_registrado_da_400_por_el_correo(self):
        # Con dos cuentas con el mismo correo el login por correo no sabe a
        # cual entrar.
        _registrar(email='a@b.com')
        r = _registrar(email='a@b.com', dni='99999999')
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)
        self.assertEqual(User.objects.filter(email__iexact='a@b.com').count(), 1)


class ElGradoEsListaCerradaTests(APITestCase):
    def test_un_grado_inventado_da_400_por_el_grado(self):
        # "Sgto." es exactamente lo que el §5 quiere impedir: con 150 personas
        # escribiendo su propio grado convivirian "Sgto", "Sgto.", "Sargento"
        # y "SG" en la misma base.
        r = _registrar(rank='Sgto.')
        self.assertEqual(r.status_code, 400)
        self.assertIn('rank', r.data)

    def test_cada_grado_de_la_lista_se_acepta(self):
        for i, grado in enumerate(UserProfile.RANK_VALUES):
            with self.subTest(grado=grado):
                r = _registrar(
                    rank=grado, email=f'g{i}@b.com', dni=str(40000000 + i))
                self.assertEqual(r.status_code, 201, r.data)

    def test_el_endpoint_de_grados_devuelve_los_dos_grupos_en_orden_jerarquico(self):
        grupos = _client(None).get('/api/grados/').data
        self.assertEqual([g['grupo'] for g in grupos], ['Oficiales', 'Suboficiales'])
        self.assertEqual(
            [g['valor'] for g in grupos[0]['grados']][:3], ['GD', 'GB', 'CY'])

    def test_el_endpoint_de_grados_sale_entero_del_modelo(self):
        # Todos los grados, en el orden del modelo y sin ninguno de mas: el
        # desplegable del frontend no redefine la lista.
        grupos = _client(None).get('/api/grados/').data
        planos = [g['valor'] for grupo in grupos for g in grupo['grados']]
        self.assertEqual(tuple(planos), UserProfile.RANK_VALUES)
        self.assertEqual(
            [g['valor'] for g in grupos[1]['grados']],
            ['SM', 'SP', 'SA', 'SI', 'SG', 'CI', 'CB'])
        # Valor y etiqueta de cada grado, tal cual el modelo: hoy coinciden, y
        # un `etiqueta` fabricado desde el valor no tiene que pasar.
        esperado = [
            {'grupo': grupo, 'grados': [
                {'valor': valor, 'etiqueta': etiqueta} for valor, etiqueta in grados]}
            for grupo, grados in UserProfile.RANK_CHOICES
        ]
        self.assertEqual(grupos, esperado)


class _ConDosBuzos:
    def setUp(self):
        _registrar(
            email='mal@b.com', dni='30111222', first_name='Mal', last_name='Escrito')
        _registrar(email='otro@b.com', dni='30333444')
        self.buzo = User.objects.get(email='mal@b.com')
        self.otro = User.objects.get(email='otro@b.com')


class CorregirElCorreoTests(_ConDosBuzos, APITestCase):
    # 15.11: la pantalla muestra a que direccion van los avisos, con la opcion
    # de corregirla. Sin esto, un correo mal tipeado no tiene arreglo y el buzo
    # no se entera de ningun rechazo.
    def _corregir(self, email='bien@b.com', user=None):
        user = user or User.objects.get(pk=self.buzo.pk)
        return _client(user).put('/api/mi-correo/', {'email': email}, format='json')

    def test_cambiar_el_correo_lo_actualiza_en_el_usuario(self):
        r = self._corregir()
        self.assertEqual(r.status_code, 200, r.data)
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.email, 'bien@b.com')

    def test_cambiar_el_correo_lo_actualiza_tambien_en_allauth(self):
        # Si EmailAddress queda con el viejo, el login por correo deja de andar
        self._corregir()
        self.assertTrue(
            EmailAddress.objects.filter(user=self.buzo, email='bien@b.com').exists())
        self.assertFalse(
            EmailAddress.objects.filter(user=self.buzo, email='mal@b.com').exists())

    def test_el_correo_nuevo_queda_como_el_principal_de_allauth(self):
        self._corregir()
        self.assertEqual(
            list(EmailAddress.objects.filter(user=self.buzo, primary=True)
                 .values_list('email', flat=True)),
            ['bien@b.com'])

    def test_despues_de_cambiarlo_el_login_con_el_correo_nuevo_anda(self):
        # Lo mas riesgoso de la tarea: el login es por correo, y una copia
        # desincronizada deja al buzo afuera de su cuenta.
        login = APIClient().post(
            '/api/auth/login/', {'email': 'bien@b.com', 'password': CLAVE},
            format='json')
        self.assertEqual(login.status_code, 400, 'el correo nuevo aun no existe')
        self.assertEqual(self._corregir().status_code, 200)
        login = APIClient().post(
            '/api/auth/login/', {'email': 'bien@b.com', 'password': CLAVE},
            format='json')
        self.assertEqual(login.status_code, 200, login.data)
        self.assertIn('key', login.data)

    def test_despues_de_cambiarlo_el_correo_viejo_ya_no_entra(self):
        self._corregir()
        login = APIClient().post(
            '/api/auth/login/', {'email': 'mal@b.com', 'password': CLAVE},
            format='json')
        self.assertEqual(login.status_code, 400)

    def test_un_correo_ya_usado_por_otro_da_400_por_el_correo(self):
        r = self._corregir(email=self.otro.email)
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.email, 'mal@b.com')

    def test_un_correo_ya_usado_por_otro_con_otras_mayusculas_tambien(self):
        r = self._corregir(email='OTRO@b.com')
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)

    def test_un_correo_invalido_da_400_por_el_correo_en_castellano(self):
        r = self._corregir(email='no-es-correo')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            [str(m) for m in r.data['email']],
            ['Debe indicarse una dirección de correo válida.'])

    def test_sin_correo_da_400_por_el_correo_en_castellano(self):
        r = _client(User.objects.get(pk=self.buzo.pk)).put(
            '/api/mi-correo/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            [str(m) for m in r.data['email']], ['Falta completar este dato.'])

    def test_repetir_el_propio_correo_no_es_un_conflicto(self):
        r = self._corregir(email='mal@b.com')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(
            EmailAddress.objects.filter(user=self.buzo, email='mal@b.com').count(), 1)

    def test_el_buzo_no_puede_cambiar_el_correo_de_otro(self):
        # Actua siempre sobre request.user: no hay id que mandar
        _client(User.objects.get(pk=self.buzo.pk)).put(
            '/api/mi-correo/',
            {'email': 'bien@b.com', 'id': self.otro.pk, 'user': self.otro.pk},
            format='json')
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.email, 'otro@b.com')
        self.assertTrue(
            EmailAddress.objects.filter(user=self.otro, email='otro@b.com').exists())
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.email, 'bien@b.com')

    def test_sin_sesion_no_se_puede_corregir_el_correo(self):
        r = _client(None).put('/api/mi-correo/', {'email': 'bien@b.com'}, format='json')
        self.assertEqual(r.status_code, 401)
        self.buzo.refresh_from_db()
        self.assertEqual(self.buzo.email, 'mal@b.com')

    def test_un_usuario_sin_fila_en_allauth_tambien_se_corrige(self):
        # Un superusuario creado por la consola no pasa por el registro.
        EmailAddress.objects.filter(user=self.buzo).delete()
        self.assertEqual(self._corregir().status_code, 200)
        self.assertTrue(
            EmailAddress.objects.filter(user=self.buzo, email='bien@b.com').exists())


class ElQueSeRegistraEsBuzoTests(APITestCase):
    def test_el_rol_sale_buzo_y_no_se_puede_pedir_otro(self):
        # §5 + D-5: el rol lo designa el admin. 'USER' es el valor real del rol
        # buzo en UserProfile.ROLE_CHOICES, y es el default del campo.
        _registrar(email='nuevo@b.com', role='DOCTOR')
        self.assertEqual(UserProfile.objects.get(user__email='nuevo@b.com').role, 'USER')
