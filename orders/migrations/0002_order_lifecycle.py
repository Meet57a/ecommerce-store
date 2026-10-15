import uuid

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def populate_order_numbers(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.filter(order_number__isnull=True):
        order.order_number = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        order.save(update_fields=["order_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_number",
            field=models.CharField(editable=False, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.RunPython(populate_order_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_number",
            field=models.CharField(editable=False, max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending payment"),
                    ("confirmed", "Confirmed"),
                    ("processing", "Processing"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.RenameField(
            model_name="orderitem",
            old_name="subtotal",
            new_name="line_total",
        ),
    ]
