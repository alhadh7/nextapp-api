from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingExtension

@shared_task
def auto_cancel_bookings():
    now = timezone.now()
    # timeout = timedelta(minutes=15)
    timeout = timedelta(minutes=10)
    extension_timeout = timedelta(minutes=10)
    release_timeout = timedelta(minutes=30)

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

   # ✅ Notify admin if paid booking is pending for 30+ minutes and still unassigned
    stuck_paid_bookings = Booking.objects.filter(
        status='pending',
        payment_status='paid',
        partner__isnull=True,
        released_at__lt=now - release_timeout
    )


    # instead of mail use whatsapp , and alert in panel
    # if stuck_paid_bookings.exists():
    #     booking_list = "\n".join([f"ID: {b.id}, Date: {b.scheduled_date}, User: {b.user.full_name}" for b in stuck_paid_bookings])
    #     send_mail(
    #         subject="🚨 Unassigned Paid Bookings (30+ min delay)",
    #         message=f"The following paid bookings have not been accepted by any partner:\n\n{booking_list}",
    #         from_email=settings.DEFAULT_FROM_EMAIL,
    #         recipient_list=[settings.ADMIN_EMAIL],
    #         fail_silently=False
    #     )


    print(
        f"Auto-cancelled {unassigned_count} unassigned, "
        f"{unpaid_count} unpaid bookings, "
        f"{unpaid_extension_count} unpaid approved extensions, and "
        f"{stale_extension_count} stale pending extensions."
        f"{stuck_paid_bookings.count()} stuck paid notified."

    )