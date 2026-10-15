import json

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from orders.models import Order

from .models import Payment
from .services import process_webhook_event, verify_payment, verify_webhook


@login_required
def checkout(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = get_object_or_404(Payment, order=order, user=request.user)
    if payment.status == Payment.Status.CAPTURED:
        return redirect("orders:detail", order_number=order.order_number)
    return render(
        request,
        "payments/checkout.html",
        {
            "order": order,
            "payment": payment,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        },
    )


@login_required
@require_POST
def verify(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    try:
        verify_payment(
            order,
            request.POST["razorpay_payment_id"],
            request.POST["razorpay_order_id"],
            request.POST["razorpay_signature"],
        )
    except (
        KeyError,
        ValueError,
        Payment.DoesNotExist,
        razorpay.errors.SignatureVerificationError,
    ):
        return JsonResponse({"success": False, "error": "Payment verification failed."}, status=400)
    return JsonResponse({"success": True, "redirect_url": f"/orders/{order.order_number}/"})


@csrf_exempt
@require_POST
def webhook(request):
    try:
        verify_webhook(request.body, request.headers.get("X-Razorpay-Signature", ""))
        payload = json.loads(request.body)
        process_webhook_event(payload)
    except (
        ValueError,
        json.JSONDecodeError,
        razorpay.errors.SignatureVerificationError,
    ):
        return JsonResponse({"error": "Invalid webhook."}, status=400)
    return JsonResponse({"received": True})


@login_required
@require_POST
def failed(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    Payment.objects.filter(order=order, status=Payment.Status.CREATED).update(
        status=Payment.Status.FAILED,
        failure_reason="Customer cancelled or payment failed.",
    )
    from orders.services import cancel_order_and_release_stock

    cancel_order_and_release_stock(order)
    messages.error(request, "Payment was not completed.")
    return redirect("orders:detail", order_number=order.order_number)
