from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

from .models import NotificationLog


def send_once(order, event, subject, template_name):
    with transaction.atomic():
        _, created = NotificationLog.objects.get_or_create(
            order=order, event=event, defaults={"user": order.user}
        )
        if not created:
            return False
        context = {"order": order}
        message = EmailMultiAlternatives(
            subject,
            render_to_string(f"emails/{template_name}.txt", context),
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
        )
        message.attach_alternative(render_to_string(f"emails/{template_name}.html", context), "text/html")
        message.send()
        return True


def send_order_confirmed(order):
    return send_once(order, NotificationLog.Event.ORDER_CONFIRMED, f"Order {order.order_number} confirmed", "order_confirmed")


def send_payment_confirmed(order):
    return send_once(order, NotificationLog.Event.PAYMENT_CONFIRMED, f"Payment confirmed for {order.order_number}", "payment_confirmed")


def send_payment_failed(order):
    return send_once(order, NotificationLog.Event.PAYMENT_FAILED, f"Payment update for {order.order_number}", "payment_failed")


def send_fulfillment_update(order, event, subject, template_name):
    return send_once(order, event, subject, template_name)
