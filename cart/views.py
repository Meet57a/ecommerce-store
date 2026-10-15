from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product

from .forms import QuantityForm
from .services import add_product, get_cart_summary, remove_product, set_product_quantity


def detail(request):
    return render(request, "cart/detail.html", {"cart": get_cart_summary(request)})


@require_POST
def add(request, slug):
    product = get_object_or_404(Product, slug=slug)
    form = QuantityForm(request.POST)
    if not product.is_available:
        messages.error(request, "This product is not currently available.")
    elif form.is_valid():
        quantity = form.cleaned_data["quantity"]
        existing = next((line.quantity for line in get_cart_summary(request).lines if line.product.pk == product.pk), 0)
        if existing + quantity > product.stock_quantity:
            messages.error(request, f"Only {product.stock_quantity} item(s) are available.")
        else:
            add_product(request, product, quantity)
            messages.success(request, f"{product.name} was added to your cart.")
    else:
        messages.error(request, "Enter a valid quantity.")
    return redirect(request.POST.get("next") or "cart:detail")


@require_POST
def update(request, slug):
    product = get_object_or_404(Product, slug=slug)
    form = QuantityForm(request.POST)
    if not product.is_available:
        messages.error(request, "This product is no longer available.")
    elif form.is_valid() and form.cleaned_data["quantity"] <= product.stock_quantity:
        set_product_quantity(request, product, form.cleaned_data["quantity"])
        messages.success(request, "Cart updated.")
    else:
        messages.error(request, f"Enter a quantity between 1 and {product.stock_quantity}.")
    return redirect("cart:detail")


@require_POST
def remove(request, slug):
    product = get_object_or_404(Product, slug=slug)
    remove_product(request, product)
    messages.success(request, f"{product.name} was removed from your cart.")
    return redirect("cart:detail")
