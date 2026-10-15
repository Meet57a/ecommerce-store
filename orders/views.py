from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cart.models import CartItem
from cart.services import get_cart_summary
from catalog.models import Product

from .forms import CheckoutForm
from .models import Order, OrderItem
from .services import calculate_totals
from payments.services import PaymentConfigurationError, create_gateway_order
from coupons.models import Coupon
from coupons.services import CouponError, get_valid_coupon


@login_required
def checkout(request):
    cart = get_cart_summary(request)
    if not cart.lines:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")
    coupon = Coupon.objects.filter(pk=request.session.get("coupon_id")).first()
    try:
        if coupon:
            get_valid_coupon(coupon.code, request.user, cart.subtotal)
    except CouponError:
        request.session.pop("coupon_id", None)
        coupon = None
        messages.info(request, "The applied coupon is no longer valid.")
    totals = calculate_totals(cart, request.user, coupon)
    form = CheckoutForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            cart_items = list(
                CartItem.objects.select_for_update()
                .select_related("product")
                .filter(cart__user=request.user)
            )
            if not cart_items:
                messages.error(request, "Your cart is empty.")
                return redirect("cart:detail")
            product_ids = [item.product_id for item in cart_items]
            locked_products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(pk__in=product_ids)
            }
            for item in cart_items:
                product = locked_products.get(item.product_id)
                if not product or not product.is_available or item.quantity > product.stock_quantity:
                    messages.error(request, "Your cart changed. Review availability before checkout.")
                    return redirect("cart:detail")
            current_subtotal = sum(
                (locked_products[item.product_id].price * item.quantity for item in cart_items),
                start=totals["subtotal"] * 0,
            )
            current_cart = type("CurrentCart", (), {"subtotal": current_subtotal})()
            current_coupon = coupon
            if current_coupon:
                current_coupon = get_valid_coupon(current_coupon.code, request.user, current_subtotal)
            current_totals = calculate_totals(current_cart, request.user, current_coupon)
            address_data = form.address_data()
            order = Order.objects.create(
                user=request.user,
                address_line_1=address_data["address_line_1"],
                address_line_2=address_data["address_line_2"],
                city=address_data["city"],
                state=address_data["state"],
                postal_code=address_data["postal_code"],
                country=address_data["country"],
                coupon=current_coupon,
                **current_totals,
            )
            for item in cart_items:
                product = locked_products[item.product_id]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item.quantity,
                    line_total=product.price * item.quantity,
                )
                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity", "updated_at"])
            CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
            if form.cleaned_data.get("save_address") and not form.cleaned_data.get("use_saved_address"):
                from accounts.models import Address

                Address.objects.update_or_create(user=request.user, defaults=address_data)
            try:
                create_gateway_order(order)
            except PaymentConfigurationError as exc:
                messages.error(request, str(exc))
                return redirect("orders:confirmation", pk=order.pk)
        return redirect("payments:checkout", order_number=order.order_number)
    return render(request, "orders/checkout.html", {"form": form, "cart": cart, "totals": totals})


@login_required
def history(request):
    return render(request, "orders/history.html", {"orders": request.user.orders.all()})


@login_required
def detail(request, order_number):
    order = get_object_or_404(
        request.user.orders.prefetch_related("items", "payment"),
        order_number=order_number,
    )
    return render(request, "orders/detail.html", {"order": order})


@login_required
def confirmation(request, pk):
    order = get_object_or_404(request.user.orders.prefetch_related("items"), pk=pk)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def cancel(request, order_number):
    if request.method != "POST":
        return redirect("orders:detail", order_number=order_number)
    with transaction.atomic():
        order = get_object_or_404(
            request.user.orders.select_for_update().prefetch_related("items"),
            order_number=order_number,
        )
        if not order.can_cancel:
            messages.error(request, "This order can no longer be cancelled.")
            return redirect("orders:detail", order_number=order.order_number)
        for item in order.items.all():
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock_quantity += item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        if hasattr(order, "payment"):
            order.payment.status = "cancelled"
            order.payment.save(update_fields=["status", "updated_at"])
    messages.success(request, "Your order was cancelled.")
    return redirect("orders:detail", order_number=order.order_number)
