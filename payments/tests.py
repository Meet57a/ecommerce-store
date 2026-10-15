import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from orders.models import Order
from orders.services import calculate_totals

from .models import Payment
from .services import process_webhook_event, verify_payment, verify_webhook

User = get_user_model()


class PaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Payment category", slug="payment-category")
        cls.product = Product.objects.create(
            category=category,
            name="Payment product",
            slug="payment-product",
            description="Payment test product",
            price=Decimal("100.00"),
            stock_quantity=2,
        )
        cls.user = User.objects.create_user(
            username="payment@example.com",
            email="payment@example.com",
            password="Strong-password-123",
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.order = Order.objects.create(
            user=self.user,
            address_line_1="1 Main Street",
            city="Ahmedabad",
            state="Gujarat",
            postal_code="380001",
            country="India",
            subtotal=Decimal("100.00"),
            shipping_charge=Decimal("99.00"),
            discount=Decimal("0.00"),
            total=Decimal("199.00"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            gateway_order_id="order_test_123",
            amount=self.order.total,
        )

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("payments.services.get_razorpay_client")
    def test_valid_signature_confirms_order_once(self, get_client):
        client = Mock()
        client.payment.fetch.return_value = {
            "order_id": "order_test_123",
            "amount": 19900,
            "currency": "INR",
            "status": "captured",
        }
        get_client.return_value = client

        verify_payment(self.order, "pay_123", "order_test_123", "valid_signature")

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.CAPTURED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        client.utility.verify_payment_signature.assert_called_once()
        verify_payment(self.order, "pay_123", "order_test_123", "valid_signature")
        self.assertEqual(Payment.objects.get(pk=self.payment.pk).status, Payment.Status.CAPTURED)
        client.utility.verify_payment_signature.assert_called_once()

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("payments.services.get_razorpay_client")
    def test_invalid_signature_does_not_confirm_order(self, get_client):
        import razorpay

        client = Mock()
        client.utility.verify_payment_signature.side_effect = razorpay.errors.SignatureVerificationError("invalid")
        get_client.return_value = client

        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            verify_payment(self.order, "pay_bad", "order_test_123", "bad")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("payments.services.get_razorpay_client")
    def test_mismatched_gateway_order_is_rejected(self, get_client):
        with self.assertRaises(ValueError):
            verify_payment(self.order, "pay_123", "order_other", "signature")
        get_client.assert_not_called()

    @override_settings(RAZORPAY_WEBHOOK_SECRET="webhook_secret")
    @patch("payments.services.get_razorpay_client")
    def test_webhook_signature_uses_raw_body(self, get_client):
        client = Mock()
        get_client.return_value = client
        raw_body = b'{"event":"payment.captured"}'

        verify_webhook(raw_body, "signature")

        client.utility.verify_webhook_signature.assert_called_once_with(
            raw_body,
            "signature",
            "webhook_secret",
        )

    def test_duplicate_captured_webhooks_are_idempotent(self):
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "pay_webhook",
                "order_id": self.payment.gateway_order_id,
                "amount": 19900,
            }}},
        }

        self.assertTrue(process_webhook_event(payload))
        self.assertTrue(process_webhook_event(payload))
        self.assertEqual(Payment.objects.get(pk=self.payment.pk).status, Payment.Status.CAPTURED)
        self.assertEqual(Order.objects.get(pk=self.order.pk).status, Order.Status.CONFIRMED)

    def test_webhook_amount_mismatch_does_not_confirm(self):
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "pay_wrong_amount",
                "order_id": self.payment.gateway_order_id,
                "amount": 1,
            }}},
        }

        self.assertFalse(process_webhook_event(payload))
        self.assertEqual(Payment.objects.get(pk=self.payment.pk).status, Payment.Status.CREATED)

    def test_only_owner_can_access_payment_checkout(self):
        other = User.objects.create_user(username="other@example.com", email="other@example.com", password="Strong-password-123")
        self.client.force_login(other)

        response = self.client.get(reverse("payments:checkout", args=[self.order.order_number]))

        self.assertEqual(response.status_code, 404)
