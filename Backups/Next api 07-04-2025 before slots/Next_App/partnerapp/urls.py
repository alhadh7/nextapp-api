
from django.urls import path

from . import views


urlpatterns = [
    # Common endpoints
    path('services/', views.ServiceTypeListView.as_view(), name='service-list'),
    path('bookings/<int:booking_id>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('partner/home/', views.PartnerHomeView.as_view(), name='partner-home'),

    path('partner/book-slot/',views.BookSlotView.as_view(), name='partner-book-slot'),
    path('partner/bookings/available/', views.AvailableBookingsView.as_view(), name='partner-available-bookings'),
    path('partner/bookings/<int:booking_id>/accept/', views.AcceptBookingView.as_view(), name='partner-accept-booking'),
    path('partner/bookings/active/', views.PartnerActiveBookingsView.as_view(), name='partner-active-bookings'),
    path('partner/bookings/<int:booking_id>/toggle-status/', views.ToggleWorkStatusView.as_view(), name='partner-toggle-work-status'),
    path('partner/extensions/<int:extension_id>/respond/', views.RespondToExtensionRequestView.as_view(), name='partner-respond-extension'),
    path('partner/bookings/completed/', views.PartnerCompletedBookingsView.as_view(), name='partner-completed-bookings'),
    path('partner/reviews/', views.PartnerReviewsView.as_view(), name='partner-reviews'),
]