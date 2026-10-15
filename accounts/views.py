from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from cart.services import merge_session_cart

from .forms import AddressForm, EmailAuthenticationForm, ProfileForm, RegistrationForm
from .models import Address


class CustomerLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        merge_session_cart(self.request, self.request.user)
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        merge_session_cart(request, user)
        messages.success(request, "Your account has been created.")
        return redirect("accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    address = Address.objects.filter(user=request.user).first()
    if address is None:
        address = Address(user=request.user)
    profile_form = ProfileForm(request.POST or None, instance=request.user)
    address_form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST":
        if profile_form.is_valid() and address_form.is_valid():
            profile_form.save()
            saved_address = address_form.save(commit=False)
            saved_address.user = request.user
            saved_address.save()
            messages.success(request, "Your profile and shipping address were updated.")
            return redirect("accounts:profile")
    return render(
        request,
        "accounts/profile.html",
        {"profile_form": profile_form, "address_form": address_form},
    )
