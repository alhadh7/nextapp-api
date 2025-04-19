from django.contrib import admin

from .models import OTP, Booking, BookingExtension, BookingRequest, CustomUser, Partner, Review, ServiceType

# Register your models here.
admin.site.register(CustomUser)

admin.site.register(Partner)

admin.site.register(ServiceType)

admin.site.register(Booking)

admin.site.register(BookingRequest)

admin.site.register(BookingExtension)

admin.site.register(Review)

admin.site.register(OTP)