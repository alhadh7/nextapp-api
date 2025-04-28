# adminapp/urls.py
from django.urls import path
from .views import *

app_name = 'adminapp'

urlpatterns = [
    # Authentication URLs
    path('login/', login_view, name='login'),
    path('totp-verify/', totp_verify_view, name='totp_verify'),
    path('totp-setup/', totp_setup_view, name='totp_setup'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboard URLs
    path('', dashboard, name='dashboard'),
    
    # Basic model management URLs - just placeholders for now
    path('users/', user_list, name='user_list'),
    path('partners/', partner_list, name='partner_list'),
    path('services/', service_list, name='service_list'),

    path('bookings/', booking_list, name='booking_list'),
    path('bookings/edit/<int:booking_id>/', edit_booking, name='edit_booking'),
    path('bookings/delete/<int:booking_id>/', delete_booking, name='delete_booking'),

                    
]