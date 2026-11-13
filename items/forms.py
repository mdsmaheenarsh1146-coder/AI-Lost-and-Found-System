
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Item

from PIL import Image, UnidentifiedImageError


class RegisterForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="Email Address"
    )

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

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class ItemForm(forms.ModelForm):

  
    phone_number = forms.RegexField(
        regex=r'^\+?[0-9]{10,15}$',
        max_length=16,
        required=True,
        label="Contact Phone Number",
        error_messages={
            "invalid": "Enter a valid phone number with 10 to 15 digits."
        },
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
        
        
  
    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            return image

        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Image size must not exceed 5 MB."
            )

        try:
            img = Image.open(image)

            if img.format not in ["JPEG", "PNG", "WEBP"]:
                raise forms.ValidationError(
                    "Only JPG, PNG, and WEBP images are allowed."
                )

            if img.width * img.height > 25_000_000:
                raise forms.ValidationError(
                    "Image dimensions are too large."
                )

            img.verify()

        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise forms.ValidationError(
                "Please upload a valid image file."
            )

        finally:
            image.seek(0)

        return image



class EditProfileForm(forms.ModelForm):

    email = forms.EmailField(required=True, label="Email Address")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                "This email address is already registered."
            )

        return email
