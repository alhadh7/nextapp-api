from rest_framework import serializers
from authentication.models import CustomUser, Partner, ServiceType, Booking, BookingRequest, BookingExtension, Review

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'full_name', 'is_partner']
        read_only_fields = ['id', 'is_partner']

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['id', 'phone_number', 'email', 'full_name', 'education', 'experience', 'is_verified']
        read_only_fields = ['id', 'is_verified']

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = '__all__'

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'service_type', 'partner_type', 'is_instant', 'hours', 
            'scheduled_date', 'user_location', 'hospital_location'
        ]
    
    def validate(self, data):
        # Validate that scheduled_date is provided for "Book Later"
        if not data.get('is_instant') and not data.get('scheduled_date'):
            raise serializers.ValidationError("Scheduled date is required for 'Book Later' bookings")
        
        # Validate that hospital_location is provided for "Checkup Companion"
        service_type = data.get('service_type')
        if service_type and service_type.name == 'checkup_companion' and not data.get('hospital_location'):
            raise serializers.ValidationError("Hospital location is required for 'Checkup Companion' service")
            
        return data
    
    def create(self, validated_data):
        # Set the user from the request
        user = self.context['request'].user
        validated_data['user'] = user
        
        booking = Booking.objects.create(**validated_data)
        # Calculate the total amount
        booking.calculate_total_amount()
        booking.save()
        
        return booking

class BookingDetailSerializer(serializers.ModelSerializer):
    service_type = ServiceTypeSerializer(read_only=True)
    partner = PartnerSerializer(read_only=True)
    
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user', 'status', 'work_started_at', 'work_ended_at', 'total_amount', 'payment_status']

class BookingRequestSerializer(serializers.ModelSerializer):
    partner = PartnerSerializer(read_only=True)
    
    class Meta:
        model = BookingRequest
        fields = ['id', 'booking', 'partner', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

# class BookingExtensionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = BookingExtension
#         fields = ['id', 'booking', 'additional_hours', 'status', 'requested_at', 'extension_amount', 'payment_status']
#         read_only_fields = ['id', 'status', 'requested_at', 'extension_amount', 'payment_status']
    
#     def create(self, validated_data):
#         booking = validated_data['booking']
#         additional_hours = validated_data['additional_hours']
        
#         # Calculate extension amount
#         base_rate = booking.service_type.base_hourly_rate
#         rate_multiplier = 1.5 if booking.partner_type == 'trained' else 1.0
#         extension_amount = base_rate * rate_multiplier * additional_hours
        
#         validated_data['extension_amount'] = extension_amount
#         return super().create(validated_data)

from decimal import Decimal

class BookingExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingExtension
        fields = ['id', 'booking', 'additional_hours', 'status', 'requested_at', 'extension_amount', 'payment_status']
        read_only_fields = ['id', 'status', 'requested_at', 'extension_amount', 'payment_status']
    
    def create(self, validated_data):
        # Automatically handle the booking and additional_hours here
        booking = validated_data['booking']
        additional_hours = validated_data['additional_hours']
        
        # Convert base_rate, rate_multiplier, and additional_hours to Decimal for safe calculation
        base_rate = booking.service_type.base_hourly_rate  # Already a Decimal
        rate_multiplier = Decimal(1.5) if booking.partner_type == 'trained' else Decimal(1.0)  # Convert to Decimal
        additional_hours = Decimal(additional_hours)  # Convert additional_hours to Decimal

        # Calculate extension amount
        extension_amount = base_rate * rate_multiplier * additional_hours
        
        validated_data['extension_amount'] = extension_amount
        
        # Call the parent create method to actually save the object
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def create(self, validated_data):
        # No need to access booking from context, it's now in validated_data
        booking = validated_data['booking']
        validated_data['booking'] = booking  # This is redundant but explicit for clarity

        # Create and return the review
        return super().create(validated_data)


