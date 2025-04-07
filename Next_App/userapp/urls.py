
from django.urls import path

from . import views


urlpatterns = [
    # Common endpoints
    path('home/', views.UserHomeView.as_view(), name='user-home'),
    path('services/', views.ServiceTypeListView.as_view(), name='service-list'),
    path('bookings/<int:booking_id>/', views.BookingDetailView.as_view(), name='booking-detail'),
    
    # User endpoints
    path('bookings/create/', views.CreateBookingView.as_view(), name='create-booking'),
    path('bookings/<int:booking_id>/available-partners/', views.BookingAvailablePartnersView.as_view(), name='booking-available-partners'),
    path('bookings/<int:booking_id>/select-partner/<int:partner_id>/', views.SelectPartnerView.as_view(), name='select-partner'),

    # User payments
    path('bookings/<int:booking_id>/create-order/', views.CreateBookingOrderView.as_view()),
    path('bookings/<int:booking_id>/process-payment/', views.ProcessPaymentView.as_view()),
    path('extensions/<int:extension_id>/create-order/', views.CreateExtensionOrderView.as_view()),
    path('extensions/<int:extension_id>/process-payment/', views.ProcessExtensionPaymentView.as_view()),

    path('bookings/active/', views.UserActiveBookingsView.as_view(), name='user-active-bookings'),
    path('bookings/<int:booking_id>/extension/', views.RequestBookingExtensionView.as_view(), name='request-extension'),
    path('bookings/<int:booking_id>/review/', views.CreateReviewView.as_view(), name='create-review'),
    
    path('razorpay/webhook/', views.RazorPayWebhookView.as_view(), name='razorpay-webhook'),

]