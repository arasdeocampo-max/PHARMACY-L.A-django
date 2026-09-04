import re

from django import forms
from django.contrib.auth.models import User
from .models import Product, Batch, UserProfile

CTRL = {"class": "form-control"}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{3,29}$")


def is_valid_username(username):
    return bool(USERNAME_PATTERN.fullmatch(username))


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "barcode",
            "category",
            "kind",
            "type",
            "price",
            "reorder_level",
            "shelf",
            "supplier",
            "image_url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = [
            "product",
            "batch_number",
            "expiry",
            "quantity",
            "supplier_name",
            "shelf",
            "received_date",
        ]
        widgets = {
            "expiry": forms.DateInput(attrs={"type": "date", **CTRL}),
            "received_date": forms.DateInput(attrs={"type": "date", **CTRL}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if name not in ("expiry", "received_date"):
                f.widget.attrs.setdefault("class", "form-control")


class DisposeForm(forms.Form):
    qty = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={**CTRL, "placeholder": "Quantity to dispose"}),
    )
    reason = forms.CharField(
        widget=forms.TextInput(
            attrs={**CTRL, "placeholder": "e.g. Expired per batch record"}
        )
    )
    authorized_by = forms.CharField(
        widget=forms.TextInput(
            attrs={**CTRL, "placeholder": "Pharmacist or Admin name"}
        )
    )


class AddUserForm(forms.Form):
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={**CTRL, "placeholder": "e.g. Maria Santos"})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={**CTRL, "placeholder": "Login username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**CTRL, "placeholder": "Temporary password"})
    )
    role = forms.ChoiceField(
        choices=[
            ("admin", "Admin"),
            ("pharmacist", "Pharmacist"),
            ("staff", "Counter Staff"),
        ],
        widget=forms.Select(attrs=CTRL),
    )

    def clean_username(self):
        u = self.cleaned_data["username"]
        if not is_valid_username(u):
            raise forms.ValidationError(
                "Use 4-30 letters or numbers; . _ - are allowed. Do not use an email or emoji."
            )
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Username already taken.")
        return u

    def save(self):
        d = self.cleaned_data
        parts = d["full_name"].strip().split(" ", 1)
        user = User.objects.create_user(
            username=d["username"],
            password=d["password"],
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
        )
        UserProfile.objects.create(user=user, role=d["role"])
        return user
