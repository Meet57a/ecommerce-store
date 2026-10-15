from django.contrib import admin

from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "starts_at", "expires_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "order", "discount_amount", "used_at")
    readonly_fields = ("coupon", "user", "order", "discount_amount", "used_at")
    has_add_permission = lambda self, request: False
