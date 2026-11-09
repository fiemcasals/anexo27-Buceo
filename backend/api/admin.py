from django.contrib import admin

from .models import HabilitationEnrollment, HabilitationWindow


@admin.register(HabilitationWindow)
class HabilitationWindowAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'slot', 'start_date', 'end_date')
    list_filter = ('cycle', 'slot')


@admin.register(HabilitationEnrollment)
class HabilitationEnrollmentAdmin(admin.ModelAdmin):
    """Sólo lectura: es el historial, no se edita a mano."""
    list_display = ('user', 'cycle', 'window', 'chosen_at')
    list_filter = ('cycle',)
    search_fields = ('user__username', 'user__email', 'user__last_name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
