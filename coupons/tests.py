from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Coupon
from .services import CouponError, discount_for, get_valid_coupon


class CouponTests(TestCase):
    def test_percentage_discount_is_capped_at_subtotal(self):
        coupon = Coupon(discount_type=Coupon.DiscountType.PERCENTAGE, discount_value=100)
        self.assertEqual(discount_for(coupon, Decimal("50.00")), Decimal("50.00"))

    def test_expired_coupon_is_rejected(self):
        user = get_user_model().objects.create_user(username="coupon", password="pass12345")
        coupon = Coupon.objects.create(
            code="OLD", discount_type=Coupon.DiscountType.FIXED, discount_value=10,
            starts_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )
        with self.assertRaises(CouponError):
            get_valid_coupon(coupon.code, user, Decimal("100.00"))
