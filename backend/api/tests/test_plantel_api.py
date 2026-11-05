"""Tests de `GET /api/plantel/`: el plantel que se le sirve al médico.

Tres cosas sostienen este archivo, y cada una tiene su clase:

1. **Quién entra y quién figura.** Sólo los revisores; el plantel son los buzos.
2. **Que cueste un número fijo de consultas** (`NoHayNMasUnoTests`). Es lo que
   impide que alguien reemplace el prefetch por un `annotate`.
3. **Que el listado y la ficha digan lo mismo**
   (`ElListadoYLaFichaDicenLoMismoTests`).

Además, la dirección de la página la escribe cualquiera: `QueryStringTests`
comprueba que cada valor raro se normaliza **y** que devuelve las filas que
corresponden. No alcanza con "no da 500": un `?turno=2` mal convertido da 200 y
una lista vacía, y el médico creería que nadie se anotó a ese turno.

`hoy` se fija para que ningún caso dependa del día en que corra la suite.
"""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from api import catalog, fitness
from api.tests.test_fitness import (
    TODAY, VALID_FOR_EVERY_POINT, _diver, _july_2027, _november_2026, _upload,
)
from users.models import UserProfile

URL = '/api/plantel/'


def _revisor(username, role):
    user = User.objects.create(username=username, email=f'{username}@ara.mil.ar')
    UserProfile.objects.create(user=user, role=role)
    return user


def _apellidar(profile, apellido, nombre='Juan'):
    User.objects.filter(pk=profile.user_id).update(
        last_name=apellido, first_name=nombre)
    return profile


class _ConPlantel(APITestCase):
    """Cinco buzos conocidos, un médico, un enfermero y un administrador.

    Alonso es el buzo que pide el endpoint cuando hace falta uno, y es parte del
    plantel como cualquier otro.

    ============ ========== ============================================
    buzo         turno      lo que tiene
    ============ ========== ============================================
    Alonso       2.º        nada (INCOMPLETE)
    Gómez        1.º        los siete aprobados por el médico (APTO)
    Pérez        1.º        un estudio sin tocar (INCOMPLETE, a revisar 1)
    Vega         2.º        nada (INCOMPLETE)
    Zapata       sin turno  nada (NO_WINDOW)
    ============ ========== ============================================
    """

    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.hoy = TODAY

        self.turno_1 = _november_2026()
        self.turno_2 = _july_2027()

        self.alonso = _apellidar(
            _diver(birth_year=1988, window=self.turno_2), 'Alonso')
        self.gomez = _apellidar(
            _diver(birth_year=1988, window=self.turno_1), 'Gómez')
        for code in 'bcdefgh':
            _upload(self.gomez, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('APPROVED', 'DOCTOR')])
        self.perez = _apellidar(
            _diver(birth_year=1988, window=self.turno_1), 'Pérez')
        _upload(self.perez, 'b', VALID_FOR_EVERY_POINT)
        self.vega = _apellidar(
            _diver(birth_year=1988, window=self.turno_2), 'Vega')
        self.zapata = _apellidar(
            _diver(birth_year=1988, window=None), 'Zapata')

        self.buzo = self.alonso.user
        self.medico = _revisor('doc', 'DOCTOR')
        self.enfermero = _revisor('vera', 'NURSE')
        self.admin = _revisor('jefe', 'ADMIN')

        self.client = APIClient()
        self.client.force_authenticate(self.medico)

    def pedir(self, **params):
        respuesta = self.client.get(URL, params)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def get_filas(self, **params):
        return self.pedir(**params)['filas']

    def apellidos(self, **params):
        return [f['apellido'] for f in self.get_filas(**params)]


# --------------------------------------------------------------------------
# Quién entra
# --------------------------------------------------------------------------
class SoloLosRevisoresEntranTests(_ConPlantel):
    def test_el_buzo_recibe_403(self):
        self.client.force_authenticate(self.buzo)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_el_medico_y_el_enfermero_entran(self):
        for u in (self.medico, self.enfermero):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get(URL).status_code, 200)

    def test_el_administrador_no_entra(self):
        # El §5 le da el plantel al médico y a los enfermeros; el administrador
        # designa roles, no revisa estudios.
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_sin_sesion_recibe_401_y_no_403(self):
        # El frontend manda al login con el 401 y muestra un mensaje con el 403.
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_un_usuario_sin_perfil_recibe_403(self):
        # El perfil se crea aparte del User: su ausencia nunca significa "ve todo".
        sin_perfil = User.objects.create(username='sinperfil')
        self.client.force_authenticate(sin_perfil)
        self.assertEqual(self.client.get(URL).status_code, 403)


# --------------------------------------------------------------------------
# Quién figura
# --------------------------------------------------------------------------
class ElPlantelSonLosBuzosTests(_ConPlantel):
    def test_el_medico_el_enfermero_y_el_admin_no_figuran_en_el_plantel(self):
        # Spec §5: no aparecen en "Personal a controlar".
        ids = [f['id'] for f in self.get_filas()]
        self.assertNotIn(self.medico.profile.pk, ids)
        self.assertNotIn(self.enfermero.profile.pk, ids)
        self.assertNotIn(self.admin.profile.pk, ids)

    def test_figuran_los_cinco_buzos_por_el_id_del_perfil(self):
        # La ruta de la ficha es /plantel/:id y consulta UserProfile: el id de la
        # fila es el del perfil, no el del usuario.
        ids = sorted(f['id'] for f in self.get_filas())
        perfiles = [p.pk for p in (self.alonso, self.gomez, self.perez,
                                   self.vega, self.zapata)]
        self.assertEqual(ids, sorted(perfiles))

    def test_el_id_es_el_del_perfil_aunque_difiera_del_del_usuario(self):
        # Si coincidieran por casualidad, el test de arriba no distinguiría. Con
        # usuarios sin perfil de por medio, el pk del usuario se adelanta al del
        # perfil y no pueden coincidir.
        User.objects.create(username='relleno-1')
        User.objects.create(username='relleno-2')
        nuevo = _apellidar(_diver(birth_year=1990), 'Nuevo')
        self.assertNotEqual(nuevo.pk, nuevo.user_id)
        fila = next(f for f in self.get_filas() if f['apellido'] == 'Nuevo')
        self.assertEqual(fila['id'], nuevo.pk)


class LaRespuestaTests(_ConPlantel):
    def test_la_forma_de_la_respuesta(self):
        cuerpo = self.pedir()
        self.assertEqual(set(cuerpo),
                         {'contadores', 'total', 'pagina', 'paginas', 'filas'})
        self.assertEqual(set(cuerpo['contadores']),
                         {'aptos', 'a_revisar', 'vencidos', 'por_filtro'})
        self.assertEqual(cuerpo['total'], 5)
        self.assertEqual(cuerpo['pagina'], 1)
        self.assertEqual(cuerpo['paginas'], 1)
        self.assertEqual(len(cuerpo['filas']), 5)

    def test_las_fechas_salen_como_texto(self):
        # `ultima_revision` es un día y `subida_mas_vieja_sin_dictamen` un
        # instante con zona: no son del mismo tipo y cada uno sale como es.
        _upload(self.vega, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR')])
        _upload(self.vega, 'd', VALID_FOR_EVERY_POINT)
        fila = next(f for f in self.get_filas() if f['apellido'] == 'Vega')
        self.assertEqual(fila['ultima_revision'], '2026-10-30')
        self.assertRegex(fila['subida_mas_vieja_sin_dictamen'],
                         r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        self.assertEqual(fila['turno']['start_date'], '2027-07-12')
        self.assertEqual(fila['turno']['id'], self.turno_2.pk)

    def test_sin_nada_pendiente_las_dos_fechas_son_null(self):
        fila = next(f for f in self.get_filas() if f['apellido'] == 'Zapata')
        self.assertIsNone(fila['ultima_revision'])
        self.assertIsNone(fila['subida_mas_vieja_sin_dictamen'])
        self.assertIsNone(fila['turno'])


# --------------------------------------------------------------------------
# Lo que escribe cualquiera en la dirección de la página
# --------------------------------------------------------------------------
class QueryStringTests(_ConPlantel):
    TODOS = ['Alonso', 'Gómez', 'Pérez', 'Vega', 'Zapata']

    # --- filtro -----------------------------------------------------------
    def test_filtro_inventado_vuelve_a_todos_y_no_da_500(self):
        self.assertEqual(self.apellidos(filtro='inventado'), self.TODOS)

    def test_filtro_vacio_es_todos(self):
        self.assertEqual(self.apellidos(filtro=''), self.TODOS)

    def test_filtro_valido_filtra(self):
        self.assertEqual(self.apellidos(filtro='pendientes'), ['Pérez'])
        self.assertEqual(self.apellidos(filtro='completa'), ['Gómez'])
        self.assertEqual(self.apellidos(filtro='incompleta'),
                         ['Alonso', 'Pérez', 'Vega', 'Zapata'])

    # --- orden ------------------------------------------------------------
    def test_orden_inventado_ordena_por_apellido_y_no_da_500(self):
        self.assertEqual(self.apellidos(orden='inventado'), self.TODOS)

    def test_sin_orden_ordena_por_apellido(self):
        # `ordenar(filas, None)` lanza ValueError: la vista pone el valor.
        self.assertEqual(self.apellidos(), self.TODOS)
        self.assertEqual(self.apellidos(orden=''), self.TODOS)

    def test_cada_criterio_valido_se_respeta(self):
        # Pérez es el único con algo para revisar: encabeza `pendientes` y
        # `pila_cruda`, y el resto se desempata por apellido.
        self.assertEqual(self.apellidos(orden='pendientes')[0], 'Pérez')
        self.assertEqual(self.apellidos(orden='pila_cruda')[0], 'Pérez')
        # Gómez es el único con dictamen del médico: los nunca revisados van
        # primero.
        self.assertEqual(self.apellidos(orden='ultima_revision')[-1], 'Gómez')
        self.assertEqual(len(self.apellidos(orden='pila_rapida')), 5)

    # --- turno ------------------------------------------------------------
    def test_turno_llega_como_texto_y_se_compara_como_id(self):
        # `?turno=2` es el texto '2'; el id del turno es el entero 2. Sin
        # convertirlo, nunca coinciden y la lista sale vacía, sin error.
        self.assertEqual(self.apellidos(turno=str(self.turno_1.pk)),
                         ['Gómez', 'Pérez'])
        self.assertEqual(self.apellidos(turno=str(self.turno_2.pk)),
                         ['Alonso', 'Vega'])

    def test_turno_vacio_no_filtra(self):
        # `?turno=` es "sin filtro", no "filtrar por nada".
        self.assertEqual(self.apellidos(turno=''), self.TODOS)

    def test_turno_sin_son_los_no_inscriptos(self):
        self.assertEqual(self.apellidos(turno='sin'), ['Zapata'])

    def test_turno_que_no_es_un_numero_no_filtra(self):
        # Una dirección escrita a mano no puede dejar la pantalla vacía ni
        # romperla: se ignora, igual que un filtro inventado.
        self.assertEqual(self.apellidos(turno='inventado'), self.TODOS)

    def test_turno_de_un_id_que_no_existe_da_vacio(self):
        # Acá sí: es un id válido sin nadie adentro.
        cuerpo = self.pedir(turno='9999')
        self.assertEqual(cuerpo['filas'], [])
        self.assertEqual(cuerpo['total'], 0)

    # --- buscar -----------------------------------------------------------
    def test_buscar_encuentra_por_apellido_sin_acentos(self):
        self.assertEqual(self.apellidos(buscar='gomez'), ['Gómez'])

    def test_buscar_por_dni_con_puntos(self):
        dni = self.vega.dni
        con_puntos = f'{dni[:2]}.{dni[2:5]}.{dni[5:]}'
        self.assertEqual(self.apellidos(buscar=con_puntos), ['Vega'])

    def test_buscar_vacio_no_filtra(self):
        self.assertEqual(self.apellidos(buscar=''), self.TODOS)

    # --- pagina -----------------------------------------------------------
    def test_pagina_que_no_es_un_numero_es_la_primera(self):
        self.assertEqual(self.pedir(pagina='cero')['pagina'], 1)
        self.assertEqual(self.apellidos(pagina='cero'), self.TODOS)

    def test_pagina_cero_negativa_o_fuera_de_rango_es_la_primera(self):
        for crudo in ('0', '-1', '2', '999'):
            cuerpo = self.pedir(pagina=crudo)
            self.assertEqual(cuerpo['pagina'], 1, crudo)
            self.assertEqual(len(cuerpo['filas']), 5, crudo)

    def test_pagina_vacia_es_la_primera(self):
        self.assertEqual(self.pedir(pagina='')['pagina'], 1)


class PaginacionTests(_ConPlantel):
    """De a 50, y propia: DRF no tiene `DEFAULT_PAGINATION_CLASS`."""

    def setUp(self):
        super().setUp()
        for n in range(55):
            # Apellidos que ordenan después de Zapata: 'Zz00' ... 'Zz54'.
            _apellidar(_diver(birth_year=1990), f'Zz{n:02d}')

    def test_la_primera_pagina_trae_cincuenta(self):
        cuerpo = self.pedir()
        self.assertEqual(cuerpo['total'], 60)
        self.assertEqual(cuerpo['paginas'], 2)
        self.assertEqual(cuerpo['pagina'], 1)
        self.assertEqual(len(cuerpo['filas']), 50)

    def test_la_segunda_trae_el_resto_en_orden(self):
        primera = self.get_filas()
        segunda = self.pedir(pagina='2')
        self.assertEqual(segunda['pagina'], 2)
        self.assertEqual(len(segunda['filas']), 10)
        ids = [f['id'] for f in primera + segunda['filas']]
        self.assertEqual(len(set(ids)), 60)
        self.assertEqual(segunda['filas'][-1]['apellido'], 'Zz54')

    def test_fuera_de_rango_vuelve_a_la_primera(self):
        cuerpo = self.pedir(pagina='3')
        self.assertEqual(cuerpo['pagina'], 1)
        self.assertEqual(cuerpo['filas'], self.get_filas())

    def test_los_contadores_cuentan_el_plantel_y_no_la_pagina(self):
        # Pagine o no pagine la tabla, los números son del plantel entero.
        for pagina in ('1', '2'):
            c = self.pedir(pagina=pagina)['contadores']
            self.assertEqual(c['aptos'], 1, pagina)
            self.assertEqual(c['por_filtro']['todos'], 60, pagina)

    def test_sin_resultados_hay_una_pagina_vacia(self):
        cuerpo = self.pedir(buscar='nadie se llama asi')
        self.assertEqual(cuerpo['filas'], [])
        self.assertEqual((cuerpo['total'], cuerpo['pagina'], cuerpo['paginas']),
                         (0, 1, 1))


class LosContadoresRecalculanTests(_ConPlantel):
    def test_sin_filtros_cuentan_el_plantel_entero(self):
        c = self.pedir()['contadores']
        self.assertEqual((c['aptos'], c['a_revisar'], c['vencidos']), (1, 1, 0))
        self.assertEqual(c['por_filtro'],
                         {'todos': 5, 'completa': 1, 'incompleta': 4,
                          'pendientes': 1})

    def test_el_turno_cambia_los_numeros_de_arriba(self):
        # Del turno 2 nadie está apto ni espera revisión; del 1, uno y uno.
        c1 = self.pedir(turno=str(self.turno_1.pk))['contadores']
        self.assertEqual((c1['aptos'], c1['a_revisar']), (1, 1))
        self.assertEqual(c1['por_filtro']['todos'], 2)
        c2 = self.pedir(turno=str(self.turno_2.pk))['contadores']
        self.assertEqual((c2['aptos'], c2['a_revisar']), (0, 0))
        self.assertEqual(c2['por_filtro']['todos'], 2)

    def test_el_buscador_cambia_los_numeros_de_arriba(self):
        c = self.pedir(buscar='perez')['contadores']
        self.assertEqual((c['aptos'], c['a_revisar']), (0, 1))
        self.assertEqual(c['por_filtro']['todos'], 1)

    def test_el_filtro_no_achica_los_conteos_de_los_filtros(self):
        # Cada solapa lleva su conteo: si elegir una pusiera en cero a las
        # otras, el médico no podría ver cuánto hay detrás de cada una.
        sin = self.pedir()['contadores']
        con = self.pedir(filtro='pendientes')['contadores']
        self.assertEqual(con, sin)

    def test_el_total_es_el_de_la_lista_filtrada(self):
        cuerpo = self.pedir(filtro='incompleta', turno=str(self.turno_1.pk))
        self.assertEqual(cuerpo['total'], 1)
        self.assertEqual([f['apellido'] for f in cuerpo['filas']], ['Pérez'])


# --------------------------------------------------------------------------
# El número de consultas
# --------------------------------------------------------------------------
class NoHayNMasUnoTests(_ConPlantel):
    """**No tocar este test para que pase.**

    Protege que traer el plantel cueste un número fijo de consultas, sin
    importar cuántos buzos haya. Es lo que mantiene a `fitness.diver_summary`
    como la **única** definición de la regla de aptitud.

    Sin el `select_related`/`prefetch_related` de `api/fitness.py`, cada buzo
    cuesta consultas propias (su usuario, su turno, sus estudios, los dictámenes
    de cada estudio) y con 150 buzos el listado hace cientos. La reacción natural
    es "esto se arregla con un `annotate`". No: un `annotate` reescribiría en SQL
    la vigencia, el último dictamen, la regla de la edad y la precedencia entre
    estados, o sea una **segunda definición de la regla**. Esa copia se va a
    desincronizar de `fitness.py`, y el listado diría 6/7 donde la ficha dice
    5/7, sin error ni excepción, y nadie sabría cuál de las dos miente.

    Si este test falla porque el número **creció**, alguien rompió el prefetch:
    arreglá el prefetch. Si falla porque el número **cambió** al agregar algo
    legítimo a la vista, subí `CONSULTAS` sabiendo qué consulta nueva es y que no
    depende de la cantidad de buzos.

    Si el número **baja**, alguien dejó de usar `fitness`: no ajustes la
    constante, averiguá por qué. Un `annotate` que reemplace al motor da menos
    consultas, y bajar `CONSULTAS` para que pase deja la segunda definición de la
    regla adentro. Este test sólo vigila una mitad: un `annotate` que además
    conservara el prefetch quedaría en 4 consultas y no se vería acá. Esa otra
    mitad de la red es `ElListadoYLaFichaDicenLoMismoTests`, que compara cada
    fila contra `diver_summary`.
    """

    #: Medido, no estimado: el perfil de quien pide (el permiso) + los buzos con
    #: su usuario y su turno en una sola consulta + los bloques vigentes de
    #: todos + los dictámenes de todos esos bloques.
    CONSULTAS = 4

    def entrar_como_en_produccion(self):
        """Autentica con el usuario recién traído de la base, como llega en
        producción: el que armó `_revisor` ya trae su perfil en caché, y el
        permiso no costaría la consulta del perfil. Se llama **antes** de
        medir, porque traer el usuario también es una consulta."""
        self.client.force_authenticate(User.objects.get(pk=self.medico.pk))

    def crear_buzos(self, cuantos):
        """Buzos con turno, estudios cargados y dictámenes: cada uno le daría a
        un listado ingenuo consultas para el turno, el usuario, los estudios y
        los dictámenes de cada estudio."""
        for _ in range(cuantos):
            buzo = _diver(birth_year=1988, window=self.turno_1)
            for code in 'bcd':
                _upload(buzo, code, VALID_FOR_EVERY_POINT,
                        dictamenes=[('PRE_APPROVED', 'NURSE'),
                                    ('APPROVED', 'DOCTOR')])

    def test_el_plantel_entero_cuesta_un_numero_fijo_y_chico_de_consultas(self):
        self.crear_buzos(5)
        self.entrar_como_en_produccion()
        with self.assertNumQueries(self.CONSULTAS):
            self.assertEqual(self.client.get(URL).status_code, 200)
        self.crear_buzos(20)
        self.entrar_como_en_produccion()
        with self.assertNumQueries(self.CONSULTAS):
            self.assertEqual(self.client.get(URL).status_code, 200)

    def test_con_filtros_y_orden_cuesta_lo_mismo(self):
        # Buscar, filtrar, ordenar y paginar se resuelven sobre las filas ya
        # armadas: ninguno agrega una consulta.
        self.crear_buzos(5)
        self.entrar_como_en_produccion()
        with self.assertNumQueries(self.CONSULTAS):
            self.client.get(URL, {
                'buscar': 'a', 'filtro': 'pendientes',
                'turno': str(self.turno_1.pk),
                'orden': 'pila_cruda', 'pagina': '1'})


# --------------------------------------------------------------------------
# El listado y la ficha dicen lo mismo
# --------------------------------------------------------------------------
class ElListadoYLaFichaDicenLoMismoTests(APITestCase):
    """Compara, buzo por buzo y sobre los mismos datos, lo que devuelve el
    endpoint contra `fitness.diver_summary`, que es lo que lee la ficha.

    Los siete casos son donde más fácil se separan las dos lecturas."""

    def setUp(self):
        patcher = mock.patch('api.serializers.hoy', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.hoy = TODAY
        turno = _november_2026()
        todos = 'abcdefgh'

        # 1. Sin turno, con estudios subidos: no hay contra qué medir.
        sin_turno = _diver(birth_year=1980, window=None)
        for code in 'abc':
            _upload(sin_turno, code, VALID_FOR_EVERY_POINT)

        # 2. Sin fecha de nacimiento: no se sabe cuántos le corresponden.
        sin_nacimiento = _diver(birth_year=None, window=turno)
        _upload(sin_nacimiento, 'b', VALID_FOR_EVERY_POINT,
                dictamenes=[('APPROVED', 'DOCTOR')])
        _upload(sin_nacimiento, 'c', VALID_FOR_EVERY_POINT)

        # 3. Cuarenta justos: nace el 31/12/1986, cumple 40 el año del turno.
        cuarenta = _diver(birth_year=1986, birth_month=12, birth_day=31,
                          window=turno)
        for code in todos:
            _upload(cuarenta, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('APPROVED', 'DOCTOR')])

        # 4. Un vencido y un rechazado a la vez: gana el rechazado.
        vencido_y_rechazado = _diver(birth_year=1988, window=turno)
        _upload(vencido_y_rechazado, 'b', date(2025, 1, 1),
                dictamenes=[('APPROVED', 'DOCTOR')])
        _upload(vencido_y_rechazado, 'c', VALID_FOR_EVERY_POINT,
                dictamenes=[('REJECTED', 'DOCTOR')])

        # 5. Sin nada subido.
        _diver(birth_year=1988, window=turno)

        # 6. Todo presentado, uno sin tocar y seis pre-revisados: las dos pilas de
        # "a revisar".
        pilas = _diver(birth_year=1988, window=turno)
        _upload(pilas, 'b', VALID_FOR_EVERY_POINT)
        for code in 'cdefgh':
            _upload(pilas, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('PRE_APPROVED', 'NURSE')])

        # 7. Apto: los siete aprobados por el médico.
        apto = _diver(birth_year=1988, window=turno)
        for code in 'bcdefgh':
            _upload(apto, code, VALID_FOR_EVERY_POINT,
                    dictamenes=[('PRE_APPROVED', 'NURSE'),
                                ('APPROVED', 'DOCTOR')])

        self.medico = _revisor('doc', 'DOCTOR')
        self.client = APIClient()
        self.client.force_authenticate(self.medico)

    def get_filas(self):
        respuesta = self.client.get(URL)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()['filas']

    def test_cada_fila_coincide_con_diver_summary_de_ese_buzo(self):
        filas = self.get_filas()
        self.assertEqual(len(filas), 7)
        for f in filas:
            perfil = UserProfile.objects.get(pk=f['id'])
            resumen = fitness.diver_summary(perfil, self.hoy)
            with self.subTest(buzo=perfil.user.username):
                if f['exigidos'] is None:
                    # Sin turno o sin edad la ficha no tiene exigidos, y el
                    # listado cuenta lo subido en vez de decir "0": un buzo que
                    # subió ocho estudios no leería "0/0".
                    self.assertEqual(
                        f['presentados'],
                        sum(1 for s in resumen.slots if s.block is not None))
                    self.assertEqual(resumen.required_codes, ())
                else:
                    self.assertEqual(f['presentados'], resumen.presented)
                    self.assertEqual(f['exigidos'], len(resumen.required_codes))
                self.assertEqual(f['a_revisar'],
                                 resumen.pending_review + resumen.pre_reviewed)
                self.assertEqual(f['sin_tocar'], resumen.pending_review)
                self.assertEqual(f['pre_revisados'], resumen.pre_reviewed)
                self.assertEqual(f['rechazados'], resumen.rejected)
                self.assertEqual(f['vencidos'], resumen.expired)
                self.assertEqual(f['estado'], resumen.state.name)
                self.assertEqual(
                    f['ultima_revision'],
                    None if resumen.last_doctor_review is None
                    else resumen.last_doctor_review.isoformat())

    def test_los_casos_no_son_todos_iguales(self):
        # Que el test de arriba no pase por vacío: los siete buzos tienen que
        # cubrir los estados que dice cubrir.
        estados = sorted(f['estado'] for f in self.get_filas())
        self.assertEqual(estados, sorted([
            'NO_WINDOW', 'UNKNOWN_AGE', 'APTO', 'REJECTED', 'INCOMPLETE',
            'TO_REVIEW', 'APTO',
        ]))

    def test_los_subidos_sin_exigidos_son_los_que_cargaron_los_fixtures(self):
        # Literales, no recalculados: si la implementación y el test de arriba
        # contaran mal de la misma forma, coincidirían igual. Acá el número sale
        # de lo que `setUp` subió: tres estudios el buzo sin turno, dos el que no
        # tiene fecha de nacimiento.
        filas = self.get_filas()
        sin_turno = next(f for f in filas if f['turno'] is None)
        self.assertIsNone(sin_turno['exigidos'])
        self.assertEqual(sin_turno['presentados'], 3)
        sin_nacimiento = next(f for f in filas
                              if f['turno'] is not None and f['edad'] is None)
        self.assertIsNone(sin_nacimiento['exigidos'])
        self.assertEqual(sin_nacimiento['presentados'], 2)

    def test_el_de_cuarenta_justos_debe_ocho(self):
        fila = next(f for f in self.get_filas() if f['edad'] == 40)
        self.assertEqual(fila['exigidos'], len(catalog.CODES))
        self.assertEqual(fila['presentados'], 8)

    def test_el_vencido_y_rechazado_cae_en_rechazado_y_cuenta_los_dos(self):
        fila = next(f for f in self.get_filas() if f['rechazados'] == 1)
        self.assertEqual(fila['vencidos'], 1)
        self.assertEqual(fila['estado'], 'REJECTED')
