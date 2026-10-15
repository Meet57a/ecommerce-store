from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from .models import Address

User = get_user_model()


class RegistrationForm(UserCreationForm):
    name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField(label="Email address")

    class Meta:
        model = User
        fields = ("name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["name"].strip()
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email address")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "email")
        labels = {"first_name": "Full name"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ("user",)
        widgets = {
            "address_line_1": forms.TextInput(attrs={"placeholder": "Street address"}),
            "address_line_2": forms.TextInput(attrs={"placeholder": "Apartment, suite, etc. (optional)"}),
        }
