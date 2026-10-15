from django import forms

from .models import Category, Review


class ProductFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All categories",
    )


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "title", "body")
        widgets = {"rating": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)])}
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ("newest", "Newest"),
            ("price_low", "Price: low to high"),
            ("price_high", "Price: high to low"),
        ),
    )
