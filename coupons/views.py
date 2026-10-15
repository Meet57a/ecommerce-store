from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from cart.services import get_cart_summary

from .forms import CouponCodeForm
from .services import CouponError, get_valid_coupon


@login_required
@require_POST
def apply(request):
    form = CouponCodeForm(request.POST)
    if form.is_valid():
        try:
            coupon = get_valid_coupon(form.cleaned_data["code"], request.user, get_cart_summary(request).subtotal)
            request.session["coupon_id"] = coupon.pk
            request.session["coupon_code"] = coupon.code
            request.session.modified = True
            messages.success(request, f"Coupon {coupon.code} applied.")
        except CouponError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Enter a valid coupon code.")
    return redirect("orders:checkout")


@login_required
@require_POST
def remove(request):
    request.session.pop("coupon_id", None)
    request.session.pop("coupon_code", None)
    request.session.modified = True
    messages.success(request, "Coupon removed.")
    return redirect("orders:checkout")
