from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User
from theaters.models import City


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    preferred_city = forms.ModelChoiceField(queryset=City.objects.filter(is_active=True), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'preferred_city')


class CustomAuthenticationForm(AuthenticationForm):
    pass


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'preferred_city', 'bio')
