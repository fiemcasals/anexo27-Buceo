from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    StudyBlock, Comment, Permission, DiveActivity, DiveLog, HabilitationWindow,
)
from django.utils import timezone
from .fitness import puede_reemplazarse
from .roles import es_revisor
from users.models import UserProfile, ProfileFieldTemplate


def hoy():
    return timezone.localdate()


def validar_fecha_de_nacimiento(valor):
    """Una fecha de nacimiento no puede ser posterior a hoy."""
    if valor is not None and valor > hoy():
        raise serializers.ValidationError(
            'La fecha de nacimiento no puede ser posterior a hoy.')
    return valor


class HabilitationWindowSerializer(serializers.ModelSerializer):
    """Una fecha publicada, de sólo lectura. `ya_paso`: su último día ya pasó."""
    slot_display = serializers.CharField(source='get_slot_display', read_only=True)
    ya_paso = serializers.SerializerMethodField()

    class Meta:
        model = HabilitationWindow
        fields = ['id', 'slot', 'slot_display', 'start_date', 'end_date', 'ya_paso']
        read_only_fields = fields

    def get_ya_paso(self, obj):
        return obj.end_date < hoy()


class InscripcionSerializer(serializers.Serializer):
    """La fecha a la que se inscribe el buzo; `null` lo desinscribe."""
    window = serializers.PrimaryKeyRelatedField(
        queryset=HabilitationWindow.objects.all(), allow_null=True,
        error_messages={
            'does_not_exist': 'La fecha elegida no existe.',
            'required': 'Debe indicarse la fecha, o null para desinscribirse.',
            'incorrect_type': 'La fecha elegida no es válida.',
        },
    )

    def validate_window(self, window):
        if window is not None and window.end_date < hoy():
            raise serializers.ValidationError(
                'La fecha elegida ya pasó y no puede seleccionarse.')
        return window

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'role', 'is_instructor', 'profile_data', 'dni', 'birth_date', 'phone', 'rank', 'destination', 'weight', 'height', 'first_name', 'last_name']
        # §5: "Cuatro roles. El admin los designa." El rol no es un dato que el
        # usuario edite de su propio perfil, y desde que el acceso sale del rol
        # (D-5) es la única credencial de autorización del sistema: escribible
        # por su dueño, cualquiera se hacía médico con un PATCH y leía el legajo
        # de todos los buzos. Se designa por el admin de Django (D-1).
        # `is_instructor` va por lo mismo: lo da `promote-instructor`
        # (`IsAdminUser`) y habilita a firmar la bitácora de otros.
        read_only_fields = ['role', 'is_instructor']
        # No es de sólo lectura: el buzo corrige un error de tipeo. Lo que no
        # puede es dejarla vacía (ver `validate_birth_date`).
        extra_kwargs = {
            'birth_date': {'error_messages': {
                'invalid': 'La fecha de nacimiento debe indicarse como AAAA-MM-DD.',
            }},
        }

    def validate_birth_date(self, valor):
        # El registro la exige y de ella depende qué estudios corresponden: un
        # dato obligatorio que después se puede borrar no es obligatorio. Las
        # cuentas anteriores al registro nuevo que no la tienen pueden seguir
        # guardando otros datos.
        if valor is None and self.instance is not None and self.instance.birth_date:
            raise serializers.ValidationError(
                'La fecha de nacimiento no puede quedar vacía; sólo puede corregirse.')
        return validar_fecha_de_nacimiento(valor)

    def update(self, instance, validated_data):
        # Correct way to handle multiple pops from same nested dict if mapped by source
        # DRF merges source='user.first_name' into validated_data['user']['first_name']
        user_data = validated_data.pop('user', {})
        fname = user_data.get('first_name')
        lname = user_data.get('last_name')

        if fname is not None:
            instance.user.first_name = fname
        if lname is not None:
            instance.user.last_name = lname

        if fname is not None or lname is not None:
            instance.user.save()

        return super().update(instance, validated_data)

class ProfileFieldTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileFieldTemplate
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.ReadOnlyField(source='doctor.username')
    class Meta:
        model = Comment
        fields = ['id', 'block', 'doctor', 'doctor_name', 'reviewer_role', 'content', 'status', 'rejection_reason', 'created_at', 'verified_signature']
        # `reviewer_role` lo deriva la vista del perfil del que dictamina: es en
        # calidad de qué firma, no un dato que el firmante declare. Mandado por
        # el cliente, un enfermero designado posteaba
        # `{status: APPROVED, reviewer_role: DOCTOR}` y la fila quedaba
        # indistinguible de la palabra final del médico, que el §6 declara lo
        # único que el médico no puede delegar. La CheckConstraint no lo
        # atrapaba: acopla el estado con el rol declarado, no con el real.
        read_only_fields = ['doctor', 'reviewer_role']

    def validate_status(self, value):
        # `REVERTED` sólo sale de `CommentViewSet.revertir`, que verifica que
        # haya una aprobación vigente del propio médico. Por la vía común
        # deshacería una aprobación saltándose esas reglas.
        if value == 'REVERTED':
            raise serializers.ValidationError(
                'Una aprobación se revierte con la acción de revertir.')
        return value

    def get_fields(self):
        fields = super().get_fields()
        # Un dictamen pertenece al estudio sobre el que se emitió: después de la
        # creación, `block` es de sólo lectura. Se cierra acá y no con una
        # validación porque re-apuntar una aprobación que el médico sí firmó al
        # estudio de otro buzo le da a ese buzo una palabra final que nadie dio,
        # y la validación de abajo no se dispara cuando el bloque destino no es
        # del que edita. Sin bloque que cambiar, el agujero no existe.
        if self.instance is not None:
            fields['block'].read_only = True
        return fields

    def validate(self, attrs):
        # Spec §15.9: nadie dictamina sobre sus propios estudios. Comment.clean()
        # lo cubre para el admin y el shell, pero DRF no llama a clean(); y no
        # hay CheckConstraint posible (haría falta un join). `doctor` lo pone la
        # vista, así que el revisor es el usuario autenticado.
        block = attrs.get('block') or getattr(self.instance, 'block', None)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if block is not None and user is not None and block.user_id == user.pk:
            raise serializers.ValidationError(
                {'block': 'Nadie puede dictaminar sobre sus propios estudios.'}
            )
        # §5: el enfermero auxiliar "no puede declarar apto"; la pre-aprobación
        # es su acto. Con `reviewer_role` derivado del perfil, el pareo contra el
        # estado hay que cotejarlo acá: la CheckConstraint lo atrapa igual, pero
        # sale como IntegrityError —500— y no como un 400 con el motivo. Mismo
        # pareo que `Comment.clean()`, que DRF no llama.
        status = attrs.get('status') or getattr(self.instance, 'status', None)
        role = self._rol_efectivo(user)
        if role is not None:
            if status == 'APPROVED' and role == 'NURSE':
                raise serializers.ValidationError(
                    {'status': 'La aprobación corresponde sólo al médico.'})
            if status == 'PRE_APPROVED' and role == 'DOCTOR':
                raise serializers.ValidationError(
                    {'status': 'La pre-aprobación corresponde sólo al '
                               'enfermero auxiliar.'})
        return attrs

    def _rol_efectivo(self, user):
        """En calidad de qué va a quedar firmada la fila, o None si no se sabe.

        Al crear es el rol del perfil del que dictamina —el mismo que
        `CommentViewSet.perform_create` graba—; al editar, el que la fila ya
        tiene, porque `reviewer_role` es de sólo lectura. None cuando no hay
        request ni fila: el serializador se usa suelto en los tests y sin
        usuario no hay rol que cotejar. El pareo igual queda cubierto por la
        CheckConstraint y por `clean()`.
        """
        if self.instance is not None:
            return self.instance.reviewer_role
        profile = getattr(user, 'profile', None) if user is not None else None
        return profile.role if profile is not None else None

class StudyBlockSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    access_level = serializers.SerializerMethodField()

    class Meta:
        model = StudyBlock
        fields = ['id', 'user', 'user_details', 'study_code', 'is_current', 'title', 'description', 'created_at', 'study_date', 'pdf_attachment', 'comments', 'access_level']
        # `title` lo pone `StudyBlock.save()` desde el catálogo: el punto de la
        # directiva lo decide el botón con que el buzo entró, no un texto libre.
        read_only_fields = ['user', 'title']
        extra_kwargs = {'study_code': {'required': True}}

    def validate(self, attrs):
        # Un reemplazo es un POST al mismo punto. Lo aprobado por el médico no
        # se reemplaza: la carga nueva bajaría la vigente y el buzo se quedaría
        # sin su estudio aprobado. Sin request no hay buzo, y no hay qué cotejar.
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if self.instance is None and user is not None and 'study_code' in attrs:
            if not self._puede_reemplazarse(user, attrs['study_code']):
                raise serializers.ValidationError({
                    'study_code': 'El estudio ya fue revisado por el médico '
                                  'y no puede reemplazarse.'})
        return attrs

    @staticmethod
    def _puede_reemplazarse(user, code):
        """Si el buzo puede volver a cargar el punto `code` (ver `fitness`)."""
        vigente = (StudyBlock.objects.prefetch_related('comments')
                   .filter(user=user, study_code=code, is_current=True).first())
        profile = (UserProfile.objects.select_related('habilitation_window')
                   .filter(user=user).first())
        window = None if profile is None else profile.habilitation_window
        return puede_reemplazarse(code, vigente, window, hoy())

    def get_access_level(self, obj):
        request = self.context.get('request')
        if not request or request.user == obj.user:
            return 'OWNER'
        # §5: el revisor designado puede dictaminar sobre el estudio, y este
        # campo es el que lo informa. Resolviéndolo por `Permission` le decía
        # "NONE" sobre los estudios que la misma respuesta le estaba sirviendo,
        # y `Dashboard.jsx:477` cuelga de este valor el único camino de interfaz
        # para escribir un dictamen: el backend aceptaba el dictamen y la
        # pantalla no se lo ofrecía.
        #
        # `MODIFY` es lo que en el vocabulario de este código significa "puede
        # dictaminar" —`Permissions.jsx:262` lo rotula "Médico"—, no "puede
        # editar el estudio": eso lo sigue impidiendo `SoloElDuenoDelEstudio`.
        # Cuando el plan 3 construya la pantalla del médico conviene reemplazar
        # este campo por uno honesto; mientras tanto tiene que decir la verdad.
        # Sale antes de consultar `Permission`, así que al revisor le ahorra una
        # consulta por fila (§13).
        if es_revisor(request.user):
            return 'MODIFY'
        perms = Permission.objects.filter(grantor=obj.user, grantee=request.user)
        for p in perms:
            if "ALL" in p.shared_items or str(obj.id) in p.shared_items:
                return p.access_level
        return 'NONE'

class PermissionSerializer(serializers.ModelSerializer):
    grantee_email = serializers.EmailField(write_only=True, required=False)
    grantee_details = UserSerializer(source='grantee', read_only=True)
    grantor_details = UserSerializer(source='grantor', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'grantor', 'grantor_details', 'grantee', 'grantee_details', 'grantee_email', 'access_level', 'shared_items', 'created_at']
        read_only_fields = ['grantor', 'grantee']

    def create(self, validated_data):
        # Remove grantee_email from validated_data before creating model instance
        validated_data.pop('grantee_email', None)
        return super().create(validated_data)

class DiveActivitySerializer(serializers.ModelSerializer):
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    safety_diver_name = serializers.ReadOnlyField(source='safety_diver.profile.first_name', default='')
    medic_name = serializers.ReadOnlyField(source='medic.profile.first_name', default='')
    supervisor_name = serializers.ReadOnlyField(source='supervisor.profile.first_name', default='')

    class Meta:
        model = DiveActivity
        fields = '__all__'
        read_only_fields = ['instructor']

class DiveLogSerializer(serializers.ModelSerializer):
    activity_details = DiveActivitySerializer(source='activity', read_only=True)
    diver_name = serializers.ReadOnlyField(source='diver.username')

    class Meta:
        model = DiveLog
        fields = '__all__'
        read_only_fields = ['token', 'diver', 'is_completed', 'completed_at']


# ---------------------------------------------------------------------------
# Lo que el administrador de la unidad hace desde la webapp
# ---------------------------------------------------------------------------
# Se puede designar revisores y volver a alguien a buzo, y nada mas. `ADMIN`
# queda deliberadamente afuera: un administrador designa revisores, no fabrica
# administradores. Esa potestad sigue siendo del admin de Django, que es donde
# la tiene el oficial de la unidad.
ROLES_QUE_EL_ADMIN_ASIGNA = ('DOCTOR', 'NURSE', 'USER')


def nombre_para_mostrar(user):
    """Como se nombra a una persona en una lista de 150.

    Por correo no se reconoce a nadie, asi que la pantalla muestra el apellido
    primero. Sin nombre cargado cae al usuario, que siempre existe.
    """
    apellido = (user.last_name or '').strip()
    nombre = (user.first_name or '').strip()
    if apellido and nombre:
        return f'{apellido}, {nombre}'
    return apellido or nombre or user.username


class DesignarRevisorSerializer(serializers.Serializer):
    """Le pone a una persona el rol de medico, de enfermero, o la vuelve a buzo.

    El correo identifica a la persona porque es con lo que entra al sistema
    (`ACCOUNT_AUTHENTICATION_METHOD = 'email'`) y es lo que el administrador
    tiene a mano. Se compara sin distinguir mayusculas: lo escribe a mano
    mirando una lista en papel.
    """

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ROLES_QUE_EL_ADMIN_ASIGNA)

    def validate_email(self, valor):
        encontrados = list(User.objects.filter(email__iexact=valor.strip())[:2])
        if not encontrados:
            raise serializers.ValidationError(
                'No hay ningún usuario registrado con ese correo.')
        if len(encontrados) > 1:
            # No deberia pasar: el registro rechaza duplicados. Si pasa, elegir
            # uno al azar le daria acceso a los estudios de 150 buzos a la
            # persona equivocada, asi que se para y se dice.
            raise serializers.ValidationError(
                'Hay más de un usuario con ese correo. Resolvelo en el admin '
                'de Django antes de designarlo.')
        self._usuario = encontrados[0]
        return valor

    def save(self):
        # `get_or_create`: el perfil se crea aparte del `User`, asi que puede
        # no existir todavia. Sin esto, designar a alguien recien creado por
        # consola levantaria en lugar de designarlo.
        perfil, _ = UserProfile.objects.get_or_create(user=self._usuario)
        perfil.role = self.validated_data['role']
        # `update_fields`: designar al medico no toca ningun otro campo del
        # perfil, y en particular no toca `is_staff` ni `is_superuser`, que
        # viven en `User` y son la puerta del admin de Django. Ser medico es
        # del §5; entrar al admin de Django es otra cosa.
        perfil.save(update_fields=['role'])
        return perfil


class CargarFechasSerializer(serializers.Serializer):
    """Carga o corrige las fechas de habilitacion de un ciclo.

    Un input por lugar del ciclo, y la fecha cargada es **un dia solo**: el
    modelo guarda un rango porque toda vigencia se mide contra `end_date`, asi
    que `start_date` y `end_date` quedan en el mismo dia. Si no fuera asi, la
    habilitacion abarcaria dias que el administrador nunca escribio.

    Un lugar que no viene, o que viene vacio, **queda como estaba**. Un campo en
    blanco es "todavia no la cargue", no "borrala": borrar una fecha desinscribe
    a todos los buzos anotados en ella, y eso no puede ser el efecto de no
    tocar un input.
    """

    cycle = serializers.IntegerField(min_value=2000, max_value=2100)
    FIRST = serializers.DateField(required=False)
    SECOND = serializers.DateField(required=False)
    COMPLEMENTARY = serializers.DateField(required=False)

    LUGARES = ('FIRST', 'SECOND', 'COMPLEMENTARY')

    def to_internal_value(self, data):
        # Los campos vacios se descartan antes de validar: un `DateField` no
        # acepta '' y daria 400 por un input que la persona simplemente no toco.
        limpio = {
            clave: valor for clave, valor in data.items()
            if not (isinstance(valor, str) and not valor.strip()) and valor is not None
        }
        return super().to_internal_value(limpio)

    def validate(self, datos):
        if not any(lugar in datos for lugar in self.LUGARES):
            raise serializers.ValidationError(
                'No viene ninguna fecha. Cargá al menos una.')
        return datos

    def save(self):
        from django.db import transaction

        ciclo = self.validated_data['cycle']
        with transaction.atomic():
            for lugar in self.LUGARES:
                fecha = self.validated_data.get(lugar)
                if fecha is None:
                    continue
                # `update_or_create` y no un create: `cycle` + `slot` es unico,
                # asi que corregir un tipeo explotaria la segunda vez. Y
                # actualizar la fila conserva su id, asi que los buzos ya
                # inscriptos siguen inscriptos: `habilitation_window` es una FK
                # y volver a crear la fila se los llevaria puestos.
                HabilitationWindow.objects.update_or_create(
                    cycle=ciclo, slot=lugar,
                    defaults={'start_date': fecha, 'end_date': fecha})
        return ciclo
