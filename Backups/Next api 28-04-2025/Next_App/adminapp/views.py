# adminapp/views/auth_views.py
import binascii
from django.conf import settings
import pyotp
import qrcode
from io import BytesIO
import base64



from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .forms import AdminLoginForm, TOTPVerificationForm
from .auth import setup_totp_device, get_totp_uri
from .models import AdminProfile

User = get_user_model()

from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import AdminLoginForm
from .models import AdminProfile  # adjust import as needed

# def login_view(request):
#     """Admin login view with TOTP handling"""
#     if request.method == 'POST':
#         form = AdminLoginForm(request.POST)
#         if form.is_valid():
#             phone_number = form.cleaned_data['phone_number']
#             password = form.cleaned_data['password']

#             user = authenticate(
#                 request=request,
#                 username=phone_number,
#                 password=password
#             )

#             if user is not None:
#                 if not user.is_superuser:
#                     messages.error(request, "Access denied. Only superusers can access the admin panel.")
#                     return redirect('adminapp:login')

#                 # Ensure admin profile exists
#                 profile, _ = AdminProfile.objects.get_or_create(user=user)

#                 # Check if a confirmed TOTP device exists
#                 has_totp_device = TOTPDevice.objects.filter(user=user, confirmed=True).exists()

#                 if not has_totp_device:
#                     # Store user ID in session for TOTP setup
#                     request.session['admin_setup_id'] = user.id
#                     messages.info(request, "Please set up two-factor authentication.")
#                     return redirect('adminapp:totp_setup')

#                 # TOTP is set up, proceed to verification
#                 request.session['admin_user_id'] = user.id
#                 request.session['needs_totp'] = True
#                 return redirect('adminapp:totp_verify')

#             else:
#                 messages.error(request, "Invalid phone number or password.")
#     else:
#         form = AdminLoginForm()

#     return render(request, 'adminapp/login.html', {'form': form})



# temporary protection against bruteforce

def login_view(request):
    """Admin login view with TOTP handling and improved security"""
    # Limit failed attempts
    if request.session.get('login_attempts', 0) >= 5:
        if request.session.get('lockout_until') and timezone.now() < timezone.datetime.fromisoformat(request.session.get('lockout_until')):
            messages.error(request, "Too many failed attempts. Please try again later.")
            return render(request, 'adminapp/login.html', {'form': AdminLoginForm(), 'locked': True})
        else:
            # Reset counter after lockout period
            request.session['login_attempts'] = 0
            request.session.pop('lockout_until', None)
    
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']

            user = authenticate(
                request=request,
                username=phone_number,
                password=password
            )

            if user is not None:
                if not user.is_superuser:
                    messages.error(request, "Access denied. Only superusers can access the admin panel.")
                    # Don't increment attempt counter for correct credentials but wrong permissions
                    return redirect('adminapp:login')

                # Clear failed login attempts on successful authentication
                if 'login_attempts' in request.session:
                    del request.session['login_attempts']
                if 'lockout_until' in request.session:
                    del request.session['lockout_until']
                
                # Regenerate session ID to prevent session fixation
                request.session.cycle_key()

                # Ensure admin profile exists
                profile, _ = AdminProfile.objects.get_or_create(user=user)

                # Check if a confirmed TOTP device exists
                has_totp_device = TOTPDevice.objects.filter(user=user, confirmed=True).exists()

                if not has_totp_device:
                    # Store user ID in session for TOTP setup
                    request.session['admin_setup_id'] = user.id
                    # Set a short expiry on this session state
                    request.session.set_expiry(300)  # 5 minutes to complete setup
                    messages.info(request, "Please set up two-factor authentication.")
                    return redirect('adminapp:totp_setup')

                # TOTP is set up, proceed to verification
                request.session['admin_user_id'] = user.id
                request.session['needs_totp'] = True
                # Set a short expiry on this intermediate authentication state
                request.session.set_expiry(300)  # 5 minutes to enter TOTP code
                return redirect('adminapp:totp_verify')

            else:
                # Increment failed login attempts
                request.session['login_attempts'] = request.session.get('login_attempts', 0) + 1
                
                # Apply lockout after 5 failed attempts
                if request.session.get('login_attempts', 0) >= 5:
                    lockout_until = timezone.now() + timezone.timedelta(minutes=1)
                    request.session['lockout_until'] = lockout_until.isoformat()
                    messages.error(request, "Too many failed attempts. Please try again after 15 minutes.")
                else:
                    messages.error(request, "Invalid phone number or password.")
        else:
            # Increment attempt counter for invalid form submissions too
            request.session['login_attempts'] = request.session.get('login_attempts', 0) + 1
            messages.error(request, "Invalid form submission.")
    else:
        form = AdminLoginForm()

    return render(request, 'adminapp/login.html', {'form': form})

from django_otp import devices_for_user

# def totp_verify_view(request):
#     """TOTP verification view"""
#     if 'admin_user_id' not in request.session:
#         messages.error(request, "Please login first.")
#         return redirect('adminapp:login')
    
#     try:
#         user = User.objects.get(id=request.session['admin_user_id'], is_superuser=True)
#     except User.DoesNotExist:
#         messages.error(request, "Invalid session. Please login again.")
#         return redirect('adminapp:login')

#     # Ensure a confirmed TOTP device exists
#     from django_otp.plugins.otp_totp.models import TOTPDevice
#     if not TOTPDevice.objects.filter(user=user, confirmed=True).exists():
#         messages.info(request, "Two-factor setup required.")
#         return redirect('adminapp:totp_setup')

#     if request.method == 'POST':
#         form = TOTPVerificationForm(request.POST)
#         if form.is_valid():
#             totp_token = form.cleaned_data['totp_token']
            
#             # Manually verify against confirmed devices
#             devices = devices_for_user(user, confirmed=True)
#             for device in devices:
#                 if device.verify_token(totp_token):
#                     login(request, user)

#                     # Update last login time
#                     profile, _ = AdminProfile.objects.get_or_create(user=user)
#                     profile.last_login = timezone.now()
#                     profile.save()

#                     request.session.pop('admin_user_id', None)
#                     request.session.pop('needs_totp', None)

#                     messages.success(request, f"Welcome, {user.full_name}!")
#                     return redirect('adminapp:dashboard')

#             messages.error(request, "Invalid TOTP code. Please try again.")
#     else:
#         form = TOTPVerificationForm()

#     return render(request, 'adminapp/totp_verify.html', {'form': form})

# temporary protection against bruteforce


def totp_verify_view(request):
    """TOTP verification view with improved security"""
    # Check if session contains required authentication data
    if 'admin_user_id' not in request.session:
        messages.error(request, "Please login first.")
        return redirect('adminapp:login')
    
    # Check for session expiration (if your session middleware doesn't handle this)
    if request.session.get_expiry_age() <= 0:
        messages.error(request, "Your session has expired. Please login again.")
        return redirect('adminapp:login')
    
    # Limit TOTP verification attempts
    if request.session.get('totp_attempts', 0) >= 3:
        # Clear the session and force re-authentication
        request.session.flush()
        messages.error(request, "Too many failed verification attempts. Please login again.")
        return redirect('adminapp:login')
    
    try:
        user = User.objects.get(id=request.session['admin_user_id'], is_superuser=True)
    except User.DoesNotExist:
        # Clear the invalid session
        request.session.flush()
        messages.error(request, "Invalid session. Please login again.")
        return redirect('adminapp:login')

    # Ensure a confirmed TOTP device exists
    from django_otp.plugins.otp_totp.models import TOTPDevice
    if not TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        messages.info(request, "Two-factor setup required.")
        # Clear the intermediate auth state
        request.session.pop('admin_user_id', None)
        request.session.pop('needs_totp', None)
        return redirect('adminapp:totp_setup')

    if request.method == 'POST':
        form = TOTPVerificationForm(request.POST)
        if form.is_valid():
            totp_token = form.cleaned_data['totp_token']
            
            # Increment attempt counter before verification
            request.session['totp_attempts'] = request.session.get('totp_attempts', 0) + 1
            
            # Verify with time-based restrictions to prevent replay attacks
            devices = devices_for_user(user, confirmed=True)
            verification_successful = False
            
            for device in devices:
                if device.verify_token(totp_token):
                    # Regenerate session ID for security
                    request.session.cycle_key()
                    
                    # Complete login process
                    login(request, user)

                    # Update last login time
                    profile, _ = AdminProfile.objects.get_or_create(user=user)
                    profile.last_login = timezone.now()
                    profile.save()

                    # Clear intermediate authentication data
                    request.session.pop('admin_user_id', None)
                    request.session.pop('needs_totp', None)
                    request.session.pop('totp_attempts', None)
                    
                    # Set appropriate session timeout for admin sessions
                    request.session.set_expiry(3600)  # 1 hour timeout for admin sessions
                    
                    messages.success(request, f"Welcome, {user.full_name}!")
                    verification_successful = True
                    
                    # Log successful admin login
                    logger.info(f"Admin login successful for user {user.id}")
                    
                    return redirect('adminapp:dashboard')

            if not verification_successful:
                messages.error(request, "Invalid TOTP code. Please try again.")
                # Log failed verification attempt
                logger.warning(f"Failed TOTP verification attempt for user {user.id}")
    else:
        form = TOTPVerificationForm()

    return render(request, 'adminapp/totp_verify.html', {
        'form': form, 
        'attempts_remaining': 3 - request.session.get('totp_attempts', 0)
    })

import base64
import binascii
from io import BytesIO

import pyotp
import qrcode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import TOTPVerificationForm
from .auth import setup_totp_device, get_totp_uri
from .models import AdminProfile
from django.contrib.auth import get_user_model

import logging
logger = logging.getLogger(__name__)

User = get_user_model()

def totp_setup_view(request):
    """Setup TOTP for admin user"""
    if 'admin_setup_id' not in request.session:
        messages.error(request, "Please login first.")
        return redirect('adminapp:login')

    try:
        user = User.objects.get(id=request.session['admin_setup_id'], is_superuser=True)
    except User.DoesNotExist:
        messages.error(request, "Invalid session. Please login again.")
        return redirect('adminapp:login')

    # Setup TOTP device
    device = setup_totp_device(user)
    device.refresh_from_db()

    print(f"[DEBUG] Device key (hex): {device.key}")

    # Convert hex to base32
    key_bytes = binascii.unhexlify(device.key.encode())
    base32_key = base64.b32encode(key_bytes).decode('utf-8').rstrip('=')
    totp = pyotp.TOTP(base32_key)

    # Create QR code
    totp_uri = totp.provisioning_uri(
        name=user.email or user.phone_number,
        issuer_name="HealthConnect Admin"
    )

    if request.method == 'POST':
        form = TOTPVerificationForm(request.POST)
        if form.is_valid():
            totp_token = form.cleaned_data['totp_token']

            # print(f"[DEBUG] Submitted OTP: {totp_token}")
            # print(f"[DEBUG] Expected OTP: {totp.now()}")

            if totp.verify(totp_token, valid_window=1):  # allow slight time drift
                device.confirmed = True
                device.save()

                login(request, user)
                profile, _ = AdminProfile.objects.get_or_create(user=user)
                profile.last_login = timezone.now()
                profile.save()

                request.session.pop('admin_user_id', None)
                request.session.pop('needs_totp', None)

                messages.success(request, "Two-factor authentication set up successfully!")
                return redirect('adminapp:dashboard')
            else:
                messages.error(request, "Invalid verification code. Please try again.")
    else:
        form = TOTPVerificationForm()

    # QR code generation
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer)
    qr_code_image = base64.b64encode(buffer.getvalue()).decode()

    # Show current OTP in debug mode
    # current_otp = totp.now() if settings.DEBUG else None

    context = {
        'qr_code_image': qr_code_image,
        'secret_key': base32_key,
        'form': form,
        # 'current_otp': current_otp,
    }

    return render(request, 'adminapp/totp_setup.html', context)


@login_required
def logout_view(request):
    """Logout admin user"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('adminapp:login')




# adminapp/views/dashboard_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from authentication.models import CustomUser, Partner
from authentication.models import ServiceType, Booking, BookingRequest, Review

User = get_user_model()

def admin_required(view_func):
    """Decorator to ensure user is a superuser"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('adminapp:login')
        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def dashboard(request):
    """Main admin dashboard view"""
    # Get counts for dashboard widgets
    user_count = CustomUser.objects.count()
    partner_count = Partner.objects.count()
    booking_count = Booking.objects.count()
    service_count = ServiceType.objects.count()
    
    # Get latest bookings
    latest_bookings = Booking.objects.all().order_by('-created_at')[:5]
    
    context = {
        'user_count': user_count,
        'partner_count': partner_count,
        'booking_count': booking_count,
        'service_count': service_count,
        'latest_bookings': latest_bookings,
    }
    
    return render(request, 'adminapp/dashboard.html', context)

# @admin_required
# def user_list(request):
#     """List all users"""
#     users = CustomUser.objects.filter(is_partner=False, is_superuser=False).order_by('-id')
    
#     # Set up pagination
#     paginator = Paginator(users, 20)  # 20 users per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     return render(request, 'adminapp/user_list.html', {'page_obj': page_obj})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from authentication.models import CustomUser
from .forms import UserUpdateForm  # Create this form to handle user modification

@admin_required
def user_list(request):
    """List all users with options to delete and modify."""
    users = CustomUser.objects.filter(is_partner=False, is_superuser=False).order_by('-id')
    
    # Handle delete user
    if request.method == 'POST' and 'delete_user' in request.POST:
        user_id = request.POST.get('user_id')
        user_to_delete = get_object_or_404(CustomUser, id=user_id)
        user_to_delete.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('adminapp:user_list')
    
    # Handle update user
    if request.method == 'POST' and 'update_user' in request.POST:
        user_id = request.POST.get('user_id')
        user_to_update = get_object_or_404(CustomUser, id=user_id)
        form = UserUpdateForm(request.POST, instance=user_to_update)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect('adminapp:user_list')

    # Set up pagination
    paginator = Paginator(users, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'adminapp/user_list.html', {'page_obj': page_obj})



# @admin_required
# def partner_list(request):
#     """List all partners"""
#     partners = Partner.objects.all().order_by('-id')


    
#     # Set up pagination
#     paginator = Paginator(partners, 20)  # 20 partners per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     return render(request, 'adminapp/partner_list.html', {'page_obj': page_obj})


@admin_required
def partner_list(request):
    """List all partners with options to edit and delete."""
    partners = Partner.objects.all().order_by('-id')

    # Handle delete partner
    if request.method == 'POST' and 'delete_partner' in request.POST:
        partner_id = request.POST.get('partner_id')
        partner_to_delete = get_object_or_404(Partner, id=partner_id)
        partner_to_delete.delete()
        messages.success(request, "Partner deleted successfully.")
        return redirect('adminapp:partner_list')

    # Handle update partner
    if request.method == 'POST' and 'update_partner' in request.POST:
        partner_id = request.POST.get('partner_id')
        partner = get_object_or_404(Partner, id=partner_id)

        partner.full_name = request.POST.get('full_name')
        partner.phone_number = request.POST.get('phone_number')
        partner.education = request.POST.get('education')
        partner.is_verified = bool(request.POST.get('is_verified'))
        partner.save()
        
        messages.success(request, "Partner updated successfully.")
        return redirect('adminapp:partner_list')

    paginator = Paginator(partners, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'adminapp/partner_list.html', {'page_obj': page_obj})


@admin_required
def booking_list(request):
    """List all bookings"""
    bookings = Booking.objects.all().order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(bookings, 20)  # 20 bookings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'adminapp/booking_list.html', {'page_obj': page_obj})

from django.shortcuts import render, get_object_or_404, redirect
from authentication.models import Booking
from .forms import BookingForm  # You will need to create this form if not already created

@admin_required
def edit_booking(request, booking_id):
    """Edit a booking's details."""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes')
        
        # Update the booking fields
        booking.status = status
        booking.notes = notes
        booking.save()
        
        # Redirect to the booking list after saving
        return redirect('adminapp:booking_list')

    return redirect('adminapp:booking_list')  # In case of a GET request, just redirect back

@admin_required
def delete_booking(request, booking_id):
    """Delete a booking."""
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    return redirect('adminapp:booking_list')



# @admin_required
# def service_list(request):
#     """List all service types"""
#     services = ServiceType.objects.all().order_by('name')
    
#     return render(request, 'adminapp/service_list.html', {'services': services})

@admin_required
def service_list(request):
    services = ServiceType.objects.all().order_by('name')

    if request.method == 'POST':
        service_id = request.POST.get('service_id')

        # Delete
        if 'delete_service' in request.POST:
            service = get_object_or_404(ServiceType, id=service_id)
            service.delete()
            messages.success(request, "Service deleted.")
            return redirect('adminapp:service_list')

        # Update
        elif 'update_service' in request.POST:
            service = get_object_or_404(ServiceType, id=service_id)
            service.name = request.POST.get('name')
            service.description = request.POST.get('description')
            service.base_hourly_rate = request.POST.get('base_hourly_rate')
            service.save()
            messages.success(request, "Service updated.")
            return redirect('adminapp:service_list')

    return render(request, 'adminapp/service_list.html', {'services': services})
