from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet, ProfileFieldTemplateViewSet,
    StudyBlockViewSet, CommentViewSet, PermissionViewSet,
    DiveActivityViewSet, DiveLogViewSet, SuperUserViewSet,
    FechasView, MiFechaView, MiEstadoView, GradosView, MiCorreoView,
    RolesAdminView, FechasAdminView, PlantelView,
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'templates', ProfileFieldTemplateViewSet, basename='template')
router.register(r'blocks', StudyBlockViewSet, basename='block')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'dive-activities', DiveActivityViewSet, basename='diveactivity')
router.register(r'dive-logs', DiveLogViewSet, basename='divelog')
router.register(r'superusers', SuperUserViewSet, basename='superuser')

urlpatterns = [
    path('fechas/', FechasView.as_view(), name='fechas'),
    path('mi-fecha/', MiFechaView.as_view(), name='mi-fecha'),
    path('mi-estado/', MiEstadoView.as_view(), name='mi-estado'),
    path('grados/', GradosView.as_view(), name='grados'),
    path('mi-correo/', MiCorreoView.as_view(), name='mi-correo'),
    # Las dos pantallas del administrador de la unidad. Van antes del
    # router para que `admin/` no la agarre ninguna ruta generada.
    path('admin/roles/', RolesAdminView.as_view(), name='admin-roles'),
    path('admin/fechas/', FechasAdminView.as_view(), name='admin-fechas'),
    # El plantel del médico. Antes del router por la misma razón que arriba.
    path('plantel/', PlantelView.as_view(), name='plantel'),
    path('', include(router.urls)),
]
