"""Registro con los datos del §5 y corrección del correo (§15.11).

`LANGUAGE_CODE` es 'en-us': todo mensaje de validación que no se pise acá sale en
inglés. Por eso cada campo que declara este módulo trae sus `error_messages`.
"""

from allauth.account.models import EmailAddress
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework import serializers

from api.serializers import validar_fecha_de_nacimiento
from users.models import UserProfile

FALTA = 'Falta completar este dato.'
OBLIGATORIO = {'required': FALTA, 'blank': FALTA, 'null': FALTA}
CORREO_INVALIDO = 'Debe indicarse una dirección de correo válida.'
CORREO_EN_USO = 'Ese correo ya está en uso.'
DNI_REPETIDO = 'Ya existe un registro con ese DNI.'
ERRORES_DE_CORREO = {**OBLIGATORIO, 'invalid': CORREO_INVALIDO}


def _correo_en_uso(correo, excluyendo=None):
    """Si otro usuario ya tiene el correo, en `User` o en la copia de allauth.

    El login es por correo: dos cuentas con el mismo correo dejan al login sin
    saber a cuál entrar.
    """
    usuarios = User.objects.filter(email__iexact=correo)
    direcciones = EmailAddress.objects.filter(email__iexact=correo)
    if excluyendo is not None:
        usuarios = usuarios.exclude(pk=excluyendo.pk)
        direcciones = direcciones.exclude(user=excluyendo)
    return usuarios.exists() or direcciones.exists()


class RegistroSerializer(RegisterSerializer):
    # El buzo no tiene un nombre de usuario: entra por correo y allauth genera
    # uno interno. Sin esto el registro exigía un campo que nadie sabe qué es.
    username = serializers.CharField(required=False)
    email = serializers.EmailField(error_messages=ERRORES_DE_CORREO)
    # §15.11: el correo se pide dos veces; no hay paso de verificación.
    email2 = serializers.EmailField(
        write_only=True, error_messages=ERRORES_DE_CORREO)
    password1 = serializers.CharField(write_only=True, error_messages=OBLIGATORIO)
    password2 = serializers.CharField(write_only=True, error_messages=OBLIGATORIO)
    first_name = serializers.CharField(max_length=150, error_messages=OBLIGATORIO)
    last_name = serializers.CharField(max_length=150, error_messages=OBLIGATORIO)
    dni = serializers.CharField(max_length=20, error_messages=OBLIGATORIO)
    # La lista sale del modelo (§5): no se redefine acá ni en el frontend.
    rank = serializers.ChoiceField(
        choices=UserProfile.RANK_VALUES,
        error_messages={
            **OBLIGATORIO,
            'invalid_choice': 'El grado debe elegirse de la lista.',
        },
    )
    destination = serializers.CharField(max_length=100, error_messages=OBLIGATORIO)
    birth_date = serializers.DateField(
        error_messages={
            **OBLIGATORIO,
            'invalid': 'La fecha de nacimiento debe indicarse como AAAA-MM-DD.',
        },
    )
    # `role` no se declara: un cliente no puede pedirlo. El rol buzo es el
    # default del modelo y los demás los designa el admin (§5, D-5).

    def validate_email(self, email):
        email = email.strip()
        if _correo_en_uso(email):
            raise serializers.ValidationError(CORREO_EN_USO)
        return email

    def validate_dni(self, dni):
        if UserProfile.objects.filter(dni=dni).exists():
            raise serializers.ValidationError(DNI_REPETIDO)
        return dni

    def validate_birth_date(self, valor):
        return validar_fecha_de_nacimiento(valor)

    def validate(self, data):
        errores = {}
        if data['password1'] != data['password2']:
            errores['password2'] = ['Las dos contraseñas deben coincidir.']
        if data['email'].lower() != data['email2'].strip().lower():
            errores['email2'] = ['Los dos correos deben coincidir.']
        if errores:
            raise serializers.ValidationError(errores)
        return data

    def get_cleaned_data(self):
        datos = super().get_cleaned_data()
        datos['first_name'] = self.validated_data['first_name']
        datos['last_name'] = self.validated_data['last_name']
        return datos

    def save(self, request):
        v = self.validated_data
        try:
            # Usuario y perfil en la misma transacción: si el perfil falla, el
            # usuario no queda huérfano.
            with transaction.atomic():
                user = super().save(request)
                UserProfile.objects.create(
                    user=user, dni=v['dni'], rank=v['rank'],
                    destination=v['destination'], birth_date=v['birth_date'],
                )
        except IntegrityError:
            # Dos registros simultáneos con el mismo DNI pasan los dos la
            # validación y chocan en la restricción única.
            if UserProfile.objects.filter(dni=v['dni']).exists():
                raise serializers.ValidationError({'dni': [DNI_REPETIDO]})
            raise
        return user


class CorregirCorreoSerializer(serializers.Serializer):
    """El correo del que llama, nunca el de otro: el usuario sale de la sesión."""
    email = serializers.EmailField(error_messages=ERRORES_DE_CORREO)

    def validate_email(self, email):
        email = email.strip()
        if _correo_en_uso(email, excluyendo=self.context['request'].user):
            raise serializers.ValidationError(CORREO_EN_USO)
        return email

    def save(self):
        user = self.context['request'].user
        correo = self.validated_data['email']
        # El correo vive en `User` y allauth guarda su propia copia: con una sola
        # actualizada, el login por correo deja afuera al usuario.
        with transaction.atomic():
            user.email = correo
            user.save(update_fields=['email'])
            EmailAddress.objects.filter(user=user).delete()
            EmailAddress.objects.create(
                user=user, email=correo, primary=True, verified=False)
        return user
