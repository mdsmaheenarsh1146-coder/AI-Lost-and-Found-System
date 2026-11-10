from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

from .models import Item


class ItemForm(forms.ModelForm):
    
    phone_number = forms.CharField(
    max_length=20,
    required=True,
    label="Contact Phone Number",
    widget=forms.TextInput(attrs={
        "placeholder": "Enter your phone number"
    })
)

    class Meta:

        model = Item
        fields = [
            "item_name",
            "description",
            "image",
            "item_type",
            "location",
            "phone_number",
            "date",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }