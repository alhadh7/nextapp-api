from django.db import models

# adminapp/models.py
from django.db import models
from django.conf import settings
from django_otp.plugins.otp_totp.models import TOTPDevice

class AdminProfile(models.Model):
    """Profile for admin users with TOTP settings"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile')
    last_login = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Admin: {self.user.full_name}"
    
    @property
    def has_active_totp(self):
        """Check if user has configured TOTP"""
        return TOTPDevice.objects.filter(user=self.user, confirmed=True).exists()