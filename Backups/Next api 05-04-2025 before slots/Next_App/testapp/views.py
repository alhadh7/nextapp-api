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
from .serializers import (
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