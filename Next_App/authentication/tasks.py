from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking

@shared_task
def auto_cancel_bookings():
    now = timezone.now()
    timeout = timedelta(minutes=2)

    # Cancel bookings that are still unassigned after 30 minutes
    unassigned = Booking.objects.filter(
        status='pending',
        partner__isnull=True,
        created_at__lt=now - timeout
    )
    unassigned_count = unassigned.update(status='cancelled')

    # Cancel bookings with an assigned partner but unpaid after 30 minutes
    unpaid = Booking.objects.filter(
        # status='pending',
        partner__isnull=False,
        payment_status='pending',
        partner_accepted_at__lt=now - timeout
    )
    unpaid_count = unpaid.update(status='cancelled')

    print(f"Auto-cancelled {unassigned_count} unassigned and {unpaid_count} unpaid bookings.")
