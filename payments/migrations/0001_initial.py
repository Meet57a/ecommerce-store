import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("orders", "0002_order_lifecycle"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gateway_order_id", models.CharField(max_length=100, unique=True)),
                ("gateway_payment_id", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("gateway_signature", models.CharField(blank=True, max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("status", models.CharField(choices=[("created", "Created"), ("authorized", "Authorized"), ("captured", "Captured"), ("failed", "Failed"), ("refunded", "Refunded"), ("cancelled", "Cancelled")], default="created", max_length=20)),
                ("failure_reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment", to="orders.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
