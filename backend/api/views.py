import logging

from rest_framework import generics, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Prefetch, Q
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import (
    StudyBlock, Comment, Permission, DiveActivity, DiveLog, HabilitationWindow,
)
from users.models import UserProfile, ProfileFieldTemplate
from .serializers import (
    StudyBlockSerializer, CommentSerializer, PermissionSerializer,
    UserProfileSerializer, ProfileFieldTemplateSerializer,
    DiveActivitySerializer, DiveLogSerializer,
    HabilitationWindowSerializer, InscripcionSerializer,
)
from . import serializers as _serializers
from .estado import armar_estado
from .images import ArchivoRechazado, comprimir
from .report_pdf import generate_anexo_27
# §5, en su propio modulo porque tambien lo consultan los serializadores.
from .roles import REVIEWER_ROLES, es_revisor  # noqa: F401  (re-export)

# Los errores de validacion se registran, no se imprimen: un print va a stdout
# y contamina la salida de los tests y del servidor.
logger = logging.getLogger(__name__)


class SoloElDuenoDelPerfil(permissions.BasePermission):
    """Un perfil lo modifica y lo borra sólo su dueño. La lectura no se toca.

    Hermano de `SoloElDuenoDelEstudio`, y por el mismo agujero: sin control a
    nivel de objeto, un grantee con una concesión de **sólo lectura** podía
    reescribir el perfil del grantor —rol y DNI incluidos— y borrarlo (204).

    El queryset de abajo sirve sólo el perfil propio, así que hoy un perfil
    ajeno da 404 antes de llegar acá. La regla existe igual porque el §8.1 pide
    un listado de 150 buzos para el médico: cuando el plan que lo construya
    ensanche ese queryset, que el médico pueda **ver** 150 perfiles no puede
    volverse poder reescribirlos. El §5 le da ver, aprobar y rechazar.
    """

    message = 'Sólo el dueño del perfil puede modificarlo o borrarlo.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.pk


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, SoloElDuenoDelPerfil]

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(profile, data=request.data, partial=(request.method == 'PATCH'))
            if not serializer.is_valid():
                logger.debug("Perfil: validacion rechazada: %s", serializer.errors)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
            
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def get_queryset(self):
        # D-5 sobre el endpoint que el cierre del plan 1 no convirtió: el acceso
        # sale del rol, no de concesiones entre usuarios. Acá la concesión
        # `PERSONAL_DATA`/`ALL` seguía rigiendo de verdad, y es textualmente la
        # ruta que D-5 condena — el buzo le entregaba su DNI, su fecha de
        # nacimiento, su grado y su destino a cualquier usuario registrado, con
        # el registro abierto y sin verificación de correo.
        #
        # Queda en lo propio y nada más. El §8.1 pide además un listado de 150
        # buzos con grado, nombre y unidad para el médico: eso es una vista que
        # todavía no existe y la construye el plan que haga su pantalla, con el
        # rol como base igual que `StudyBlockViewSet`. Ensancharlo acá ahora le
        # cambiaría la respuesta a `Dashboard.jsx:56` sin pantalla que lo use.
        return UserProfile.objects.filter(user=self.request.user)

class ProfileFieldTemplateViewSet(viewsets.ModelViewSet):
    queryset = ProfileFieldTemplate.objects.all()
    serializer_class = ProfileFieldTemplateSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can manage templates

class SoloElDuenoDelEstudio(permissions.BasePermission):
    """Un estudio lo modifica y lo borra sólo su dueño. La lectura no se toca.

    Que el buzo borre sus propios estudios cuando quiera es diseño, no un
    agujero: al borrarse, sus dictámenes se van en cascada (`Comment.block` es
    CASCADE), el punto queda faltante y, si sube otro, arranca sin dictamen y
    vuelve a revisión — por ese camino nadie queda apto. Lo que hay que cerrar
    es la escritura sobre el estudio de otro. Antes la abría una concesión de
    `Permission`, que metía el bloque ajeno en el queryset: un buzo con un
    permiso de sólo lectura podía borrar el registro médico del grantor (204).
    Y con el acceso por rol del §5 el revisor ve a todos los buzos, así que sin
    esto podría borrar o editar el estudio de cualquiera; el §5 le da ver,
    aprobar y rechazar — no modificar ni borrar.

    No es el §15.10 —qué estados le permiten al buzo reemplazar lo propio—, que
    sigue sin implementar.
    """

    message = 'Sólo el dueño del estudio puede modificarlo o borrarlo.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.pk


class StudyBlockViewSet(viewsets.ModelViewSet):
    queryset = StudyBlock.objects.all()
    serializer_class = StudyBlockSerializer
    permission_classes = [permissions.IsAuthenticated, SoloElDuenoDelEstudio]
    # Sin PUT ni PATCH: un estudio no se edita, se reemplaza con un POST al mismo
    # punto. Editar el archivo en el lugar esquivaba la regla del reemplazo y la
    # compresión, y le cambiaba el papel al médico a sus espaldas (§15.10).
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        try:
            user = self.request.user
            # §5: el revisor designado ve a todos los buzos; el buzo, sólo lo
            # suyo. Nada de concesiones: ver `es_revisor` arriba.
            if es_revisor(user):
                queryset = StudyBlock.objects.all()
            else:
                queryset = StudyBlock.objects.filter(user=user)
            # §6: el estudio reemplazado no es visible en la vista normal. El
            # historial se pide a propósito, con ?historico=1; cualquier otro
            # valor deja la vista normal. Sin pantalla: el plan 2 la construye.
            if self.request.query_params.get('historico') != '1':
                queryset = queryset.filter(is_current=True)
            return queryset
        except Exception as e:
            logger.exception("Estudios: fallo al armar el queryset")
            raise

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            logger.debug("Estudios: validacion rechazada: %s", e.detail)
            raise

    def perform_create(self, serializer):
        # Las fotos se reducen en el servidor, antes de guardarlas: un rechazo
        # del archivo es un 400 con el mensaje ya redactado, no un 500.
        try:
            archivo = comprimir(serializer.validated_data['pdf_attachment'])
        except ArchivoRechazado as e:
            raise ValidationError({'pdf_attachment': e.mensaje})
        serializer.save(user=self.request.user, pdf_attachment=archivo)

class Anexo27View(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        # Sin la guarda, un id inexistente propaga `DoesNotExist` y sale como
        # 500 — con DEBUG=True, un traceback.
        user = get_object_or_404(User, pk=pk)
        # §5 sobre el tercer endpoint que sirve el registro médico, y el que lo
        # sirve como el documento que firma un oficial: el revisor designado ve
        # los estudios de todos, así que puede emitir el formulario. Decidía por
        # `is_staff`, que es la llave del admin de Django y no tiene nada que ver
        # con el §5: el médico designado recibía 403 sobre el formulario que el
        # sistema existe para producir.
        #
        # `is_staff` se conserva igual: D-1 deja el admin de Django como acceso
        # crudo y salida de emergencia hasta que exista la pantalla propia del
        # admin, así que ya ve los estudios y los dictámenes por ahí. Negarle
        # este endpoint mientras el panel sirve los mismos datos no protegería
        # nada.
        if (request.user != user
                and not es_revisor(request.user)
                and not request.user.is_staff):
            return HttpResponse("Unauthorized", status=403)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="anexo_27_{user.username}.pdf"'
        
        generate_anexo_27(response, user)
        return response

class SoloQuienDictamino(permissions.BasePermission):
    """Un dictamen lo edita y lo borra sólo quien lo emitió. Nadie más, nunca.

    `CommentViewSet` no tenía ningún control en `update` ni en `destroy`, y el
    registro es abierto (`core/urls.py`, `ACCOUNT_EMAIL_VERIFICATION='none'`).
    Un `PATCH {status: "APPROVED", reviewer_role: "DOCTOR"}` sobre el dictamen
    de otro dejaba la fila diciendo que el médico aprobó, con `doctor` todavía
    apuntando al médico real: `fitness` no guarda la aptitud, la deriva de esa
    fila, así que fabricarla es declarar apto a un buzo sin que el médico haya
    dicho nada. Un rechazo borrado por el propio buzo no produce aptitud, pero
    destruye el motivo y el detalle que el §9 manda por correo.

    La lectura no se toca: la ficha del buzo y el listado del médico la usan.

    Y hace falta **seguir** designado, no haberlo estado. El §5 condiciona la
    facultad a la designación en presente ("designado por el admin") y su tabla
    no tiene una fila para "ex-médico": a quien el admin le saca la designación
    lo pone en la fila "Buzo | Ve y gestiona sus propios estudios. Nada más."
    Sin esto, el enfermero al que le sacaron la designación convertía su
    pre-aprobación en la aprobación del médico —verificado: PATCH
    `{status: APPROVED}` daba 200— y el motor la lee como la palabra final. Era
    el mismo riesgo de falsificación de arriba con un paso previo. La asimetría
    lo delataba: ya no podía ver el estudio pero sí reescribir el dictamen sobre
    ese estudio.
    """

    message = 'Un dictamen lo puede modificar o borrar sólo quien lo emitió.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return es_revisor(request.user) and obj.doctor_id == request.user.pk

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, SoloQuienDictamino]

    def get_queryset(self):
        # §5 sobre la misma base que los estudios, porque el dictamen es el
        # contenido de la revisión: el revisor designado ve todos; el buzo ve los
        # de sus propios estudios, que el §6 le muestra textuales con el motivo y
        # el detalle; nadie más ve ninguno. `Comment.objects.all()` le servía a
        # cualquier usuario autenticado el rechazo de cualquier buzo.
        user = self.request.user
        if es_revisor(user):
            return Comment.objects.all()
        # Lo que uno mismo dictaminó lo ve siempre: si no, a quien el admin le
        # saca la designación deja de poder corregir lo que firmó, y
        # `SoloQuienDictamino` no tendría nunca sobre qué fila pronunciarse.
        return Comment.objects.filter(Q(block__user=user) | Q(doctor=user)).distinct()

    def perform_create(self, serializer):
        # §5: dictamina el médico o un enfermero auxiliar designado por el
        # admin, y nadie más. Antes lo habilitaba una concesión del propio buzo,
        # que es al revés: el buzo le podía dar la revisión de sus estudios a
        # cualquier usuario registrado. El §15.9 —nadie dictamina sobre sus
        # propios estudios— lo aplica CommentSerializer.validate, encima de esto.
        if not es_revisor(self.request.user):
            raise PermissionDenied(
                'Sólo el médico o un enfermero auxiliar designados pueden '
                'dictaminar sobre un estudio médico.')
        # `reviewer_role` sale del perfil, no del cuerpo del pedido: es en
        # calidad de qué firma, y el §6 dice que "lo único que el médico no
        # puede delegar es decir que alguien está apto". `es_revisor` de arriba
        # ya garantizó que el perfil existe y que el rol es uno de los dos.
        serializer.save(
            doctor=self.request.user,
            reviewer_role=self.request.user.profile.role)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            logger.debug("Dictamen: validacion rechazada: %s", e.detail)
            raise

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return permissions where the user is the grantor
        # This prevents the grantee from seeing or modifying them via the API
        return Permission.objects.filter(grantor=self.request.user)

    def perform_destroy(self, instance):
        if instance.grantor != self.request.user:
            raise PermissionDenied("Solo el creador del permiso puede revocarlo.")
        instance.delete()

    def perform_create(self, serializer):
        email = self.request.data.get('grantee_email')
        if email:
            try:
                grantee = User.objects.get(email=email)
                serializer.save(grantor=self.request.user, grantee=grantee)
            except User.DoesNotExist:
                raise ValidationError({"grantee_email": "Usuario con este correo no existe."})
        else:
            serializer.save(grantor=self.request.user)
    
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            logger.debug("Permiso: validacion rechazada: %s", e.detail)
            raise

from django.utils import timezone

class DiveActivityViewSet(viewsets.ModelViewSet):
    queryset = DiveActivity.objects.all()
    serializer_class = DiveActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DiveActivity.objects.filter(instructor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

class DiveLogViewSet(viewsets.ModelViewSet):
    queryset = DiveLog.objects.all()
    serializer_class = DiveLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DiveLog.objects.all()
        return DiveLog.objects.filter(Q(activity__instructor=user) | Q(diver=user))

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_token(self, request):
        activity_id = request.data.get('activity_id')
        if not activity_id:
            return Response({"error": "activity_id is required"}, status=400)
        try:
            activity = DiveActivity.objects.get(id=activity_id, instructor=request.user)
        except DiveActivity.DoesNotExist:
            return Response({"error": "Activity not found or not owned by you"}, status=404)
        
        data = request.data
        log = DiveLog.objects.create(
            activity=activity,
            residual_nitrogen_post=data.get('residual_nitrogen_post', ''),
            residual_nitrogen_pre=data.get('residual_nitrogen_pre', ''),
            decompression_stop=str(data.get('decompression_stop', 'false')).lower() == 'true',
            decompression_depth_meters=data.get('decompression_depth_meters') or None,
            decompression_time_minutes=data.get('decompression_time_minutes') or None,
            equipment_type=data.get('equipment_type', ''),
            gas_type=data.get('gas_type', 'Aire'),
            suit_type=data.get('suit_type', ''),
            weight_kgs=data.get('weight_kgs') or None,
            tank_type=data.get('tank_type', ''),
            start_pressure_bar=data.get('start_pressure_bar') or None,
            end_pressure_bar=data.get('end_pressure_bar') or None,
            diver_notes=data.get('diver_notes', '')
        )
        
        if 'dive_graph' in request.FILES:
            log.dive_graph = request.FILES['dive_graph']
            log.save()
            
        return Response({"token": str(log.token)})

    @action(detail=False, methods=['get'], url_path='by-token/(?P<token>[^/.]+)')
    def get_by_token(self, request, token=None):
        try:
            log = DiveLog.objects.get(token=token)
        except DiveLog.DoesNotExist:
            return Response({"error": "Invalid token"}, status=404)
        
        serializer = self.get_serializer(log)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='by-token/(?P<token>[^/.]+)/complete')
    def complete_log(self, request, token=None):
        try:
            log = DiveLog.objects.get(token=token)
        except DiveLog.DoesNotExist:
            return Response({"error": "Invalid token"}, status=404)
            
        if log.is_completed:
            return Response({"error": "This log has already been completed"}, status=400)
            
        log.diver = request.user
        log.is_completed = True
        log.completed_at = timezone.now()
        log.save()
        
        serializer = self.get_serializer(log)
        return Response(serializer.data)

class SuperUserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['post'])
    def promote(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            return Response({"message": f"{email} is now a superuser."})
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

    @action(detail=False, methods=['post'], url_path='promote-instructor')
    def promote_instructor(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_instructor = True
            profile.save()
            return Response({"message": f"{email} ahora tiene permisos de Instructor."})
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)


class FechasView(generics.ListAPIView):
    """Las fechas de habilitación publicadas, por `start_date`. Sólo lectura."""
    queryset = HabilitationWindow.objects.order_by('start_date')
    serializer_class = HabilitationWindowSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class MiFechaView(APIView):
    """Inscribe al que llama a una fecha, o lo desinscribe con `null`.

    Escribe siempre el perfil de `request.user`: no hay id de usuario ni de
    perfil en el cuerpo, de modo que no hay forma de apuntar a otro.
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = InscripcionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.habilitation_window = serializer.validated_data['window']
        profile.save(update_fields=['habilitation_window'])
        return Response({'window': profile.habilitation_window_id})


class MiEstadoView(APIView):
    """El estado del que llama, tal como lo muestra su pantalla.

    Sólo lectura y sin parámetros: lee el perfil de `request.user`, así que no
    hay forma de pedir el de otro. Trae el perfil con su ventana, y los
    estudios vigentes con sus dictámenes, en un número fijo de consultas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        profile = UserProfile.objects.select_related(
            'user', 'habilitation_window',
        ).prefetch_related(
            Prefetch(
                'user__study_blocks',
                queryset=StudyBlock.objects.filter(is_current=True)
                .prefetch_related('comments'),
            ),
        ).get(user=request.user)
        # La fecha sale de la costura de `serializers`, que los tests congelan.
        return Response(armar_estado(profile, _serializers.hoy(), request=request))
