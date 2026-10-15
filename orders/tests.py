from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Address
from cart.models import Cart, CartItem
from catalog.models import Category, Product

from .models import Order
from .services import calculate_totals

User = get_user_model()


class CheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Order category", slug="order-category")
        cls.product = Product.objects.create(
            category=category,
            name="Order product",
            slug="order-product",
            description="Order test product",
            price=Decimal("100.00"),
            stock_quantity=4,
        )
        cls.user = User.objects.create_user(
            username="buyer@example.com",
            email="buyer@example.com",
            password="Strong-password-123",
        )

    def setUp(self):
        self.client.force_login(self.user)
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

    def test_checkout_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("orders:checkout"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('orders:checkout')}",
        )

    def test_checkout_totals_use_decimal_server_calculation(self):
        response = self.client.get(reverse("orders:checkout"))

        self.assertEqual(response.context["totals"]["subtotal"], Decimal("200.00"))
        self.assertEqual(response.context["totals"]["shipping_charge"], Decimal("99.00"))
        self.assertEqual(response.context["totals"]["total"], Decimal("299.00"))

    def test_checkout_creates_pending_order_and_decrements_stock(self):
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_line_1": "1 Main Street",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "postal_code": "380001",
                "country": "India",
                "save_address": "on",
            },
        )

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse("orders:confirmation", args=[order.pk]))
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(order.total, Decimal("299.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())
        self.assertTrue(Address.objects.filter(user=self.user, city="Ahmedabad").exists())

    def test_checkout_rejects_insufficient_stock(self):
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_line_1": "1 Main Street",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "postal_code": "380001",
                "country": "India",
            },
        )

        self.assertRedirects(response, reverse("cart:detail"))
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_free_shipping_threshold(self):
        self.product.price = Decimal("1000.00")
        self.product.save(update_fields=["price"])

        cart = type("CartSummary", (), {"subtotal": Decimal("1000.00")})()

        self.assertEqual(calculate_totals(cart)["shipping_charge"], Decimal("0.00"))
