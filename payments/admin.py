from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway_order_id", "gateway_payment_id", "amount", "currency", "status")
    list_filter = ("status", "currency")
    search_fields = ("order__order_number", "gateway_order_id", "gateway_payment_id")
    readonly_fields = (
        "order",
        "user",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        "amount",
        "currency",
        "status",
        "failure_reason",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
