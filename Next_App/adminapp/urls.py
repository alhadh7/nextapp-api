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

    path('bookings/stuck/', stuck_paid_bookings, name='stuck_paid_bookings'),
    path('bookings/assign-partner/<int:booking_id>/', assign_partner, name='assign_partner'),

    path('bookings/edit/<int:booking_id>/', edit_booking, name='edit_booking'),
    path('bookings/delete/<int:booking_id>/', delete_booking, name='delete_booking'),

    path('partners/<int:partner_id>/trigger-payout/', trigger_partner_payout, name='trigger_partner_payout'),

    path('bookings/<int:booking_id>/refund/', refund_booking, name='refund_booking'),


]