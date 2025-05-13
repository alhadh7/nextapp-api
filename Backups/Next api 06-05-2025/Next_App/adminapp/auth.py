# adminapp/auth.py
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
import pyotp

User = get_user_model()

class AdminTOTPBackend(ModelBackend):
    """
    Custom authentication backend for Admin users with TOTP
    """
    def authenticate(self, request, username=None, password=None, totp_token=None, **kwargs):
        try:
            # Try to find the user by phone number (which is the USERNAME_FIELD)
            user = User.objects.get(phone_number=username)
            
            # Check if user is a superuser
            if not user.is_superuser:
                return None
            
            # First verify password if provided
            if password is not None and not self.check_password(password, user.password):
                return None
                
            # If we have a TOTP token, verify it
            if totp_token:
                # Get confirmed devices only
                devices = devices_for_user(user, confirmed=True)
                for device in devices:
                    if device.verify_token(totp_token):
                        # Clear the TOTP verification requirement
                        if request and 'needs_totp' in request.session:
                            del request.session['needs_totp']
                        return user
                
                # TOTP verification failed
                return None
            elif password:
                # Only password was provided
                # Set session flag for TOTP verification requirement
                if request and hasattr(request, 'session'):
                    request.session['needs_totp'] = True
                return user
            
            # Neither password nor TOTP provided
            return None
            
        except User.DoesNotExist:
            return None

# adminapp/auth.py (updated functions)

def setup_totp_device(user):
    """Create or get a TOTP device for a user"""
    # 🛑 Don't delete unconfirmed device — just reuse it
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device:
        return device

    existing_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if existing_device:
        return existing_device

    # ✅ Only create a new one if none exist
    device = TOTPDevice(
        user=user,
        name=f'Admin TOTP for {user.full_name}',
        confirmed=False
    )
    device.key = pyotp.random_hex()
    device.save()

    return device


def get_totp_uri(device):
    """Get the URI for TOTP device setup (for QR code)"""
    import base64
    import binascii

    # Convert the device.key (hex string) to binary, then to base32
    key_bytes = binascii.unhexlify(device.key.encode())
    base32_key = base64.b32encode(key_bytes).decode('utf-8').rstrip('=')

    totp = pyotp.TOTP(base32_key)
    return totp.provisioning_uri(
        name=device.user.email or device.user.phone_number,
        issuer_name="HealthConnect Admin"
    )
