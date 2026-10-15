from django.shortcuts import render

from catalog.models import Product


def home(request):
    """Render the storefront landing page."""
    return render(
        request,
        "core/home.html",
        {
            "featured_products": Product.objects.filter(
                is_active=True,
                is_featured=True,
                stock_quantity__gt=0,
            )[:6],
            "latest_products": Product.objects.filter(
                is_active=True,
                stock_quantity__gt=0,
            ).order_by("-created_at")[:8],
        },
    )
