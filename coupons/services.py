from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Coupon, CouponUsage


class CouponError(ValueError):
    pass


def get_valid_coupon(code, user, subtotal, for_update=False):
    queryset = Coupon.objects
    if for_update:
        queryset = queryset.select_for_update()
    coupon = queryset.filter(code__iexact=code.strip()).first()
    now = timezone.now()
    if not coupon or not coupon.is_active:
        raise CouponError("This coupon is not available.")
    if now < coupon.starts_at or now >= coupon.expires_at:
        raise CouponError("This coupon has expired or is not active yet.")
    if subtotal < coupon.minimum_order_amount:
        raise CouponError(f"This coupon requires a minimum order of ₹{coupon.minimum_order_amount}.")
    total_uses = coupon.usages.count()
    if coupon.maximum_uses is not None and total_uses >= coupon.maximum_uses:
        raise CouponError("This coupon has reached its usage limit.")
    if coupon.per_customer_limit is not None and CouponUsage.objects.filter(
        coupon=coupon,
        user=user,
    ).count() >= coupon.per_customer_limit:
        raise CouponError("You have reached this coupon's usage limit.")
    return coupon


def discount_for(coupon, subtotal):
    if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
        discount = subtotal * coupon.discount_value / Decimal("100")
    else:
        discount = coupon.discount_value
    return min(discount, subtotal)


@transaction.atomic
def record_coupon_usage(order, coupon_id):
    if not coupon_id:
        return None
    coupon = Coupon.objects.select_for_update().get(pk=coupon_id)
    existing = CouponUsage.objects.filter(order=order).first()
    if existing:
        return existing
    get_valid_coupon(coupon.code, order.user, order.subtotal, for_update=True)
    discount_amount = discount_for(coupon, order.subtotal)
    return CouponUsage.objects.create(
        coupon=coupon,
        user=order.user,
        order=order,
        discount_amount=discount_amount,
    )
