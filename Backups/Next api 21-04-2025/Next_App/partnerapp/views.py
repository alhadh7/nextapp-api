from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from authentication.serializers import BookingDetailSerializer, BookingExtensionSerializer, BookingRequestSerializer, ReviewSerializer, ServiceTypeSerializer
from authentication.models import (
    CustomUser, Partner, ServiceType, Booking, 
    BookingRequest, BookingExtension, Review
)

# Partner views
class PartnerHomeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if the user is a partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view this page."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Query the Partner model if the user is a partner
        try:
            partner = Partner.objects.get(id=request.user.id)
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the partner is verified
        if not partner.is_verified:
            return Response({
                "error": "Access denied. You must be a verified partner to view this page."
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            "message": "Welcome to Partner Home!",
            "partner_id": partner.id,
            "education": partner.education,
            "experience": partner.experience,
            "is_verified": partner.is_verified
        }, status=status.HTTP_200_OK)


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
        if user.is_partner:
            # Partner's booking history
            return Booking.objects.filter(partner=user, status__in=['completed', 'cancelled']).order_by('-created_at')
        else:
            # User's booking history
            return Booking.objects.filter(user=user, status__in=['completed', 'cancelled']).order_by('-created_at')



class BookingDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, booking_id):
        # Handle both user and partner access
        if request.user.is_partner:
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


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta, time
from authentication.models import Booking, BookingExtension, BookingRequest, PartnerSlot, Partner, Review, ServiceType

class BookSlotView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_partner:
            return Response({"error": "Only partners allowed."}, status=403)

        try:
            partner = Partner.objects.get(id=request.user.id)
        except Partner.DoesNotExist:
            return Response({"error": "Partner not found"}, status=404)

        if not partner.is_verified:
            return Response({"error": "Partner not verified."}, status=403)

        # Get date from query or default to today
        date_str = request.query_params.get('date')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
        else:
            date_obj = timezone.localdate()

        all_slots = []
        start_hour = 9
        end_hour = 22  # Exclusive

        now = timezone.localtime()
        for hour in range(start_hour, end_hour, 2):
            slot_start = time(hour, 0)
            slot_end = time(hour + 2, 0)

            # Skip past slots for today
            if date_obj == now.date() and slot_end <= now.time():
                continue

            # Check if partner already booked this slot
            already_booked = PartnerSlot.objects.filter(
                partner=partner,
                date=date_obj,
                start_time=slot_start,
                end_time=slot_end,
                is_active=True
            ).exists()

            if not already_booked:
                all_slots.append({
                    "start_time": slot_start.strftime("%H:%M"),
                    "end_time": slot_end.strftime("%H:%M")
                })

        return Response({
            "date": date_obj,
            "available_slots": all_slots
        })

    def post(self, request):
        if not request.user.is_partner:
            return Response({"error": "Only partners allowed."}, status=403)

        try:
            partner = Partner.objects.get(id=request.user.id)
        except Partner.DoesNotExist:
            return Response({"error": "Partner not found"}, status=404)

        if not partner.is_verified:
            return Response({"error": "Partner not verified."}, status=403)

        slots_data = request.data.get('slots')
        if not slots_data:
            # Legacy support for single slot
            slots_data = [{
                "date": request.data.get("date"),
                "start_time": request.data.get("start_time"),
                "end_time": request.data.get("end_time")
            }]

        created_slots = []
        failed_slots = []

        for slot in slots_data:
            try:
                date_obj = datetime.strptime(slot['date'], "%Y-%m-%d").date()
                start_time = datetime.strptime(slot['start_time'], "%H:%M").time()
                end_time = datetime.strptime(slot['end_time'], "%H:%M").time()

                now = timezone.localtime()
                if date_obj < now.date() or (date_obj == now.date() and end_time <= now.time()):
                    failed_slots.append({**slot, "error": "Cannot book past slots"})
                    continue

                # Check if already booked
                exists = PartnerSlot.objects.filter(
                    partner=partner,
                    date=date_obj,
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True
                ).exists()

                if exists:
                    failed_slots.append({**slot, "error": "Slot already booked"})
                    continue

                PartnerSlot.objects.create(
                    partner=partner,
                    date=date_obj,
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True
                )
                created_slots.append(slot)

            except Exception as e:
                failed_slots.append({**slot, "error": str(e)})

        return Response({
            "created": created_slots,
            "failed": failed_slots
        }, status=201 if created_slots else 400)



class AvailableBookingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view available bookings."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to view available bookings."
                }, status=status.HTTP_403_FORBIDDEN)

            # Auto-cancel expired unassigned bookings (older than 30 min)
            cutoff_time = timezone.now() - timedelta(minutes=30)
            expired_bookings = Booking.objects.filter(
                status='pending',
                partner__isnull=True,
                created_at__lte=cutoff_time
            )
            for booking in expired_bookings:
                booking.status = 'cancelled'
                booking.save()


            now = timezone.localtime()
            current_time = now.time()
            today = now.date()

            # Check if there's a currently active slot for this exact moment
            has_active_slot = PartnerSlot.objects.filter(
                partner=partner,
                is_active=True,
                date=today,
                start_time__lte=current_time,
                end_time__gte=current_time
            ).exists()

            if not has_active_slot:
                return Response({
                    "error": "You must have at least one active booked slot to access available bookings."
                }, status=status.HTTP_403_FORBIDDEN)
            # Determine partner type based on experience
            partner_type = 'trained' if int(partner.experience) >= 2 else 'regular'
            
            # Get pending bookings matching partner type with no partner assigned
            now = timezone.now()
            
            # For "Book Now" bookings
            instant_bookings = Booking.objects.filter(
                status='pending',
                partner_type=partner_type,
                is_instant=True,
                partner__isnull=True
            )
            
            # For "Book Later" bookings
            later_bookings = Booking.objects.filter(
                status='pending',
                partner_type=partner_type,
                is_instant=False,
                scheduled_date__gte=now.date(),
                partner__isnull=True
            )
            
            # Combine both types
            available_bookings = instant_bookings | later_bookings

            # Filter out bookings the partner shouldn't accept
            valid_bookings = []
            for booking in available_bookings:
                booking_day = booking.scheduled_date if not booking.is_instant else timezone.localdate()

                same_day_bookings = Booking.objects.filter(
                    partner=partner,
                    scheduled_date=booking_day
                )

                # Rule 1: Skip if active booking in progress
                if Booking.objects.filter(partner=partner, status='in_progress').exists():
                    continue

                # Rule 2: Allow max 2 per day if completed
                if same_day_bookings.count() >= 2:
                    continue

                if same_day_bookings.exists():
                    if not all(b.status == 'completed' and b.work_ended_at for b in same_day_bookings):
                        continue

                valid_bookings.append(booking)


            serializer = BookingDetailSerializer(available_bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class AcceptBookingView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can accept bookings."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to accept bookings."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get booking that matches partner type
            partner_type = 'trained' if int(partner.experience) >= 2 else 'regular'
            booking = get_object_or_404(
                Booking, 
                id=booking_id, 
                status='pending', 
                partner_type=partner_type,
                partner__isnull=True
            )
            # 🚫 Rule 1: Check for active work
            if Booking.objects.filter(partner=partner, status='in_progress').exists():
                return Response({
                    "error": "You have an active booking in progress. Complete it before accepting new ones."
                }, status=status.HTTP_400_BAD_REQUEST)

            # 🧠 Determine the day for the booking
            booking_day = booking.scheduled_date if not booking.is_instant else timezone.localdate()

            # 🔍 Check for same-day bookings
            same_day_bookings = Booking.objects.filter(
                partner=partner,
                scheduled_date=booking_day
            ).exclude(id=booking.id)

            if same_day_bookings.count() >= 3:
                return Response({
                    "error": "You already have 3 bookings on this day. Cannot accept more."
                }, status=status.HTTP_400_BAD_REQUEST)

            if same_day_bookings.exists():
                if not all(b.status == 'completed' and b.work_ended_at for b in same_day_bookings):
                    return Response({
                        "error": "You already have a booking on this day that is not completed. Wait until it's finished."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            # ✅ Safe to accept
            # Create a booking request from this partner
            booking_request, created = BookingRequest.objects.get_or_create(
                booking=booking,
                partner=partner,
                defaults={'status': 'accepted'}
            )
            
            if not created:
                # Update the status if it already exists
                booking_request.status = 'accepted'
                booking_request.save()
            
            serializer = BookingRequestSerializer(booking_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class PartnerActiveBookingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view active bookings."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to view active bookings."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get confirmed or in-progress bookings assigned to this partner
            # that have been paid
            active_bookings = Booking.objects.filter(
                partner=partner,
                payment_status='paid'
            ).filter(
                Q(status='confirmed') | Q(status='in_progress')
            )
            
            serializer = BookingDetailSerializer(active_bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class ToggleWorkStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can toggle work status."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to toggle work status."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get booking assigned to this partner
            booking = get_object_or_404(
                Booking, 
                id=booking_id, 
                partner=partner,
                payment_status='paid'  # Only allow if payment is complete
            )

            # ❌ Reject if booking is cancelled
            if booking.status == 'cancelled':
                return Response({
                    "error": "Cannot toggle work status for a cancelled booking."
                }, status=status.HTTP_400_BAD_REQUEST)


            # For "Book Later" bookings, check if the scheduled date is today or in the past
            if not booking.is_instant and booking.scheduled_date > timezone.now().date():
                return Response({
                    "error": "Cannot start work for future bookings. This booking is scheduled for " + 
                            str(booking.scheduled_date)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Toggle status based on current status
            if booking.status == 'confirmed':
                # Start work
                booking.status = 'in_progress'
                booking.work_started_at = timezone.now()
                booking.save()
                
                return Response({
                    "message": "Work started successfully",
                    "booking_id": booking.id,
                    "work_started_at": booking.work_started_at
                }, status=status.HTTP_200_OK)
                
            elif booking.status == 'in_progress':
                # End work
                booking.status = 'completed'
                booking.work_ended_at = timezone.now()
                booking.save()
                
                return Response({
                    "message": "Work completed successfully",
                    "booking_id": booking.id,
                    "work_ended_at": booking.work_ended_at
                }, status=status.HTTP_200_OK)
                
            else:
                return Response({
                    "error": f"Cannot toggle work status for booking with status '{booking.status}'"
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class RespondToExtensionRequestView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, extension_id):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can respond to extension requests."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to respond to extension requests."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get extension for a booking assigned to this partner
            extension = get_object_or_404(
                BookingExtension,
                id=extension_id,
                booking__partner=partner,
                status='pending'
            )
            
            # Get the response (approve/reject) from request data
            response = request.data.get('response', '').lower()
            
            if response not in ['approve', 'reject']:
                return Response({
                    "error": "Invalid response. Please use 'approve' or 'reject'."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update extension status
            extension.status = 'approved' if response == 'approve' else 'rejected'
            extension.save()
            
            serializer = BookingExtensionSerializer(extension)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class PartnerCompletedBookingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view completed bookings."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to view completed bookings."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get completed bookings assigned to this partner
            completed_bookings = Booking.objects.filter(
                partner=partner,
                status='completed'
            )
            
            serializer = BookingDetailSerializer(completed_bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

class PartnerReviewsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a verified partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view their reviews."
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            partner = Partner.objects.get(id=request.user.id)
            if not partner.is_verified:
                return Response({
                    "error": "Access denied. You must be a verified partner to view your reviews."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get reviews for bookings assigned to this partner
            reviews = Review.objects.filter(
                booking__partner=partner
            )
            
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)