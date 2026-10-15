from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Category, Product, Review, WishlistItem


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.electronics = Category.objects.create(name="Electronics", slug="electronics")
        cls.books = Category.objects.create(name="Books", slug="books")
        Product.objects.create(
            category=cls.electronics,
            name="Phone",
            slug="phone",
            description="A smart mobile phone",
            price=Decimal("500.00"),
            stock_quantity=4,
        )
        Product.objects.create(
            category=cls.books,
            name="Django Guide",
            slug="django-guide",
            description="Learn Django development",
            price=Decimal("25.00"),
            stock_quantity=3,
        )
        Product.objects.create(
            category=cls.electronics,
            name="Old Stock",
            slug="old-stock",
            description="Unavailable product",
            price=Decimal("10.00"),
            stock_quantity=0,
        )
        Product.objects.create(
            category=cls.electronics,
            name="Hidden Phone",
            slug="hidden-phone",
            description="Inactive product",
            price=Decimal("100.00"),
            stock_quantity=5,
            is_active=False,
        )

    def test_listing_shows_only_active_in_stock_products(self):
        response = self.client.get(reverse("catalog:product_list"))

        self.assertContains(response, "Phone")
        self.assertContains(response, "Django Guide")
        self.assertNotContains(response, "Old Stock")
        self.assertNotContains(response, "Hidden Phone")

    def test_search_matches_name_or_description(self):
        response = self.client.get(reverse("catalog:product_list"), {"q": "Django"})

        self.assertContains(response, "Django Guide")
        self.assertNotContains(response, "Phone")

    def test_category_filter_and_price_sort(self):
        response = self.client.get(
            reverse("catalog:product_list"),
            {"category": self.electronics.pk, "sort": "price_low"},
        )

        products = list(response.context["page_obj"].object_list)
        self.assertEqual([product.name for product in products], ["Phone"])

    def test_inactive_or_out_of_stock_detail_is_not_available(self):
        response = self.client.get(reverse("catalog:product_detail", args=["old-stock"]))

        self.assertEqual(response.status_code, 404)

    def test_wishlist_requires_login_and_is_unique(self):
        product = Product.objects.get(slug="phone")
        response = self.client.post(reverse("catalog:wishlist_toggle", args=[product.slug]))
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.create_user(username="wish", password="pass12345")
        self.client.login(username="wish", password="pass12345")
        self.client.post(reverse("catalog:wishlist_toggle", args=[product.slug]))
        self.client.post(reverse("catalog:wishlist_toggle", args=[product.slug]))
        self.assertFalse(WishlistItem.objects.filter(user=user, product=product).exists())

    def test_review_is_limited_to_one_per_customer(self):
        product = Product.objects.get(slug="phone")
        user = get_user_model().objects.create_user(username="reviewer", password="pass12345")
        self.client.login(username="reviewer", password="pass12345")
        url = reverse("catalog:review_create", args=[product.slug])
        self.client.post(url, {"rating": 5, "title": "Great", "body": "Useful"})
        self.client.post(url, {"rating": 4, "title": "Again", "body": "Duplicate"})
        self.assertEqual(Review.objects.filter(user=user, product=product).count(), 1)
