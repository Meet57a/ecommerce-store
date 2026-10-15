from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__username")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "user", "status", "address_line_1", "address_line_2", "city", "state", "postal_code", "country", "subtotal", "shipping_charge", "discount", "total", "created_at", "updated_at")
