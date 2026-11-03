from django.contrib import admin

from users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('rank', 'last_name', 'first_name', 'dni', 'email', 'role')
    search_fields = ('dni', 'user__last_name', 'user__first_name')

    @admin.display(description='Apellido', ordering='user__last_name')
    def last_name(self, obj):
        return obj.user.last_name

    @admin.display(description='Nombre', ordering='user__first_name')
    def first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='Correo', ordering='user__email')
    def email(self, obj):
        return obj.user.email
