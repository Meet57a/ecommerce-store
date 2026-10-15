from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Address

User = get_user_model()


class AccountTests(TestCase):
    def test_registration_creates_hashed_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "name": "Asha Patel",
                "email": "asha@example.com",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user = User.objects.get(email="asha@example.com")
        self.assertTrue(user.check_password("Strong-password-123"))
        self.assertNotEqual(user.password, "Strong-password-123")
        self.assertEqual(response.wsgi_request.user, user)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
        )

    def test_profile_updates_user_and_shipping_address(self):
        user = User.objects.create_user(
            username="old@example.com",
            email="old@example.com",
            password="Strong-password-123",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "New Name",
                "email": "new@example.com",
                "address_line_1": "1 Main Street",
                "address_line_2": "",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "postal_code": "380001",
                "country": "India",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(Address.objects.get(user=user).city, "Ahmedabad")
