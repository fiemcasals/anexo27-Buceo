from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from .models import StudyBlock, Comment, Permission, DiveActivity, DiveLog, AuditorScope
from users.models import UserProfile, ProfileFieldTemplate, Specialty
from .serializers import (
    StudyBlockSerializer, CommentSerializer, PermissionSerializer,
    UserProfileSerializer, ProfileFieldTemplateSerializer,
    DiveActivitySerializer, DiveLogSerializer, SpecialtySerializer,
    AuditorScopeSerializer
)
from .report_pdf import generate_anexo_27

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(profile, data=request.data, partial=(request.method == 'PATCH'))
            if not serializer.is_valid():
                print(f"DEBUG: Profile update validation error: {serializer.errors}")
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
            
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='accept-terms')
    def accept_terms(self, request):
        """Sella la fecha en que la persona acepto las condiciones de uso."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.terms_accepted_at = timezone.now()
        profile.save(update_fields=['terms_accepted_at'])
        return Response(self.get_serializer(profile).data)

    def get_queryset(self):
        user = self.request.user
        
        # Own profile
        q_own = Q(user=user)
        
        # Profiles shared with me
        shared_perms = Permission.objects.filter(grantee=user)
        grantor_ids = []
        for p in shared_perms:
            if "ALL" in p.shared_items or "PERSONAL_DATA" in p.shared_items:
                grantor_ids.append(p.grantor_id)

        # Buzos habilitados por el admin segun rango de edad
        grantor_ids.extend(AuditorScope.divers_for(user))

        q_shared = Q(user_id__in=grantor_ids)
        return UserProfile.objects.filter(q_own | q_shared).distinct()

class ProfileFieldTemplateViewSet(viewsets.ModelViewSet):
    queryset = ProfileFieldTemplate.objects.all()
    serializer_class = ProfileFieldTemplateSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can manage templates

class SpecialtyViewSet(viewsets.ModelViewSet):
    """Todos leen el desplegable; solo el admin lo administra."""
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

class StudyBlockViewSet(viewsets.ModelViewSet):
    queryset = StudyBlock.objects.all()
    serializer_class = StudyBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            user = self.request.user
            
            # Own blocks
            q_own = Q(user=user)
            
            # Shared blocks
            shared_perms = Permission.objects.filter(grantee=user)
            grantor_ids = []
            specific_ids = []
            
            for perm in shared_perms:
                if "ALL" in perm.shared_items:
                    grantor_ids.append(perm.grantor_id)
                else:
                    for item in perm.shared_items:
                        try:
                            # Skip special strings like "PERSONAL_DATA" which might be in shared_items
                            if str(item).isdigit():
                                specific_ids.append(int(item))
                        except (ValueError, TypeError):
                            continue
            
            # Habilitacion institucional por rango de edad (panel de administracion)
            grantor_ids.extend(AuditorScope.divers_for(user))

            q_shared = Q(user_id__in=grantor_ids) | Q(id__in=specific_ids)
            return StudyBlock.objects.filter(q_own | q_shared).distinct().prefetch_related(
                'comments__doctor__profile__specialty'
            )
        except Exception as e:
            print(f"DEBUG: StudyBlock get_queryset error: {str(e)}")
            raise

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            print(f"DEBUG: StudyBlock validation error: {e.detail}")
            raise

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class Anexo27View(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        user = User.objects.get(pk=pk)
        # Check if user has permission or is staff
        if (request.user != user and not request.user.is_staff
                and user.id not in AuditorScope.divers_for(request.user)):
            return HttpResponse("Unauthorized", status=403)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="anexo_27_{user.username}.pdf"'
        
        generate_anexo_27(response, user)
        return response

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        block = serializer.validated_data.get('block')
        user = self.request.user
        
        if block.user != user:
            has_permission = any(
                perm.covers(block.id)
                for perm in Permission.objects.filter(
                    grantor=block.user, grantee=user, access_level='MODIFY'
                )
            )

            if not has_permission:
                has_permission = any(
                    scope.covers_user(block.user)
                    for scope in AuditorScope.objects.filter(grantee=user, access_level='MODIFY')
                )

            if not has_permission:
                raise PermissionDenied("No tienes permisos de Médico Auditor para comentar en este estudio.")
                
        serializer.save(doctor=user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            print(f"DEBUG: Comment validation error: {e.detail}")
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
            print(f"DEBUG: Permission validation error: {e.detail}")
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

class AuditorScopeViewSet(viewsets.ModelViewSet):
    """Habilitaciones de lectura/dictamen por rango de edad.

    El admin las administra; cualquier usuario puede listar (solo lectura) las que
    lo alcanzan, para ver quien tiene acceso a sus estudios sin haberlo compartido.
    """
    queryset = AuditorScope.objects.select_related('grantee')
    serializer_class = AuditorScopeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(id__in=[s.id for s in AuditorScope.covering(user)])

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SuperUserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'], url_path='privileged')
    def list_privileged(self, request):
        results = []
        superusers = User.objects.filter(is_superuser=True).exclude(pk=request.user.pk)
        for u in superusers:
            results.append({
                'id': u.id, 'email': u.email,
                'name': f"{u.first_name} {u.last_name}".strip() or u.username,
                'role': 'superuser'
            })
        instructors = UserProfile.objects.filter(is_instructor=True).exclude(user=request.user)
        for p in instructors:
            if not p.user.is_superuser:
                results.append({
                    'id': p.user.id, 'email': p.user.email,
                    'name': f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username,
                    'role': 'instructor'
                })
        return Response(results)

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

    @action(detail=False, methods=['post'], url_path='revoke')
    def revoke(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            user.is_superuser = False
            user.is_staff = False
            user.save()
            return Response({"message": f"Permisos de superusuario revocados para {email}."})
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado."}, status=404)

    @action(detail=False, methods=['post'], url_path='revoke-instructor')
    def revoke_instructor(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_instructor = False
            profile.save()
            return Response({"message": f"Permisos de instructor revocados para {email}."})
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado."}, status=404)

    @action(detail=False, methods=['get'], url_path='all-dive-logs')
    def all_dive_logs(self, request):
        from .serializers import DiveLogSerializer
        logs = DiveLog.objects.filter(
            is_completed=True, diver__isnull=False
        ).select_related(
            'diver', 'diver__profile', 'activity'
        ).order_by('diver__email', '-activity__date')

        grouped = {}
        for log in logs:
            diver = log.diver
            uid = diver.id
            if uid not in grouped:
                profile = getattr(diver, 'profile', None)
                grouped[uid] = {
                    'user_id': uid,
                    'email': diver.email,
                    'first_name': diver.first_name,
                    'last_name': diver.last_name,
                    'profile': {
                        'dni': profile.dni if profile else '',
                        'age': profile.age if profile else None,
                        'phone': profile.phone if profile else '',
                        'rank': profile.rank if profile else '',
                        'destination': profile.destination if profile else '',
                        'weight': profile.weight if profile else None,
                        'height': profile.height if profile else None,
                    },
                    'dive_logs': []
                }
            serializer = DiveLogSerializer(log, context={'request': request})
            grouped[uid]['dive_logs'].append(serializer.data)

        return Response(list(grouped.values()))


class SupportViewSet(viewsets.ViewSet):
    """Boton Soporte: el reporte sale por correo, no se guarda en la base."""
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({"error": "Contanos qué pasó antes de enviar."}, status=400)

        step = (request.data.get('step') or 'Otro / no está en la lista').strip()
        fecha = timezone.localtime().strftime('%d/%m/%Y %H:%M')
        email = request.user.email or request.user.username

        EmailMessage(
            subject=f"[Anexo Buceo] Soporte: {step}",
            body=(
                "Reporte enviado desde el botón Soporte de Anexo Buceo.\n\n"
                f"Usuario: {email}\n"
                f"Paso: {step}\n"
                f"Fecha: {fecha}\n\n"
                f"{message}\n"
            ),
            to=settings.SUPPORT_RECIPIENTS,
            reply_to=[request.user.email] if request.user.email else None,
        ).send()

        return Response({"message": "Reporte enviado. ¡Gracias!"}, status=201)
