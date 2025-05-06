from datetime import timezone
from django.contrib import admin

from .models import OTP, Booking, BookingExtension, BookingRequest, CustomUser, FCMToken, Partner, PartnerSlot, PartnerWallet, Review, ServiceType, Transaction


# Register your models here.
admin.site.register(CustomUser)

admin.site.register(Partner)

admin.site.register(ServiceType)

admin.site.register(Booking)

admin.site.register(BookingRequest)

admin.site.register(BookingExtension)

admin.site.register(Review)

admin.site.register(OTP)

admin.site.register(FCMToken)

admin.site.register(PartnerWallet)

admin.site.register(Transaction)
admin.site.register(PartnerSlot)