from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from orders.models import Order


VALID_TRANSITIONS = {
    Order.Status.PENDING_PAYMENT: {Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.PROCESSING, Order.Status.CANCELLED},
    Order.Status.PROCESSING: {Order.Status.SHIPPED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


def log_admin_action(user, obj, message, action_flag=CHANGE):
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=message,
    )


@transaction.atomic
def transition_order(order, new_status, actor):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if new_status not in VALID_TRANSITIONS.get(order.status, set()):
        raise ValueError(f"Cannot change an order from {order.get_status_display()} to {order.Status(new_status).label}.")
    if new_status == Order.Status.CANCELLED:
        from orders.services import cancel_order_and_release_stock

        order = cancel_order_and_release_stock(order)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    if new_status == Order.Status.SHIPPED:
        from notifications.models import NotificationLog
        from notifications.services import send_fulfillment_update
        send_fulfillment_update(order, NotificationLog.Event.ORDER_SHIPPED, f"Order {order.order_number} shipped", "order_shipped")
    elif new_status == Order.Status.DELIVERED:
        from notifications.models import NotificationLog
        from notifications.services import send_fulfillment_update
        send_fulfillment_update(order, NotificationLog.Event.ORDER_DELIVERED, f"Order {order.order_number} delivered", "order_delivered")
    log_admin_action(actor, order, f"Status changed to {order.get_status_display()}.")
    return order
