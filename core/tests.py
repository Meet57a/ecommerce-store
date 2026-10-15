from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_home_page_contains_storefront_content(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Find products you will love.")
        self.assertNotContains(response, "Django foundation ready")
        self.assertNotContains(response, "Coming next")
