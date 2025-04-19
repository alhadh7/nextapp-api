from django.contrib import admin

from .models import Booking, CustomUser, Partner, ServiceType

# Register your models here.
admin.site.register(CustomUser)

admin.site.register(Partner)

admin.site.register(ServiceType)

admin.site.register(Booking)