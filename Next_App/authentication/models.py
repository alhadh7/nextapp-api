from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# User Manager
class UserManager(BaseUserManager):
    def create_user(self, phone_number, email, full_name, password=None):
        if not phone_number:
            raise ValueError("Users must have a phone number")

        user = self.model(phone_number=phone_number, email=email, full_name=full_name)

        if password:  # Only set a password if provided
            user.set_password(password)  # Hash the password

        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, email, full_name, password):
        """
        Create and return a superuser with the given details.
        """
        user = self.create_user(phone_number, email, full_name, password)
        user.is_admin = True
        user.is_staff = True
        user.set_password(password)

        user.is_superuser = True
        user.save(using=self._db)
        return user    

# User Model
class CustomUser(AbstractBaseUser):
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    user_address = models.CharField(max_length=255, null=True, blank=True)

    is_partner = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'full_name']
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    def get_full_name(self):
        return self.full_name

    # Permission checks for Django Admin
    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the given permission.
        """
        # Superusers have all permissions
        if self.is_superuser:
            return True
        # Implement other permission checks as needed, for example:
        return False

    def has_module_perms(self, app_label):
        """
        Returns True if the user has permission to access the given app's module.
        """
        # Superusers have access to all modules
        if self.is_superuser:
            return True
        # Implement more checks if needed for other roles
        return False

    def __str__(self):
        return f"{self.full_name} {self.phone_number} "

# Partner Model
class Partner(CustomUser):
    # is_verified = models.BooleanField(default=False)  
    # experience = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    experience = models.IntegerField(null=True, blank=True, db_index=True)  # Changed from CharField
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, default=None)


    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Personal Information
    adhar_card_front = models.ImageField(upload_to='documents/adhar_cards/front/', null=True, blank=True)  # Aadhar front image
    adhar_card_back = models.ImageField(upload_to='documents/adhar_cards/back/', null=True, blank=True)   # Aadhar back image
    driving_license_front = models.ImageField(upload_to='documents/driving_licenses/front/', null=True, blank=True)  # Driving license front image
    driving_license_back = models.ImageField(upload_to='documents/driving_licenses/back/', null=True, blank=True)  # Driving license back image
    profile_picture = models.ImageField(upload_to='documents/profile_pictures/', null=True, blank=True)  # Profile picture

    medical_certificate = models.FileField(upload_to='documents/certificates/',null=True, blank=True) # will this accept picture ?
    education = models.CharField(max_length=255)

    # Additional Information
    dob = models.DateField(null=True, blank=True)  # Date of Birth
    languages_known = models.CharField(max_length=255, null=True, blank=True)  # Languages known, comma-separated
    secondary_phone_number = models.CharField(max_length=20, null=True, blank=True)  # Secondary phone number

    # bank details
    bank_username = models.CharField(max_length=255, null=True, blank=True)
    bank_account_number = models.CharField(max_length=50, null=True, blank=True)
    ifsc_code = models.CharField(max_length=20, null=True, blank=True)

    razorpay_contact_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_fund_account_id = models.CharField(max_length=100, null=True, blank=True)

    # Location Details 
    address = models.CharField(max_length=255, null=True, blank=True)


    def save(self, *args, **kwargs):
        reset_fund_account = False
        update_contact = False

        if self.pk:  # Existing object
            old = Partner.objects.get(pk=self.pk)
            if (self.bank_account_number != old.bank_account_number or
                self.ifsc_code != old.ifsc_code):
                reset_fund_account = True

            if (self.full_name != old.full_name or self.email != old.email):
                update_contact = True
        else:
            # New object
            reset_fund_account = bool(self.bank_account_number and self.ifsc_code)
            update_contact = True

        if reset_fund_account:
            self.razorpay_fund_account_id = None

        super().save(*args, **kwargs)

        if self.razorpay_contact_id and update_contact:
            self.update_razorpay_contact()

    def update_razorpay_contact(self):
        import requests
        from django.conf import settings

        auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        contact_id = self.razorpay_contact_id
        url = f"https://api.razorpay.com/v1/contacts/{contact_id}"

        payload = {
            "name": self.full_name,
            "email": self.email,
            "contact": self.phone_number,
            "type": "vendor",
            "reference_id": f"partner_{self.id}",
            "notes": {"source": "contact_update_on_save"},
        }

        resp = requests.patch(url, auth=auth, json=payload)
        if resp.status_code not in (200, 201):
            print(f"Failed to update Razorpay contact: {resp.text}")


    def update_avg_rating(self):
            from django.db.models import Avg
            avg = self.assignments.filter(review__isnull=False).aggregate(avg_rating=Avg('review__rating'))['avg_rating']
            self.avg_rating = avg if avg is not None else None
            self.save(update_fields=['avg_rating'])



    def __str__(self):
        return f"Partner: {self.id} {self.full_name} ({self.phone_number})"

# OTP Model
class OTP(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.phone_number} - {self.otp}"
    
# Service types
class ServiceType(models.Model):
    SERVICE_CHOICES = (
        ('hospital_care', 'Hospital Care'),
        ('checkup_companion', 'Checkup Companion'),
        ('adult_care', 'Adult Care'),
        ('baby_sitting', 'Baby Sitting'),
    )
    
    name = models.CharField(max_length=50, choices=SERVICE_CHOICES, unique=True)
    description = models.TextField()
    base_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)  # <-- New field



    def __str__(self):
        return self.get_name_display()
    
from decimal import Decimal

# Booking Model
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    PARTNER_TYPE_CHOICES = (
        ('trained', 'Trained (2+ years)'),
        ('regular', 'Regular (Less than 2 years)'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    partner_type = models.CharField(max_length=10, choices=PARTNER_TYPE_CHOICES)
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    
    
    
    # Booking details
    is_instant = models.BooleanField(default=True)  # True for "Book Now", False for "Book Later"
    hours = models.PositiveIntegerField()
    scheduled_date = models.DateField(null=True, blank=True)  
    scheduled_time = models.TimeField(null=True, blank=True)  
    notes = models.TextField(blank=True, null=True)  # Optional field for storing additional notes



    # Locations
    user_location = models.CharField(max_length=255)
    lang = models.FloatField(null=True, blank=True)  # Latitude
    long = models.FloatField(null=True, blank=True)  # Longitude
    hospital_location = models.CharField(max_length=255, null=True, blank=True)  # Only for "Checkup Companion"
    
    # Status tracking

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    partner_accepted_at = models.DateTimeField(null=True, blank=True)


    # partner release tracking
     
    released_by = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_bookings')
    released_at = models.DateTimeField(null=True, blank=True)

    cancellation_reason = models.TextField(null=True, blank=True)

    work_started_at = models.DateTimeField(null=True, blank=True)
    work_ended_at = models.DateTimeField(null=True, blank=True)
    
    # Payment
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    
    def __str__(self):
        return f"{self.user.full_name} - {self.service_type} - {self.status} - {self.id}"
    

    def calculate_total_amount(self):
        base_rate = self.service_type.base_hourly_rate
        # Add premium for trained partners
        rate_multiplier = Decimal(1.5) if self.partner_type == 'trained' else Decimal(1.0)
        self.total_amount = base_rate * rate_multiplier * Decimal(self.hours)
        return self.total_amount



    class Meta:
            indexes = [
                models.Index(fields=['user', 'status'], name='booking_user_status_idx'),
            ]


# Booking requests from users to partners
class BookingRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('released', 'Released'),  

    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='requests')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='booking_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('booking', 'partner')
        indexes = [
                    models.Index(fields=['booking', 'status'], name='booking_request_status_idx'),
                ]


    def __str__(self):
        return f"BookingRequest {self.id}: {self.booking.user.full_name} - {self.partner.full_name} - {self.status}"


# Extension requests for additional hours
class BookingExtension(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='extensions', db_index=True) #new dn index
    additional_hours = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    partner_accepted_at = models.DateTimeField(null=True, blank=True)

    cancellation_reason = models.TextField(null=True, blank=True)

    # Payment for extension
    extension_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"BookingExtension {self.id}: {self.booking.id} - {self.status}"
    
# Reviews and Ratings
class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField()  # 1-5 star rating
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.id} for Booking {self.booking.id} - Rating: {self.rating}"

class PartnerSlot(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('partner', 'date', 'start_time', 'end_time')

    def __str__(self):
        return f"PartnerSlot {self.id}: {self.partner.full_name} - {self.date} {self.start_time}-{self.end_time}"



class PartnerWallet(models.Model):
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_payout_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"PartnerWallet {self.id}: {self.partner.full_name} - ₹{self.balance}"
    
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('booking_payment', 'Booking Payment'),
        ('extension_payment', 'Extension Payment'),
        ('partner_payout', 'Partner Payout'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    extension = models.ForeignKey(BookingExtension, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    partner_wallet = models.ForeignKey(PartnerWallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    refund_id = models.CharField(max_length=100, null=True, blank=True)
    refund_status = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.id}: {self.transaction_type} - ₹{self.amount} - {self.status}"
    

# models.py 
class FCMToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=255)  # Removed unique=True
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'token')  # Only prevent duplicate user-token pairs

