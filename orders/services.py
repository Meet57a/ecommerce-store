from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalog.models import Product

FREE_SHIPPING_THRESHOLD = Decimal("1000.00")
STANDARD_SHIPPING = Decimal("99.00")


def calculate_totals(cart, user=None, coupon=None):
    subtotal = cart.subtotal
    shipping_charge = Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else STANDARD_SHIPPING
    discount = Decimal("0.00")
    if coupon:
        from coupons.services import discount_for
        discount = discount_for(coupon, subtotal)
    return {
        "subtotal": subtotal,
        "shipping_charge": shipping_charge,
        "discount": discount,
        "total": max(Decimal("0.00"), subtotal + shipping_charge - discount),
    }


@transaction.atomic
def cancel_order_and_release_stock(order):
    locked_order = type(order).objects.select_for_update().get(pk=order.pk)
    if not locked_order.can_cancel:
        return locked_order
    for item in locked_order.items.all():
        product = Product.objects.select_for_update().get(pk=item.product_id)
        product.stock_quantity += item.quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
    locked_order.status = locked_order.Status.CANCELLED
    locked_order.save(update_fields=["status", "updated_at"])
    payment = getattr(locked_order, "payment", None)
    if payment and payment.status not in {"captured", "refunded"}:
        payment.status = "cancelled"
        payment.save(update_fields=["status", "updated_at"])
    return locked_order


def expire_pending_orders(hours=24):
    from .models import Order

    cutoff = timezone.now() - timedelta(hours=hours)
    expired = []
    for order in Order.objects.filter(
        status=Order.Status.PENDING_PAYMENT,
        created_at__lt=cutoff,
    ).iterator():
        expired.append(cancel_order_and_release_stock(order).pk)
    return expired
