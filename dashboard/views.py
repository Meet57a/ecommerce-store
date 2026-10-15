from datetime import datetime, time
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.models import Category, Product
from orders.models import Order, OrderItem
from payments.models import Payment

from .forms import OrderFilterForm, ProductAdminForm, ReportFilterForm
from .services import VALID_TRANSITIONS, log_admin_action, transition_order


def staff_required(view):
    return user_passes_test(
        lambda user: user.is_active and user.is_staff and user.has_perm("orders.view_order"),
        login_url="accounts:login",
    )(view)


def _date_bounds(form):
    start = end = None
    if form.is_valid():
        if form.cleaned_data.get("date_from"):
            start = timezone.make_aware(datetime.combine(form.cleaned_data["date_from"], time.min))
        if form.cleaned_data.get("date_to"):
            end = timezone.make_aware(datetime.combine(form.cleaned_data["date_to"], time.max))
    return start, end


@staff_required
def index(request):
    paid = Payment.Status.CAPTURED
    revenue = Payment.objects.filter(status=paid).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
    context = {
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status=Order.Status.PENDING_PAYMENT).count(),
        "total_customers": get_user_model().objects.filter(is_staff=False).count(),
        "total_products": Product.objects.count(),
        "low_stock_products": Product.objects.filter(stock_quantity__lte=5, is_active=True).count(),
        "verified_revenue": revenue,
        "recent_orders": Order.objects.select_related("user").all()[:8],
        "recent_payments": Payment.objects.select_related("order", "user").all()[:8],
    }
    return render(request, "dashboard/index.html", context)


@staff_required
def product_list(request):
    if not request.user.has_perm("catalog.view_product"):
        return _forbidden()
    products = Product.objects.select_related("category").all()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "-created_at")
    if query:
        products = products.filter(name__icontains=query)
    if category:
        products = products.filter(category_id=category)
    if sort in {"name", "-price", "price", "-stock_quantity", "stock_quantity", "-created_at"}:
        products = products.order_by(sort)
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(request, "dashboard/product_list.html", {"page_obj": page_obj, "categories": Category.objects.all()})


@staff_required
def product_create(request):
    if not request.user.has_perm("catalog.add_product"):
        return _forbidden()
    form = ProductAdminForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        product = form.save()
        log_admin_action(request.user, product, "Product created.")
        messages.success(request, "Product created.")
        return redirect("dashboard:product_list")
    return render(request, "dashboard/product_form.html", {"form": form, "title": "Add product"})


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if not request.user.has_perm("catalog.change_product"):
        return _forbidden()
    form = ProductAdminForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        product = form.save()
        log_admin_action(request.user, product, "Product updated.")
        messages.success(request, "Product updated.")
        return redirect("dashboard:product_list")
    return render(request, "dashboard/product_form.html", {"form": form, "title": "Edit product", "product": product})


@staff_required
def product_deactivate(request, pk):
    if not request.user.has_perm("catalog.change_product"):
        return _forbidden()
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        log_admin_action(request.user, product, "Product deactivated.")
        messages.success(request, "Product deactivated.")
    return redirect("dashboard:product_list")


@staff_required
def order_list(request):
    form = OrderFilterForm(request.GET or None)
    orders = Order.objects.select_related("user").prefetch_related("payment").all()
    if form.is_valid():
        search = form.cleaned_data.get("search")
        if search:
            orders = orders.filter(user__email__icontains=search) | orders.filter(order_number__icontains=search)
        if form.cleaned_data.get("status"):
            orders = orders.filter(status=form.cleaned_data["status"])
        if form.cleaned_data.get("payment_status"):
            orders = orders.filter(payment__status=form.cleaned_data["payment_status"])
        start, end = _date_bounds(form)
        if start:
            orders = orders.filter(created_at__gte=start)
        if end:
            orders = orders.filter(created_at__lte=end)
    page_obj = Paginator(orders.distinct(), 15).get_page(request.GET.get("page"))
    return render(request, "dashboard/order_list.html", {"form": form, "page_obj": page_obj})


@staff_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.select_related("user", "payment").prefetch_related("items"), order_number=order_number)
    return render(request, "dashboard/order_detail.html", {"order": order, "transitions": [
        (status.value, status.label) for status in Order.Status if status.value in {
            target.value for target in VALID_TRANSITIONS.get(order.status, set())
        }
    ]})


@staff_required
def order_transition(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status == Order.Status.CONFIRMED:
            messages.error(request, "Orders can only be confirmed by verified payment evidence.")
        else:
            try:
                transition_order(order, new_status, request.user)
                messages.success(request, "Order status updated.")
            except (ValueError, KeyError):
                messages.error(request, "That order status transition is not allowed.")
    return redirect("dashboard:order_detail", order_number=order.order_number)


@staff_required
def report(request):
    form = ReportFilterForm(request.GET or None)
    orders = Order.objects.all()
    start, end = _date_bounds(form)
    if start:
        orders = orders.filter(created_at__gte=start)
    if end:
        orders = orders.filter(created_at__lte=end)
    paid_orders = orders.filter(payment__status=Payment.Status.CAPTURED)
    top_products = OrderItem.objects.filter(order__in=paid_orders).values("product_name").annotate(
        units=Sum("quantity"),
        revenue=Sum("line_total"),
    ).order_by("-units")[:10]
    return render(request, "dashboard/report.html", {
        "form": form,
        "order_count": orders.count(),
        "verified_sales": paid_orders.aggregate(total=Coalesce(Sum("total"), Decimal("0.00")))["total"],
        "top_products": top_products,
    })


def _forbidden():
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied
