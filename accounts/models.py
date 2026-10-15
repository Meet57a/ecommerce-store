from django.conf import settings
from django.db import models
from django.core.validators import MinLengthValidator


class Address(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shipping_address",
    )
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, validators=[MinLengthValidator(3)])
    country = models.CharField(max_length=100, default="India")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} - {self.city}"
