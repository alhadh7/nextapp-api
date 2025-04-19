
# from django.urls import path

# from . import views


# urlpatterns = [
#     # Common endpoints
#     path('home/', views.UserHomeView.as_view(), name='user-home'),
#     path('services/', views.ServiceTypeListView.as_view(), name='service-list'),
#     path('bookings/<int:booking_id>/', views.BookingDetailView.as_view(), name='booking-detail'),
    
#     # User endpoints
#     path('bookings/create/', views.CreateBookingView.as_view(), name='create-booking'),
#     path('bookings/<int:booking_id>/available-partners/', views.BookingAvailablePartnersView.as_view(), name='booking-available-partners'),
#     path('bookings/<int:booking_id>/select-partner/<int:partner_id>/', views.SelectPartnerView.as_view(), name='select-partner'),
#     path('bookings/<int:booking_id>/payment/', views.ProcessPaymentView.as_view(), name='process-payment'),
#     path('bookings/active/', views.UserActiveBookingsView.as_view(), name='user-active-bookings'),
#     path('bookings/<int:booking_id>/extension/', views.RequestBookingExtensionView.as_view(), name='request-extension'),
#     path('extensions/<int:extension_id>/payment/', views.ProcessExtensionPaymentView.as_view(), name='process-extension-payment'),
#     path('bookings/<int:booking_id>/review/', views.CreateReviewView.as_view(), name='create-review'),
    
#     # Partner endpoints
#     path('partner/home/', views.PartnerHomeView.as_view(), name='partner-home'),
#     path('partner/book-slot/',views.BookSlotView.as_view(), name='partner-book-slot'),

#     path('partner/bookings/available/', views.AvailableBookingsView.as_view(), name='partner-available-bookings'),
#     path('partner/bookings/<int:booking_id>/accept/', views.AcceptBookingView.as_view(), name='partner-accept-booking'),
#     path('partner/bookings/active/', views.PartnerActiveBookingsView.as_view(), name='partner-active-bookings'),
#     path('partner/bookings/<int:booking_id>/toggle-status/', views.ToggleWorkStatusView.as_view(), name='partner-toggle-work-status'),
#     path('partner/extensions/<int:extension_id>/respond/', views.RespondToExtensionRequestView.as_view(), name='partner-respond-extension'),
#     path('partner/bookings/completed/', views.PartnerCompletedBookingsView.as_view(), name='partner-completed-bookings'),
#     path('partner/reviews/', views.PartnerReviewsView.as_view(), name='partner-reviews'),
# ]