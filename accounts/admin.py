from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "state", "country", "updated_at")
    search_fields = ("user__username", "user__email", "city", "postal_code")
