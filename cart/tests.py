from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product

from .models import Cart, CartItem

User = get_user_model()


class CartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Cart category", slug="cart-category")
        cls.product = Product.objects.create(
            category=category,
            name="Cart product",
            slug="cart-product",
            description="Cart test product",
            price=Decimal("12.50"),
            stock_quantity=5,
        )

    def test_guest_can_add_and_update_session_cart(self):
        response = self.client.post(reverse("cart:add", args=[self.product.slug]), {"quantity": 2})

        self.assertRedirects(response, reverse("cart:detail"))
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, "Cart product")
        self.assertContains(response, "25.00")
        self.client.post(reverse("cart:update", args=[self.product.slug]), {"quantity": 3})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)

    def test_add_rejects_quantity_above_stock(self):
        self.client.post(reverse("cart:add", args=[self.product.slug]), {"quantity": 6})

        self.assertNotIn("cart", self.client.session)

    def test_authenticated_cart_is_persisted_and_guest_cart_merges_on_login(self):
        self.client.post(reverse("cart:add", args=[self.product.slug]), {"quantity": 2})
        user = User.objects.create_user(username="cart@example.com", email="cart@example.com", password="Strong-password-123")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "cart@example.com", "password": "Strong-password-123"},
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(CartItem.objects.get(cart__user=user, product=self.product).quantity, 2)
        self.assertNotIn("cart", self.client.session)

    def test_unavailable_line_prevents_checkout(self):
        self.client.post(reverse("cart:add", args=[self.product.slug]), {"quantity": 2})
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        response = self.client.get(reverse("cart:detail"))

        self.assertContains(response, "Only 1 item(s) remain in stock.")
        self.assertNotContains(response, "Proceed to checkout")
