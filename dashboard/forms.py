from django import forms

from catalog.models import Category, Product
from orders.models import Order


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "slug",
            "description",
            "price",
            "image",
            "category",
            "stock_quantity",
            "is_active",
            "is_featured",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_stock_quantity(self):
        value = self.cleaned_data["stock_quantity"]
        if value < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return value


class OrderFilterForm(forms.Form):
    search = forms.CharField(required=False, label="Customer or order")
    status = forms.ChoiceField(required=False, choices=[("", "All statuses")] + list(Order.Status.choices))
    payment_status = forms.ChoiceField(
        required=False,
        choices=[("", "All payment statuses")] + [
            ("created", "Created"),
            ("authorized", "Authorized"),
            ("captured", "Captured"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
        ],
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
