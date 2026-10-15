from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    class Event(models.TextChoices):
        ORDER_CONFIRMED = "order_confirmed", "Order confirmed"
        PAYMENT_CONFIRMED = "payment_confirmed", "Payment confirmed"
        PAYMENT_FAILED = "payment_failed", "Payment failed"
        ORDER_SHIPPED = "order_shipped", "Order shipped"
        ORDER_DELIVERED = "order_delivered", "Order delivered"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="notification_logs")
    event = models.CharField(max_length=30, choices=Event.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "event"], name="unique_order_notification"),
        ]
