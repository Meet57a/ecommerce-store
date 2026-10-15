from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Category, Product
from orders.models import Order, OrderItem
from payments.models import Payment

from .services import transition_order

User = get_user_model()


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Dashboard category", slug="dashboard-category")
        cls.product = Product.objects.create(
            category=cls.category,
            name="Dashboard product",
            slug="dashboard-product",
            description="Dashboard product",
            price=Decimal("50.00"),
            stock_quantity=3,
        )
        cls.customer = User.objects.create_user(
            username="customer@example.com",
            email="customer@example.com",
            password="Strong-password-123",
        )
        cls.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="Strong-password-123",
            is_staff=True,
        )
        cls.staff.user_permissions.add(
            Permission.objects.get(codename="view_order"),
            Permission.objects.get(codename="view_product"),
            Permission.objects.get(codename="add_product"),
            Permission.objects.get(codename="change_product"),
        )

    def setUp(self):
        self.client.force_login(self.staff)

    def create_order(self, status=Order.Status.PENDING_PAYMENT, payment_status=Payment.Status.CREATED):
        order = Order.objects.create(
            user=self.customer,
            status=status,
            address_line_1="1 Main Street",
            city="Ahmedabad",
            state="Gujarat",
            postal_code="380001",
            country="India",
            subtotal=Decimal("50.00"),
            shipping_charge=Decimal("99.00"),
            discount=Decimal("0.00"),
            total=Decimal("149.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
            line_total=self.product.price,
        )
        Payment.objects.create(
            order=order,
            user=self.customer,
            gateway_order_id=f"gateway-{order.pk}",
            amount=order.total,
            status=payment_status,
        )
        return order

    def test_customer_cannot_access_dashboard(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_staff_dashboard_uses_captured_payments_for_revenue(self):
        self.create_order(payment_status=Payment.Status.CAPTURED)
        self.create_order(payment_status=Payment.Status.FAILED)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["verified_revenue"], Decimal("149.00"))
        self.assertContains(response, "Low stock")

    def test_staff_can_update_product_stock_and_deactivate(self):
        response = self.client.post(
            reverse("dashboard:product_edit", args=[self.product.pk]),
            {
                "name": self.product.name,
                "slug": self.product.slug,
                "description": self.product.description,
                "price": "75.00",
                "category": self.category.pk,
                "stock_quantity": "1",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("dashboard:product_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)
        self.client.post(reverse("dashboard:product_deactivate", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_unpaid_order_cannot_be_manually_confirmed(self):
        order = self.create_order()

        response = self.client.post(
            reverse("dashboard:order_transition", args=[order.order_number]),
            {"status": Order.Status.CONFIRMED},
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertRedirects(response, reverse("dashboard:order_detail", args=[order.order_number]))

    def test_valid_fulfillment_transition_is_allowed(self):
        order = self.create_order(status=Order.Status.CONFIRMED, payment_status=Payment.Status.CAPTURED)

        transition_order(order, Order.Status.PROCESSING, self.staff)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)

    def test_invalid_transition_is_rejected(self):
        order = self.create_order(status=Order.Status.DELIVERED, payment_status=Payment.Status.CAPTURED)

        with self.assertRaises(ValueError):
            transition_order(order, Order.Status.PROCESSING, self.staff)

    def test_report_counts_only_captured_sales(self):
        self.create_order(payment_status=Payment.Status.CAPTURED)
        self.create_order(payment_status=Payment.Status.CREATED)

        response = self.client.get(reverse("dashboard:report"))

        self.assertEqual(response.context["order_count"], 2)
        self.assertEqual(response.context["verified_sales"], Decimal("149.00"))
