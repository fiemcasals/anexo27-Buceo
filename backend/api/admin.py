from django.contrib import admin

from .models import HabilitationWindow


@admin.register(HabilitationWindow)
class HabilitationWindowAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'slot', 'start_date', 'end_date')
    list_filter = ('cycle', 'slot')
