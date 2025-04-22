# adminapp/forms.py
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminLoginForm(forms.Form):
    """Form for admin login"""
    phone_number = forms.CharField(max_length=15)
    password = forms.CharField(widget=forms.PasswordInput)
    
class TOTPVerificationForm(forms.Form):
    """Form for TOTP verification"""
    totp_token = forms.CharField(
        max_length=6, 
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit code'})
    )