from django import forms

from accounts.models import Address


class CheckoutForm(forms.Form):
    use_saved_address = forms.BooleanField(required=False, label="Use my saved shipping address")
    save_address = forms.BooleanField(required=False, label="Save this address for next time")
    address_line_1 = forms.CharField(max_length=255, required=False, label="Address line 1")
    address_line_2 = forms.CharField(max_length=255, required=False, label="Address line 2")
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=100, required=False, initial="India")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_address = Address.objects.filter(user=user).first()
        self.fields["use_saved_address"].initial = bool(self.saved_address)
        if not self.saved_address:
            self.fields["use_saved_address"].disabled = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("use_saved_address"):
            if not self.saved_address:
                raise forms.ValidationError("No saved shipping address is available.")
            return cleaned
        required = ("address_line_1", "city", "state", "postal_code", "country")
        missing = [field.replace("_", " ") for field in required if not cleaned.get(field)]
        if missing:
            raise forms.ValidationError("Please provide: " + ", ".join(missing) + ".")
        return cleaned

    def address_data(self):
        if self.cleaned_data["use_saved_address"]:
            address = self.saved_address
            return {field: getattr(address, field) for field in (
                "address_line_1", "address_line_2", "city", "state", "postal_code", "country"
            )}
        return {field: self.cleaned_data[field] for field in (
            "address_line_1", "address_line_2", "city", "state", "postal_code", "country"
        )}
