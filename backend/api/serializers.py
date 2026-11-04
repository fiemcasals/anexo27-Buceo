from rest_framework import serializers
from django.contrib.auth.models import User
from .models import StudyBlock, Comment, Permission, DiveActivity, DiveLog
from .fitness import puede_reemplazarse
from .roles import es_revisor
from users.models import UserProfile, ProfileFieldTemplate

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
            vigente = (StudyBlock.objects
                       .filter(user=user, study_code=attrs['study_code'],
                               is_current=True)
                       .prefetch_related('comments').first())
            if not puede_reemplazarse(vigente):
                raise serializers.ValidationError({
                    'study_code': 'El estudio ya fue revisado por el médico '
                                  'y no puede reemplazarse.'})
        return attrs

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
