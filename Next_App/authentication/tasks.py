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

    # Cancel unassigned bookings after timeout
    unassigned = Booking.objects.filter(
        status='pending',
        partner__isnull=True,
        created_at__lt=now - timeout
    )
    for booking in unassigned:
        booking.status = 'cancelled'
        booking.cancellation_reason = 'Auto-cancelled: No partner assigned in time'
        booking.save()

    # Cancel assigned but unpaid bookings after timeout
    unpaid = Booking.objects.filter(
        partner__isnull=False,
        payment_status='pending',
        partner_accepted_at__lt=now - timeout
    )
    for booking in unpaid:
        booking.status = 'cancelled'
        booking.cancellation_reason = 'Auto-cancelled: Payment not completed in time'
        booking.save()

    # Cancel approved extensions not paid
    unpaid_extensions = BookingExtension.objects.filter(
        status='approved',
        payment_status='pending',
        partner_accepted_at__lt=now - extension_timeout
    )
    for extension in unpaid_extensions:
        extension.status = 'rejected'
        extension.cancellation_reason = 'Auto-rejected: Payment for extension not completed in time'
        extension.save()

    # Cancel pending extensions not responded to
    stale_pending_extensions = BookingExtension.objects.filter(
        status='pending',
        requested_at__lt=now - extension_timeout
    )
    for extension in stale_pending_extensions:
        extension.status = 'rejected'
        extension.cancellation_reason = 'Auto-rejected: No response to extension request'
        extension.save()

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
        f"Auto-cancelled {unassigned.count()} unassigned, "
        f"{unpaid.count()} unpaid bookings, "
        f"{unpaid_extensions.count()} unpaid approved extensions, and "
        f"{stale_pending_extensions.count()} stale pending extensions."
        f"{stuck_paid_bookings.count()} stuck paid notified."

    )