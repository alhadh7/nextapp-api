from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# Create your models here.
# User Manager
class UserManager(BaseUserManager):
    def create_user(self, phone_number, email, full_name, password=None):
        if not phone_number:
            raise ValueError("Users must have a phone number")
        user = self.model(phone_number=phone_number, email=email, full_name=full_name)
        user.set_password(password)
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
    is_partner = models.BooleanField(default=False)
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'full_name']
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()
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
    
# Partner Model
class Partner(CustomUser):
    education = models.CharField(max_length=255)
    medical_certificate = models.FileField(upload_to='certificates/',null=True, blank=True)
    
# OTP Model
class OTP(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)