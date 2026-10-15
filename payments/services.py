from decimal import Decimal

import razorpay
from django.conf import settings
from django.db import transaction

from orders.models import Order

from .models import Payment


class PaymentConfigurationError(RuntimeError):
    pass


def get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise PaymentConfigurationError("Razorpay test credentials are not configured.")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_gateway_order(order):
    client = get_razorpay_client()
    amount_paise = int((order.total * Decimal("100")).quantize(Decimal("1")))
    gateway_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": order.order_number,
        "notes": {"order_number": order.order_number},
    })
    return Payment.objects.create(
        order=order,
        user=order.user,
        gateway_order_id=gateway_order["id"],
        amount=order.total,
        currency="INR",
    )


@transaction.atomic
def verify_payment(order, payment_id, gateway_order_id, signature):
    payment = Payment.objects.select_for_update().select_related("order").get(order=order)
    if payment.status == Payment.Status.CAPTURED:
        return payment
    if payment.gateway_order_id != gateway_order_id or payment.amount != order.total or payment.currency != "INR":
        raise ValueError("Payment details do not match the order.")
    client = get_razorpay_client()
    client.utility.verify_payment_signature({
        "razorpay_payment_id": payment_id,
        "razorpay_order_id": gateway_order_id,
        "razorpay_signature": signature,
    })
    gateway_payment = client.payment.fetch(payment_id)
    if (
        gateway_payment.get("order_id") != gateway_order_id
        or int(gateway_payment.get("amount", -1)) != payment.amount_paise
        or gateway_payment.get("currency") != payment.currency
        or gateway_payment.get("status") not in {"authorized", "captured"}
    ):
        raise ValueError("Gateway payment details do not match the order.")
    payment.gateway_payment_id = payment_id
    payment.gateway_signature = signature
    payment.status = Payment.Status.CAPTURED
    payment.save(update_fields=["gateway_payment_id", "gateway_signature", "status", "updated_at"])
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    from coupons.services import record_coupon_usage
    from notifications.services import send_order_confirmed, send_payment_confirmed
    record_coupon_usage(order, order.coupon_id)
    send_order_confirmed(order)
    send_payment_confirmed(order)
    return payment


def verify_webhook(raw_body, signature):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise PaymentConfigurationError("Razorpay webhook secret is not configured.")
    get_razorpay_client().utility.verify_webhook_signature(
        raw_body,
        signature,
        settings.RAZORPAY_WEBHOOK_SECRET,
    )


@transaction.atomic
def process_webhook_event(payload):
    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
    entity = payment_entity or order_entity
    gateway_order_id = entity.get("order_id") or order_entity.get("id")
    payment_id = payment_entity.get("id")
    if not gateway_order_id:
        return False
    payment = Payment.objects.select_for_update().filter(gateway_order_id=gateway_order_id).first()
    if not payment:
        return False
    if event in {"payment.captured", "order.paid"} and payment.status != Payment.Status.CAPTURED:
        gateway_amount = entity.get("amount")
        if event == "order.paid":
            gateway_amount = order_entity.get("amount_paid", order_entity.get("amount"))
        if gateway_amount is not None and int(gateway_amount) != payment.amount_paise:
            return False
        payment.status = Payment.Status.CAPTURED
        payment.gateway_payment_id = payment_id or payment.gateway_payment_id
        payment.save(update_fields=["status", "gateway_payment_id", "updated_at"])
        Order.objects.filter(pk=payment.order_id, status=Order.Status.PENDING_PAYMENT).update(
            status=Order.Status.CONFIRMED,
        )
        payment.order.refresh_from_db()
        from coupons.services import record_coupon_usage
        from notifications.services import send_order_confirmed, send_payment_confirmed
        record_coupon_usage(payment.order, payment.order.coupon_id)
        send_order_confirmed(payment.order)
        send_payment_confirmed(payment.order)
    elif event in {"payment.failed", "payment.cancelled"} and payment.status not in {
        Payment.Status.CAPTURED,
        Payment.Status.FAILED,
    }:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = entity.get("error_description", "Payment failed")[:255]
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        payment.order.status = Order.Status.CANCELLED
        payment.order.save(update_fields=["status", "updated_at"])
        for item in payment.order.items.select_related("product"):
            item.product.stock_quantity += item.quantity
            item.product.save(update_fields=["stock_quantity", "updated_at"])
        from notifications.services import send_payment_failed
        send_payment_failed(payment.order)
    return True
