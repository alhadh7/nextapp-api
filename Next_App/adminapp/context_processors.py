from django.utils.timezone import now
from datetime import timedelta
from authentication.models import Booking  # or wherever Booking is

def stuck_paid_notifications(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return {}
    
    timeout = timedelta(minutes=30)
    stuck_bookings = Booking.objects.filter(
        status='pending',
        payment_status='paid',
        partner__isnull=True,
        released_at__lt=now() - timeout
    )
    
    return {
        'stuck_paid_bookings_count': stuck_bookings.count(),
        'stuck_paid_bookings': stuck_bookings[:5]  # limit for dropdown
    }
