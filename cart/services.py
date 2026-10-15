from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from catalog.models import Product

from .models import Cart, CartItem

SESSION_CART_KEY = "cart"


@dataclass(frozen=True)
class CartLine:
    product: Product
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    available: bool
    issue: str = ""


@dataclass(frozen=True)
class CartSummary:
    lines: list[CartLine]
    subtotal: Decimal
    item_count: int

    @property
    def has_invalid_lines(self):
        return any(not line.available for line in self.lines)


def _clean_session_cart(request):
    raw_cart = request.session.get(SESSION_CART_KEY, {})
    cleaned = {}
    if isinstance(raw_cart, dict):
        for product_id, quantity in raw_cart.items():
            try:
                product_id = int(product_id)
                quantity = int(quantity)
            except (TypeError, ValueError):
                continue
            if product_id > 0 and quantity > 0:
                cleaned[str(product_id)] = quantity
    if cleaned != raw_cart:
        request.session[SESSION_CART_KEY] = cleaned
        request.session.modified = True
    return cleaned


def _line_for_product(product, quantity):
    if not product.is_active:
        return CartLine(product, quantity, product.price, product.price * quantity, False, "This product is no longer available.")
    if product.stock_quantity < quantity:
        return CartLine(product, quantity, product.price, product.price * quantity, False, "Only "
                        f"{product.stock_quantity} item(s) remain in stock.")
    return CartLine(product, quantity, product.price, product.price * quantity, True)


def get_cart_summary(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(cart__user=request.user).select_related("product")
        lines = [_line_for_product(item.product, item.quantity) for item in items]
    else:
        session_cart = _clean_session_cart(request)
        products = Product.objects.in_bulk([int(product_id) for product_id in session_cart])
        lines = []
        for product_key, quantity in session_cart.items():
            product = products.get(int(product_key))
            if product:
                lines.append(_line_for_product(product, quantity))
    return CartSummary(
        lines=lines,
        subtotal=sum((line.subtotal for line in lines), Decimal("0.00")),
        item_count=sum(line.quantity for line in lines),
    )


@transaction.atomic
def merge_session_cart(request, user):
    session_cart = _clean_session_cart(request)
    if not session_cart:
        return
    cart, _ = Cart.objects.get_or_create(user=user)
    products = Product.objects.select_for_update().filter(pk__in=[int(key) for key in session_cart])
    for product in products:
        quantity = session_cart.get(str(product.pk), 0)
        if product.is_available:
            item = CartItem.objects.filter(cart=cart, product=product).first()
            if item:
                item.quantity = min(item.quantity + quantity, product.stock_quantity)
                item.save(update_fields=["quantity", "updated_at"])
            else:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=min(quantity, product.stock_quantity),
                )
    request.session.pop(SESSION_CART_KEY, None)
    request.session.modified = True


def add_product(request, product, quantity):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = CartItem.objects.filter(cart=cart, product=product).first()
        if item:
            item.quantity += quantity
            item.save(update_fields=["quantity", "updated_at"])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=quantity)
        return
    session_cart = _clean_session_cart(request)
    key = str(product.pk)
    session_cart[key] = session_cart.get(key, 0) + quantity
    request.session[SESSION_CART_KEY] = session_cart
    request.session.modified = True


def set_product_quantity(request, product, quantity):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            item = CartItem.objects.filter(cart=cart, product=product).first()
            if item:
                item.quantity = quantity
                item.save(update_fields=["quantity", "updated_at"])
        return
    session_cart = _clean_session_cart(request)
    session_cart[str(product.pk)] = quantity
    request.session[SESSION_CART_KEY] = session_cart
    request.session.modified = True


def remove_product(request, product):
    if request.user.is_authenticated:
        CartItem.objects.filter(cart__user=request.user, product=product).delete()
        return
    session_cart = _clean_session_cart(request)
    session_cart.pop(str(product.pk), None)
    request.session[SESSION_CART_KEY] = session_cart
    request.session.modified = True
