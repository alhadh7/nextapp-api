from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingExtension

@shared_task
def auto_cancel_bookings():
    now = timezone.now()
    # timeout = timedelta(minutes=15)
    timeout = timedelta(minutes=5)
    extension_timeout = timedelta(minutes=5)

    # Cancel bookings that are still unassigned after 15 minutes
    unassigned = Booking.objects.filter(
        status='pending',
        partner__isnull=True,
        created_at__lt=now - timeout
    )
    unassigned_count = unassigned.update(status='cancelled')

    # Cancel bookings with an assigned partner but unpaid after 15 minutes
    unpaid = Booking.objects.filter(
        # status='pending',
        partner__isnull=False,
        payment_status='pending',
        partner_accepted_at__lt=now - timeout
    )
    unpaid_count = unpaid.update(status='cancelled')


    # Cancel approved extensions not paid within 5 minute of approval
    unpaid_extensions = BookingExtension.objects.filter(
        status='approved',
        payment_status='pending',
        partner_accepted_at__lt=now - extension_timeout
    )

    unpaid_extension_count = unpaid_extensions.update(status='rejected')

    # Cancel pending extensions not responded to within 5 minute
    stale_pending_extensions = BookingExtension.objects.filter(
        status='pending',
        requested_at__lt=now - extension_timeout
    )
    stale_extension_count = stale_pending_extensions.update(status='rejected')

    print(
        f"Auto-cancelled {unassigned_count} unassigned, "
        f"{unpaid_count} unpaid bookings, "
        f"{unpaid_extension_count} unpaid approved extensions, and "
        f"{stale_extension_count} stale pending extensions."
    )