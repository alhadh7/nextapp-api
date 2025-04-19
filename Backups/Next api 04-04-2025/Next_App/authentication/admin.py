from django.contrib import admin

from .models import CustomUser, Partner

# Register your models here.
admin.site.register(CustomUser)

admin.site.register(Partner)

