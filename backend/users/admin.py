from django.contrib import admin

from users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('rank', 'last_name', 'first_name', 'dni', 'email', 'role')
    search_fields = ('dni', 'user__last_name', 'user__first_name')
    # Tres de las columnas salen de `user`: sin esto, 150 consultas de mas en la
    # unica lista que el spec pide que sea comoda (§8.5).
    list_select_related = ('user',)

    @admin.display(description='Apellido', ordering='user__last_name')
    def last_name(self, obj):
        return obj.user.last_name

    @admin.display(description='Nombre', ordering='user__first_name')
    def first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='Correo', ordering='user__email')
    def email(self, obj):
        return obj.user.email


# El panel es la unica interfaz humana que entrega esta rama, y la usa un oficial
# de la unidad: "Django administration" no le dice nada.
admin.site.site_header = 'Control de aptitud médica para buceo'
admin.site.site_title = 'Aptitud médica'
admin.site.index_title = 'Administración'
