from django import forms


class CouponCodeForm(forms.Form):
    code = forms.CharField(max_length=40, strip=True, label="Coupon code")
