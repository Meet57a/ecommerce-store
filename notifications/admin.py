from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("order", "event", "user", "sent_at")
    readonly_fields = ("order", "event", "user", "sent_at")
    has_add_permission = lambda self, request: False
    has_delete_permission = lambda self, request, obj=None: False
