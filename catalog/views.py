from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProductFilterForm, ReviewForm
from .models import Product, Review, WishlistItem


def product_list(request):
    products = Product.objects.filter(is_active=True, stock_quantity__gt=0).select_related("category")
    form = ProductFilterForm(request.GET or None)
    if form.is_valid():
        query = form.cleaned_data.get("q")
        category = form.cleaned_data.get("category")
        sort = form.cleaned_data.get("sort")
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
        if category:
            products = products.filter(category=category)
        if sort == "price_low":
            products = products.order_by("price", "name")
        elif sort == "price_high":
            products = products.order_by("-price", "name")
        else:
            products = products.order_by("-created_at")
    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "catalog/product_list.html", {"form": form, "page_obj": page_obj})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )
    if product.stock_quantity <= 0:
        raise Http404("This product is currently out of stock.")
    return render(request, "catalog/product_detail.html", {
        "product": product,
        "reviews": product.reviews.filter(is_approved=True).select_related("user"),
        "review_form": ReviewForm(),
        "in_wishlist": request.user.is_authenticated and WishlistItem.objects.filter(
            user=request.user, product=product
        ).exists(),
    })


@login_required
def wishlist(request):
    return render(request, "catalog/wishlist.html", {
        "items": WishlistItem.objects.filter(user=request.user).select_related("product"),
    })


@login_required
@require_POST
def wishlist_toggle(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
    messages.success(request, "Wishlist updated.")
    return redirect("catalog:product_detail", slug=slug)


@login_required
@require_POST
def review_create(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, "You have already reviewed this product.")
        return redirect("catalog:product_detail", slug=slug)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user, review.product = request.user, product
        review.save()
        messages.success(request, "Your review was added.")
    else:
        messages.error(request, "Please correct the review details.")
    return redirect("catalog:product_detail", slug=slug)
