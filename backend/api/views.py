from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf import settings
from .models import StudyBlock, Comment, Permission, DiveActivity, DiveLog
from users.models import UserProfile, ProfileFieldTemplate
from .serializers import (
    StudyBlockSerializer, CommentSerializer, PermissionSerializer,
    UserProfileSerializer, ProfileFieldTemplateSerializer,
    DiveActivitySerializer, DiveLogSerializer
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
        
        q_shared = Q(user_id__in=grantor_ids)
        return UserProfile.objects.filter(q_own | q_shared).distinct()

class ProfileFieldTemplateViewSet(viewsets.ModelViewSet):
    queryset = ProfileFieldTemplate.objects.all()
    serializer_class = ProfileFieldTemplateSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can manage templates

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
            
            q_shared = Q(user_id__in=grantor_ids) | Q(id__in=specific_ids)
            return StudyBlock.objects.filter(q_own | q_shared).distinct()
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
        if request.user != user and not request.user.is_staff:
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
            has_permission = Permission.objects.filter(
                grantor=block.user, 
                grantee=user, 
                access_level='MODIFY'
            ).filter(
                Q(shared_items__contains="ALL") | Q(shared_items__contains=str(block.id))
            ).exists()
            
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
