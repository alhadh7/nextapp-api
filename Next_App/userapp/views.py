from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from authentication.utilities.utils import send_push_notification
from authentication.models import (
    CustomUser, Partner, PartnerWallet, ServiceType, Booking, 
    BookingRequest, BookingExtension, Review, Transaction
)
from authentication.serializers import (
    CustomUserSerializer, PartnerSerializer, ServiceTypeSerializer,
    BookingCreateSerializer, BookingDetailSerializer, BookingRequestSerializer,
    BookingExtensionSerializer, ReviewSerializer
)

import logging
logger = logging.getLogger(__name__)


# Common views for both partners and users
class UserHomeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Welcome to homepage",
            "user": request.user.full_name
        }, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceTypeListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer

class BookingHistoryView(generics.ListAPIView):
    serializer_class = BookingDetailSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user
        print(user.__dict__)

        is_partner = self.request.auth.get('is_partner', False) if self.request.auth else False
        
        if is_partner:
            print('is partner')
            # Partner's booking history
            return Booking.objects.filter(partner=user, status__in=['completed', 'cancelled']).order_by('-created_at')
        else:
            print('is user')
            # User's booking history
            return Booking.objects.filter(user=user, status__in=['completed', 'cancelled']).order_by('-created_at')



class BookingDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, booking_id):

        is_partner = self.request.auth.get('is_partner', False) if self.request.auth else False

        # Handle both user and partner access
        if is_partner:

            # Partner can only view bookings assigned to them
            booking = get_object_or_404(
                Booking, 
                id=booking_id,
                partner_id=request.user.id
            )
        else:
            # Regular user can only view their own bookings
            booking = get_object_or_404(
                Booking, 
                id=booking_id,
                user=request.user
            )
        
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateBookingView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if user is not a partner
        is_partner = self.request.auth.get('is_partner', False) if self.request.auth else False
        if is_partner:
            return Response({
                "error": "Partners cannot make bookings."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get booking data
        booking_data = request.data
        is_instant = booking_data.get("is_instant", True)

        # Validate service availability
        service_id = booking_data.get("service_type")
        if not service_id:
            return Response({
                "error": "Service type is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = ServiceType.objects.get(id=service_id)
        except ServiceType.DoesNotExist:
            return Response({
                "error": "Selected service does not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not service.is_active:
            return Response({
                "error": "This service is currently disabled and cannot be booked."
            }, status=status.HTTP_403_FORBIDDEN)



        # Determine booking date
        if is_instant:
            booking_day = timezone.localdate()
        else:
            scheduled_date = booking_data.get("scheduled_date")
            if not scheduled_date:
                return Response({
                    "error": "Scheduled date is required for book later."
                }, status=status.HTTP_400_BAD_REQUEST)
            booking_day = scheduled_date

        # Check total number of bookings on this day (max 3)
        same_day_bookings = Booking.objects.filter(
            user=request.user,
            scheduled_date=booking_day
        ).exclude(status='cancelled')

        if same_day_bookings.count() >= 3:
            return Response({
                "error": "You already have 3 bookings on this day."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if there's any incomplete booking on the same day
        incomplete_bookings = same_day_bookings.exclude(
            status='completed', 
            work_ended_at__isnull=False
        )
        
        if incomplete_bookings.exists():
            return Response({
                "error": "You need to complete your existing booking before making a new one on this day."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Additional check for scheduled bookings (time overlap)
        if not is_instant:
            scheduled_time_str = booking_data.get("scheduled_time")
            hours = int(booking_data.get("hours", 0))

            if not scheduled_time_str:
                return Response({
                    "error": "Time is required for scheduled bookings."
                }, status=status.HTTP_400_BAD_REQUEST)

            scheduled_time = datetime.strptime(scheduled_time_str, "%H:%M").time()
            
            # Convert to datetime for range comparison
            start_datetime = datetime.combine(
                datetime.strptime(booking_day, "%Y-%m-%d").date() if isinstance(booking_day, str) else booking_day,
                scheduled_time
            )
            end_datetime = start_datetime + timedelta(hours=hours)

            # Time overlap check is unnecessary since we already confirmed no incomplete bookings exist
            # But kept for data integrity (in case of race conditions)
            overlapping_bookings = Booking.objects.filter(
                user=request.user,
                scheduled_date=booking_day,
                scheduled_time__isnull=False,
            ).exclude(status='cancelled')

            for b in overlapping_bookings:
                existing_start = datetime.combine(b.scheduled_date, b.scheduled_time)
                existing_end = existing_start + timedelta(hours=b.hours)
                if (start_datetime < existing_end) and (end_datetime > existing_start):
                    return Response({
                        "error": f"Booking overlaps with another scheduled from {existing_start.time()} to {existing_end.time()}."
                    }, status=status.HTTP_400_BAD_REQUEST)

        # Create the booking
        serializer = BookingCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            booking = serializer.save()
            
            # Return booking with details
            detail_serializer = BookingDetailSerializer(booking)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class CancelBookingView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, booking_id):
#         try:
#             booking = Booking.objects.get(id=booking_id, user=request.user)
#         except Booking.DoesNotExist:
#             return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

#         if booking.status == 'cancelled':
#             return Response({"message": "Booking is already cancelled."}, status=status.HTTP_200_OK)

#         if booking.status in ['completed', 'in_progress']:
#             return Response({"error": "Cannot cancel a booking that is already in progress or completed."}, status=status.HTTP_400_BAD_REQUEST)

#         booking.status = 'cancelled'
#         booking.save()

#         return Response({"message": "Booking has been cancelled due to partner unavailability."}, status=status.HTTP_200_OK)


class PendingBookingListView(generics.ListAPIView):
    serializer_class = BookingDetailSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            user=user,
            status='pending',
            partner__isnull=True
        ).order_by('-created_at')


# class BookingAvailablePartnersView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request, booking_id):
#         booking = get_object_or_404(Booking, id=booking_id, user=request.user)

#         # Auto-cancel if expired and unassigned
#         if (
#             booking.status == 'pending' and
#             booking.partner is None and
#             timezone.now() - booking.created_at > timedelta(minutes=30)
#         ):
#             booking.status = 'cancelled'
#             booking.save()
#             return Response({
#                 "error": "Booking auto-cancelled due to no available partners after 30 minutes."
#             }, status=status.HTTP_400_BAD_REQUEST)


#         # Get partners who have already accepted this booking
#         partners = Partner.objects.filter(
#             booking_requests__booking=booking,
#             booking_requests__status='accepted',
#             is_verified=True
#         )
        
#         # Filter partners based on verification and experience
#         if booking.partner_type == 'trained':
#             partners = partners.filter(experience__gte=2)
#         else:
#             partners = partners.filter(experience__lt=2)
        
#         serializer = PartnerSerializer(partners, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

from django.db.models import IntegerField
from django.db.models.functions import Cast


class BookingAvailablePartnersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        # Auto-cancel if expired and unassigned
        # legacy now uses celery for cancellations
        # if (
        #     booking.status == 'pending' and
        #     booking.partner is None and
        #     timezone.now() - booking.created_at > timedelta(minutes=30)
        # ):
        #     booking.status = 'cancelled'
        #     booking.save()
        #     print("Booking auto-cancelled due to timeout.")
        #     return Response({
        #         "error": "Booking auto-cancelled due to no available partners after 30 minutes."
        #     }, status=status.HTTP_400_BAD_REQUEST)

        # print(f"Booking ID: {booking.id}, Partner Type: {booking.partner_type}")

        # Step 1: Partners who accepted the booking
        accepted_partners = Partner.objects.filter(
            booking_requests__booking=booking,
            booking_requests__status='accepted'
        )
        # print(f"Accepted partners count: {accepted_partners.count()}")

        # Step 2: Only verified partners
        verified_partners = accepted_partners.filter(is_verified=True)
        # print(f"Verified accepted partners count: {verified_partners.count()}")

        # Step 3: Cast experience to Integer for proper filtering
        verified_partners = verified_partners.annotate(
            experience_int=Cast('experience', IntegerField())
        )

        # Step 4: Filter by experience based on partner_type
        if booking.partner_type == 'trained':
            final_partners = verified_partners.filter(experience_int__gte=2)
            # print("Filtering for trained partners with experience >= 2")
        else:
            final_partners = verified_partners.filter(experience_int__lt=2)
            # print("Filtering for untrained partners with experience < 2")

        # print(f"Final partners count after filtering: {final_partners.count()}")

        serializer = PartnerSerializer(final_partners, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SelectPartnerView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id, partner_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='pending')
        partner = get_object_or_404(Partner, id=partner_id, is_verified=True)
        
        # Validate partner has accepted this booking
        booking_request = get_object_or_404(
            BookingRequest,
            booking=booking,
            partner=partner,
            status='accepted'
        )
        
        # Update booking with selected partner
        booking.partner = partner
        booking.status = 'confirmed'
        booking.partner_accepted_at = timezone.now()

        booking.save()
        
        # Return updated booking
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

# class ProcessPaymentView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, booking_id):
#         booking = get_object_or_404(
#             Booking, 
#             id=booking_id, 
#             user=request.user,
#             status='confirmed',
#             payment_status='pending'
#         )
        
#         # Dummy payment processing
#         booking.payment_status = 'paid'
#         booking.save()
        
#         return Response({
#             "message": "Payment processed successfully",
#             "booking_id": booking.id,
#             "amount": booking.total_amount
#         }, status=status.HTTP_200_OK)


class CreateBookingOrderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking, 
            id=booking_id, 
            user=request.user,
            status='confirmed',
            payment_status='pending'
        )
        
        # Create RazorPay order
        try:
            order_amount = int(booking.total_amount * 100)  # Amount in paise
            order_currency = 'INR'
            order_receipt = f"booking_{booking.id}"
            notes = {'booking_id': str(booking.id)}
            
            razorpay_order = razorpay_client.order.create({
                'amount': order_amount,
                'currency': order_currency,
                'receipt': order_receipt,
                'notes': notes,
            })
            
            # Create a pending transaction
            Transaction.objects.create(
                booking=booking,
                amount=booking.total_amount,
                transaction_type='booking_payment',
                razorpay_order_id=razorpay_order['id'],
                status='pending'
            )
            
            # Return order information to frontend
            return Response({
                'order_id': razorpay_order['id'],
                'amount': order_amount / 100,  # Convert back to rupees for display
                'currency': order_currency,
                'booking_id': booking.id,
                'name': request.user.full_name,
                'email': request.user.email,
                'contact': request.user.phone_number
                }
            , status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# from decimal import Decimal
# import razorpay
# from django.conf import settings

# # Initialize Razorpay client
# razorpay_client = razorpay.Client(
#     auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# class ProcessPaymentView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, booking_id):
#         booking = get_object_or_404(
#             Booking, 
#             id=booking_id, 
#             user=request.user,
#             status='confirmed',
#             payment_status='pending'
#         )
        
#         razorpay_payment_id = request.data.get('razorpay_payment_id')
#         razorpay_order_id = request.data.get('razorpay_order_id')
        
#         # Find the related transaction
#         try:
#             transaction = Transaction.objects.get(
#                 booking=booking,
#                 razorpay_order_id=razorpay_order_id
#             )
#         except Transaction.DoesNotExist:
#             return Response({
#                 "error": "Transaction not found"
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Handle payment success
#         if  razorpay_payment_id:
#             # Update booking payment status
#             booking.payment_status = 'paid'
#             booking.save()
            
#             # Update transaction
#             transaction.razorpay_payment_id = razorpay_payment_id
#             transaction.status = 'completed'
#             transaction.save()
             
#             # Update partner wallet (if applicable)
#             if booking.partner:
#                 partner_amount = booking.total_amount * Decimal('0.75')
#                 wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
#                 wallet.balance += partner_amount
#                 wallet.save()
            
#             return Response({
#                 "message": "Payment processed successfully",
#                 "booking_id": booking.id,
#                 "amount": booking.total_amount,
#                 "razorpay_payment_id": razorpay_payment_id
#             }, status=status.HTTP_200_OK)
        
#         # Handle payment failure
#         else:
#             # Update booking payment status
#             booking.payment_status = 'failed'
#             booking.save()
            
#             # Update transaction
#             transaction.status = 'failed'
#             if razorpay_payment_id:
#                 transaction.razorpay_payment_id = razorpay_payment_id
#             transaction.save()
            
#             return Response({
#                 "error": "Payment failed",
#                 "booking_id": booking.id
#             }, status=status.HTTP_400_BAD_REQUEST)

from decimal import ROUND_DOWN, Decimal
import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class ProcessPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking, 
            id=booking_id, 
            user=request.user,
            status='confirmed',
            payment_status='pending'
        )
        
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')

        # Find the related transaction
        try:
            transaction = Transaction.objects.get(
                booking=booking,
                razorpay_order_id=razorpay_order_id
            )
        except Transaction.DoesNotExist:
            return Response({
                "error": "Transaction not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle payment success
        if razorpay_payment_id and razorpay_signature:
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            try:
                razorpay_client.utility.verify_payment_signature(params_dict)
            except razorpay.errors.SignatureVerificationError:
                # Signature verification failed
                booking.payment_status = 'failed'
                booking.save()

                transaction.status = 'failed'
                transaction.razorpay_payment_id = razorpay_payment_id
                transaction.save()

                return Response({
                    "error": "Payment signature verification failed",
                    "booking_id": booking.id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Signature verified successfully
            booking.payment_status = 'paid'
            booking.save()
            
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.status = 'completed'
            transaction.save()
             
            # Update partner wallet (if applicable)
            if booking.partner:
                partner_amount = booking.total_amount * Decimal('0.75')
                wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
                wallet.balance += partner_amount
                wallet.save()
            
            return Response({
                "message": "Payment processed successfully",
                "booking_id": booking.id,
                "amount": booking.total_amount,
                "razorpay_payment_id": razorpay_payment_id
            }, status=status.HTTP_200_OK)
        
        # Handle missing fields or failure
        else:
            booking.payment_status = 'failed'
            booking.save()
            
            transaction.status = 'failed'
            if razorpay_payment_id:
                transaction.razorpay_payment_id = razorpay_payment_id
            transaction.save()
            
            return Response({
                "error": "Payment failed",
                "booking_id": booking.id
            }, status=status.HTTP_400_BAD_REQUEST)



class UserActiveBookingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):

        is_partner = self.request.auth.get('is_partner', False) if self.request.auth else False
        if is_partner:
            return Response({
                "error": "Partners cannot see user bookings."
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Active bookings are those that are pending, confirmed, in progress, or scheduled for future
        active_bookings = Booking.objects.filter(
            user=request.user
        ).filter(
            Q(status='pending') | Q(status='confirmed') | Q(status='in_progress')
        )
        
        serializer = BookingDetailSerializer(active_bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RequestBookingExtensionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
        # Retrieve the booking object
        booking = get_object_or_404(
            Booking, 
            id=booking_id, 
            user=request.user,
            status='in_progress'
        )


        # ❌ Check if there's an existing extension that is not rejected
        existing_active_extension = booking.extensions.filter(
            status__in=['pending', 'approved']
        ).exists()

        if existing_active_extension:
            return Response(
                {"error": "An extension request already exists for this booking."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ⛔ Prevent requesting extension if <15 min remain from expected end time
        if booking.work_started_at:
            expected_end_time = booking.work_started_at + timedelta(hours=booking.hours)
            time_remaining = expected_end_time - timezone.now()
            if time_remaining < timedelta(minutes=15):
                return Response(
                    {"error": "You can no longer request an extension. Please request at least 15 minutes before the expected end of the job."},
                    status=status.HTTP_400_BAD_REQUEST
                )


        # Add the 'booking' object to the incoming request data
        request.data['booking'] = booking.id  # Use the booking's ID in the request data
        
        # Now the serializer can use this value in the validated data
        serializer = BookingExtensionSerializer(data=request.data)
        
        if serializer.is_valid():
            extension = serializer.save()  # Create and save the booking extension

            # ✅ Send notification to the partner
            if booking.partner and booking.partner.user:
                try:
                    print('partner data:',booking.partner.user)
                    send_push_notification(
                        user=booking.partner.user,
                        title="Extension Requested",
                        body=f"An extension has been requested for Booking #{booking.id}.",
                        data={"booking_id": str(booking.id), "extension_id": extension.id, "status": "extension_requested"}
                    )
                except Exception as e:
                    logger.warning(f"Failed to send extension notification to partner for booking #{booking.id}: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





# class ProcessExtensionPaymentView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, extension_id):
#         extension = get_object_or_404(
#             BookingExtension, 
#             id=extension_id, 
#             booking__user=request.user,
#             status='approved',
#             payment_status='pending'
#         )
        
#         # Dummy payment processing
#         extension.payment_status = 'paid'
#         extension.save()
        
#         # Update booking hours
#         booking = extension.booking
#         booking.hours += extension.additional_hours
#         booking.total_amount += extension.extension_amount
#         booking.save()
        
#         return Response({
#             "message": "Extension payment processed successfully",
#             "extension_id": extension.id,
#             "amount": extension.extension_amount
#         }, status=status.HTTP_200_OK)


class CreateExtensionOrderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, extension_id):
        extension = get_object_or_404(
            BookingExtension, 
            id=extension_id,
            booking__user=request.user,
            status='approved',
            payment_status='pending'
        )
        
        # Create RazorPay order
        try:
            order_amount = int(extension.extension_amount * 100)  # Amount in paise
            order_currency = 'INR'
            order_receipt = f"extension_{extension.id}"
            notes = {
                'booking_id': str(extension.booking.id),
                'extension_id': str(extension.id)
            }
            
            razorpay_order = razorpay_client.order.create({
                'amount': order_amount,
                'currency': order_currency,
                'receipt': order_receipt,
                'notes': notes,
            })
            
            # Create a pending transaction
            Transaction.objects.create(
                extension=extension,
                amount=extension.extension_amount,
                transaction_type='extension_payment',
                razorpay_order_id=razorpay_order['id'],
                status='pending'
            )
            
            # Return order information to frontend
            return Response({
                'order_id': razorpay_order['id'],
                'amount': order_amount / 100,  # Convert back to rupees for display
                'currency': order_currency,
                'extension_id': extension.id,
                'booking_id': extension.booking.id,
                'name': request.user.full_name,
                'email': request.user.email,
                'contact': request.user.phone_number
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
class ProcessExtensionPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, extension_id):
        extension = get_object_or_404(
            BookingExtension, 
            id=extension_id, 
            booking__user=request.user,
            status='approved',
            payment_status='pending'
        )
        
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')

        # Find the related transaction
        try:
            transaction = Transaction.objects.get(
                extension=extension,
                razorpay_order_id=razorpay_order_id
            )
        except Transaction.DoesNotExist:
            return Response({
                "error": "Transaction not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle payment success
        if  razorpay_payment_id:
            # Update extension payment status
            extension.payment_status = 'paid'
            extension.save()
            
            # Update transaction
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.status = 'completed'
            transaction.save()
            
            # Update booking hours
            booking = extension.booking
            booking.hours += extension.additional_hours
            booking.total_amount += extension.extension_amount
            booking.save()
            
            # Update partner wallet (if applicable)
            if booking.partner:
                partner_amount = extension.extension_amount * Decimal('0.75')
                wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
                wallet.balance += partner_amount
                wallet.save()
            
            return Response({
                "message": "Extension payment processed successfully",
                "extension_id": extension.id,
                "amount": extension.extension_amount,
                "razorpay_payment_id": razorpay_payment_id
            }, status=status.HTTP_200_OK)
        
        # Handle payment failure
        else:
            # Update extension payment status
            extension.payment_status = 'failed'
            extension.save()
            
            # Update transaction
            transaction.status = 'failed'
            if razorpay_payment_id:
                transaction.razorpay_payment_id = razorpay_payment_id
            transaction.save()
            
            return Response({
                "error": "Payment failed",
                "extension_id": extension.id
            }, status=status.HTTP_400_BAD_REQUEST)


from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db import transaction as db_transaction
from django.utils import timezone
from datetime import datetime, timedelta
import razorpay

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        # ❌ Block if already started
        if booking.work_started_at:
            return Response({"error": "Cannot cancel; service already started."}, status=400)

        # ⏱ Block if within 2 hours of scheduled time
        if not booking.is_instant and booking.scheduled_date and booking.scheduled_time:
            scheduled_dt = timezone.make_aware(
                datetime.combine(booking.scheduled_date, booking.scheduled_time),
                timezone.get_current_timezone()
            )
            if scheduled_dt - timezone.now() < timedelta(hours=2):
                return Response({"error": "Cancellations must be made at least 2 hours before start."}, status=400)

        # 🟡 If unpaid
        if booking.payment_status == 'pending':
            booking.status = 'cancelled'
            booking.save()
            return Response({"message": f"Booking #{booking.id} cancelled (no payment made)."}, status=200)

        # ✅ Paid and eligible for refund
        if booking.payment_status == 'paid' and booking.status == 'confirmed' and booking.partner:
            txn = Transaction.objects.filter(
                booking=booking,
                transaction_type='booking_payment',
                status='completed'
            ).first()

            if not txn or not txn.razorpay_payment_id:
                return Response({"error": "Valid payment not found."}, status=400)

            try:
                with db_transaction.atomic():
                    # Refund

                    txn_amount = txn.amount  # Assume txn.amount is a Decimal or float

                    # Convert txn_amount to Decimal if it's not already
                    txn_amount_decimal = Decimal(str(txn_amount))

                    # Reducing it by 2.4%
                    reduced_amount = txn_amount_decimal * (Decimal(1) - Decimal(2.4) / Decimal(100))

                    # Round down to 2 decimal places (using ROUND_DOWN)
                    reduced_amount = reduced_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

                    print("reduced",reduced_amount)

                    refund = razorpay_client.payment.refund(txn.razorpay_payment_id, {
                        "amount": int(reduced_amount * 100),
                        "speed": "optimum"
                    })

                    # Update transaction
                    txn.status = 'refunded'
                    txn.refund_id = refund.get('id')
                    txn.refund_status = refund.get('status')
                    txn.save()

                    # Update booking
                    booking.status = 'cancelled'
                    booking.payment_status = 'refunded'
                    booking.cancellation_reason = "Cancelled and refunded"

                    booking.save()

                    # Notify partner
                    send_push_notification(
                        user=booking.partner,
                        title="Booking Cancelled",
                        body=f"User cancelled booking #{booking.id}.",
                        data={"booking_id": str(booking.id), "status": "cancelled"}
                    )

                    return Response({"message": f"Booking #{booking.id} refunded and cancelled."}, status=200)

            except razorpay.errors.BadRequestError as e:
                return Response({"error": f"Refund failed: {str(e)}"}, status=400)
            except Exception as e:
                return Response({"error": f"Unexpected error: {str(e)}"}, status=500)


        # ✅ If partner released and no new one assigned, allow refund
        if (
            booking.payment_status == 'paid' and
            booking.status == 'pending' and
            booking.partner is None and
            booking.released_by is not None
        ):
            txn = Transaction.objects.filter(
                booking=booking,
                transaction_type='booking_payment',
                status='completed'
            ).first()

            if not txn or not txn.razorpay_payment_id:
                return Response({"error": "Valid payment not found."}, status=400)

            try:
                with db_transaction.atomic():
                    refund = razorpay_client.payment.refund(txn.razorpay_payment_id, {
                        "amount": int(txn.amount * 100),
                        "speed": "optimum"
                    })

                    txn.status = 'refunded'
                    txn.refund_id = refund.get('id')
                    txn.refund_status = refund.get('status')
                    txn.save()

                    booking.status = 'cancelled'
                    booking.payment_status = 'refunded'
                    booking.save()

                    return Response({"message": f"Booking #{booking.id} refunded and cancelled."}, status=200)

            except razorpay.errors.BadRequestError as e:
                return Response({"error": f"Refund failed: {str(e)}"}, status=400)
            except Exception as e:
                return Response({"error": f"Unexpected error: {str(e)}"}, status=500)



        return Response({"error": "Booking cannot be cancelled at this stage."}, status=400)

# class CancelBookingView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, booking_id):
#         booking = get_object_or_404(
#             Booking, 
#             id=booking_id, 
#             user=request.user,
#             status='confirmed',
#             payment_status__in=['pending', 'failed']
#         )
        
#         # Update booking status
#         booking.status = 'cancelled'
#         booking.save()
        
#         # Find and update all pending transactions
#         Transaction.objects.filter(
#             booking=booking,
#             status='pending'
#         ).update(status='cancelled')
        
#         return Response({
#             "message": "Booking cancelled successfully",
#             "booking_id": booking.id
#         }, status=status.HTTP_200_OK)


# class RazorPayWebhookView(APIView):
#     # No authentication for webhooks coming from RazorPay
    
#     def post(self, request):
#         # Get webhook data
#         webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
#         webhook_signature = request.headers.get('X-Razorpay-Signature')
        
#         # Verify webhook signature
#         try:
#             # Verify webhook signature
#             razorpay_client.utility.verify_webhook_signature(
#                 request.body.decode('utf-8'), 
#                 webhook_signature, 
#                 webhook_secret
#             )
#         except Exception as e:
#             return Response({
#                 'error': 'Invalid webhook signature'
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#         # Process webhook data
#         webhook_data = request.data
#         event = webhook_data.get('event')
        
#         if event == 'payment.authorized':
#             # Payment was successful
#             payment_id = webhook_data['payload']['payment']['entity']['id']
#             order_id = webhook_data['payload']['payment']['entity']['order_id']
            
#             # Find related transaction
#             try:
#                 transaction = Transaction.objects.get(razorpay_order_id=order_id)
                
#                 # Update transaction
#                 transaction.razorpay_payment_id = payment_id
#                 transaction.status = 'completed'
#                 transaction.save()
                
#                 # Update booking or extension
#                 if transaction.booking:
#                     booking = transaction.booking
#                     booking.payment_status = 'paid'
#                     booking.save()
                    
#                     # Update partner wallet
#                     if booking.partner:
#                         partner_amount = booking.total_amount * Decimal('0.75')
#                         wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
#                         wallet.balance += partner_amount
#                         wallet.save()
                        
#                 elif transaction.extension:
#                     extension = transaction.extension
#                     extension.payment_status = 'paid'
#                     extension.save()
                    
#                     # Update booking hours
#                     booking = extension.booking
#                     booking.hours += extension.additional_hours
#                     booking.total_amount += extension.extension_amount
#                     booking.save()
                    
#                     # Update partner wallet
#                     if booking.partner:
#                         partner_amount = extension.extension_amount * Decimal('0.75')
#                         wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
#                         wallet.balance += partner_amount
#                         wallet.save()
                
#             except Transaction.DoesNotExist:
#                 pass  # Log this situation
                
#         elif event == 'payment.failed':
#             # Payment failed
#             payment_id = webhook_data['payload']['payment']['entity']['id']
#             order_id = webhook_data['payload']['payment']['entity']['order_id']
            
#             # Find related transaction
#             try:
#                 transaction = Transaction.objects.get(razorpay_order_id=order_id)
                
#                 # Update transaction
#                 transaction.razorpay_payment_id = payment_id
#                 transaction.status = 'failed'
#                 transaction.save()
                
#                 # Update booking or extension status
#                 if transaction.booking:
#                     transaction.booking.payment_status = 'failed'
#                     transaction.booking.save()
#                 elif transaction.extension:
#                     transaction.extension.payment_status = 'failed'
#                     transaction.extension.save()
                    
#             except Transaction.DoesNotExist:
#                 pass  # Log this situation
        
#         return Response({'status': 'success'}, status=status.HTTP_200_OK)


class RazorPayWebhookView(APIView):
    # No authentication for webhooks coming from RazorPay
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        # Get webhook data
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        # Verify webhook signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                request.body.decode('utf-8'), 
                webhook_signature, 
                webhook_secret
            )
        except Exception as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return Response({
                'error': 'Invalid webhook signature'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Process webhook data
        webhook_data = request.data
        event = webhook_data.get('event')
        
        logger.info(f"Processing webhook event: {event}")
        
        if event == 'payment.captured':
            # Payment was successful
            payment_id = webhook_data['payload']['payment']['entity']['id']
            order_id = webhook_data['payload']['payment']['entity']['order_id']
            
            # Find related transaction
            try:
                transaction = Transaction.objects.get(razorpay_order_id=order_id)
                
                # Idempotency check
                if transaction.status == 'completed':
                    logger.info(f"Payment already processed for order_id: {order_id}")
                    return Response({'status': 'success'}, status=status.HTTP_200_OK)
                
                # Use database transaction for atomicity
                from django.db import transaction as db_transaction
                with db_transaction.atomic():
                    # Update transaction
                    transaction.razorpay_payment_id = payment_id
                    transaction.status = 'completed'
                    transaction.save()
                    
                    # Update booking or extension
                    if transaction.booking:
                        booking = transaction.booking
                        booking.payment_status = 'paid'
                        booking.save()

                        try:
                            send_push_notification(
                                user=booking.user,
                                title="Booking Confirmed",
                                body="You have an active booking.",
                                data={"booking_id": str(booking.id), "status": booking.status}
                            )
                        except Exception as e:
                            logger.warning(f"Error sending active booking notification for booking #{booking.id}: {e}")
                        
                        # legacy
                        # Update partner wallet
                        # if booking.partner:
                        #     try:
                        #         partner_amount = booking.total_amount * Decimal('0.75')
                        #         wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
                        #         wallet.balance += partner_amount
                        #         wallet.save()
                        #     except Exception as e:
                        #         logger.error(f"Failed to update partner wallet: {str(e)}")
                        #         # Continue processing as this shouldn't fail the transaction
                                
                    elif transaction.extension:
                        extension = transaction.extension
                        extension.payment_status = 'paid'
                        extension.save()
                        
                        # Update booking hours
                        booking = extension.booking
                        booking.hours += extension.additional_hours
                        booking.total_amount += extension.extension_amount
                        booking.save()

                        try:
                            send_push_notification(
                                user=booking.user,
                                title="Booking Extended",
                                body=f"Extension confirmed with new hours ({booking.hours}).",
                                data={"booking_id": str(booking.id), "status": booking.status}
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send extension confirmation notification for booking #{booking.id}: {e}")

                        # legacy
                        # Update partner wallet 
                        # if booking.partner:
                        #     try:
                        #         partner_amount = extension.extension_amount * Decimal('0.75')
                        #         wallet, created = PartnerWallet.objects.get_or_create(partner=booking.partner)
                        #         wallet.balance += partner_amount
                        #         wallet.save()
                        #     except Exception as e:
                        #         logger.error(f"Failed to update partner wallet: {str(e)}")
                
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for order_id: {order_id}")

        elif event == 'payment.failed':
            # Payment failed
            payment_id = webhook_data['payload']['payment']['entity']['id']
            order_id = webhook_data['payload']['payment']['entity']['order_id']
            
            # Find related transaction
            try:
                transaction = Transaction.objects.get(razorpay_order_id=order_id)
                
                # Idempotency check
                if transaction.status == 'failed':
                    logger.info(f"Failed payment already processed for order_id: {order_id}")
                    return Response({'status': 'success'}, status=status.HTTP_200_OK)
                
                with db_transaction.atomic():
                    # Update transaction
                    transaction.razorpay_payment_id = payment_id
                    transaction.status = 'failed'
                    transaction.save()
                    
                    # Update booking or extension status
                    if transaction.booking:
                        transaction.booking.payment_status = 'failed'
                        transaction.booking.save()
                    elif transaction.extension:
                        transaction.extension.payment_status = 'failed'
                        transaction.extension.save()
                    
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for order_id: {order_id}")
        

        elif event == 'refund.processed':
            refund_data = webhook_data['payload']['refund']['entity']
            payment_id = refund_data['payment_id']
            refund_id = refund_data['id']
            amount = Decimal(refund_data['amount']) / 100

            try:
                txn = Transaction.objects.get(razorpay_payment_id=payment_id)

                if txn.status != 'refunded':
                    txn.status = 'refunded'
                    txn.save()

                    # Optional: update booking status too
                    if txn.booking:
                        booking = txn.booking
                        booking.status = 'cancelled'
                        booking.payment_status = 'refunded'
                        booking.save()

                    logger.info(f"Refund processed for txn {txn.id}, refund_id: {refund_id}")

            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for refund: payment_id={payment_id}")


        # Handle other events if needed
        else:
            logger.info(f"Unhandled webhook event: {event}")
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class CreateReviewView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]



    def post(self, request, booking_id):

        is_partner = self.request.auth.get('is_partner', False) if self.request.auth else False
        if is_partner:
            return Response({
                "error": "Partners cannot create user reviews."
            }, status=status.HTTP_403_FORBIDDEN)

        # Retrieve the booking object, ensure it is "completed"
        booking = get_object_or_404(
            Booking, 
            id=booking_id, 
            user=request.user,
            status='completed'
        )
        
        # Check if review already exists
        if hasattr(booking, 'review'):
            return Response({
                "error": "Review already exists for this booking."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Manually add the booking ID to request.data
        request.data['booking'] = booking.id  # Use booking.id instead of the entire object
        
        # Pass data to the serializer
        serializer = ReviewSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save the review
            review = serializer.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
