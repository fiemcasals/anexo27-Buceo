from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet, ProfileFieldTemplateViewSet,
    StudyBlockViewSet, CommentViewSet, PermissionViewSet,
    Anexo27View, DiveActivityViewSet, DiveLogViewSet, SuperUserViewSet
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'templates', ProfileFieldTemplateViewSet, basename='template')
router.register(r'blocks', StudyBlockViewSet, basename='block')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'anexo27', Anexo27View, basename='anexo27')
router.register(r'dive-activities', DiveActivityViewSet, basename='diveactivity')
router.register(r'dive-logs', DiveLogViewSet, basename='divelog')
router.register(r'superusers', SuperUserViewSet, basename='superuser')

urlpatterns = [
    path('', include(router.urls)),
]
