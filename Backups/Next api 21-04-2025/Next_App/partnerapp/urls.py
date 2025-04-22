
from django.urls import path

from . import views


urlpatterns = [
    path('services/', views.ServiceTypeListView.as_view(), name='service-list'),
    path('bookings/<int:booking_id>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/history/', views.BookingHistoryView.as_view(), name='booking-history'),
    
    path('home/', views.PartnerHomeView.as_view(), name='partner-home'),
    path('book-slot/',views.BookSlotView.as_view(), name='partner-book-slot'),
    path('bookings/available/', views.AvailableBookingsView.as_view(), name='partner-available-bookings'),
    path('bookings/<int:booking_id>/accept/', views.AcceptBookingView.as_view(), name='partner-accept-booking'),
    path('bookings/active/', views.PartnerActiveBookingsView.as_view(), name='partner-active-bookings'),
    path('bookings/<int:booking_id>/toggle-status/', views.ToggleWorkStatusView.as_view(), name='partner-toggle-work-status'),
    path('extensions/<int:extension_id>/respond/', views.RespondToExtensionRequestView.as_view(), name='partner-respond-extension'),
    path('bookings/completed/', views.PartnerCompletedBookingsView.as_view(), name='partner-completed-bookings'),
    path('reviews/', views.PartnerReviewsView.as_view(), name='partner-reviews'),
]