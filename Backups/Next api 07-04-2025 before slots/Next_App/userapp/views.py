from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from authentication.models import (
    CustomUser, Partner, ServiceType, Booking, 
    BookingRequest, BookingExtension, Review
)
from authentication.serializers import (
    CustomUserSerializer, PartnerSerializer, ServiceTypeSerializer,
    BookingCreateSerializer, BookingDetailSerializer, BookingRequestSerializer,
    BookingExtensionSerializer, ReviewSerializer
)

# Common views for both partners and users
class UserHomeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Welcome to homepage",
            "user": request.user.full_name
        }, status=status.HTTP_200_OK)

class ServiceTypeListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer

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

# User views
class CreateBookingView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is not a partner
        if request.user.is_partner:
            return Response({
                "error": "Partners cannot make bookings."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get booking date based on type
        booking_data = request.data
        is_instant = booking_data.get("is_instant", True)

        if is_instant:
            booking_day = timezone.localdate()
        else:
            scheduled_date = booking_data.get("scheduled_date")
            if not scheduled_date:
                return Response({
                    "error": "Scheduled date is required for book later."
                }, status=status.HTTP_400_BAD_REQUEST)
            booking_day = scheduled_date

        # Check for existing same-day bookings by this user
        same_day_bookings = Booking.objects.filter(
            user=request.user,
            scheduled_date=booking_day
        )

        if same_day_bookings.count() >= 3:
            return Response({
                "error": "You already have 3 bookings on this day."
            }, status=status.HTTP_400_BAD_REQUEST)

        if same_day_bookings.exists():
            if not all(b.status == 'completed' and b.work_ended_at for b in same_day_bookings):
                return Response({
                    "error": "You already have a booking on this day that is not yet completed."
                }, status=status.HTTP_400_BAD_REQUEST)



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

class BookingAvailablePartnersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        # Get partners who have already accepted this booking
        partners = Partner.objects.filter(
            booking_requests__booking=booking,
            booking_requests__status='accepted',
            is_verified=True
        )
        
        # Filter partners based on verification and experience
        if booking.partner_type == 'trained':
            partners = partners.filter(experience__gte=2)
        else:
            partners = partners.filter(experience__lt=2)
        
        serializer = PartnerSerializer(partners, many=True)
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
        booking.save()
        
        # Return updated booking
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
        
        # Dummy payment processing
        booking.payment_status = 'paid'
        booking.save()
        
        return Response({
            "message": "Payment processed successfully",
            "booking_id": booking.id,
            "amount": booking.total_amount
        }, status=status.HTTP_200_OK)

class UserActiveBookingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.is_partner:
            return Response({
                "error": "Only users can access this endpoint."
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Active bookings are those that are confirmed, in progress, or scheduled for future
        active_bookings = Booking.objects.filter(
            user=request.user
        ).filter(
            Q(status='confirmed') | Q(status='in_progress')
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
        
        # Add the 'booking' object to the incoming request data
        request.data['booking'] = booking.id  # Use the booking's ID in the request data
        
        # Now the serializer can use this value in the validated data
        serializer = BookingExtensionSerializer(data=request.data)
        
        if serializer.is_valid():
            extension = serializer.save()  # Create and save the booking extension
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        
        # Dummy payment processing
        extension.payment_status = 'paid'
        extension.save()
        
        # Update booking hours
        booking = extension.booking
        booking.hours += extension.additional_hours
        booking.total_amount += extension.extension_amount
        booking.save()
        
        return Response({
            "message": "Extension payment processed successfully",
            "extension_id": extension.id,
            "amount": extension.extension_amount
        }, status=status.HTTP_200_OK)

class CreateReviewView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, booking_id):
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
