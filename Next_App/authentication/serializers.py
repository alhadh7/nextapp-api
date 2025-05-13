from django.utils import timezone
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
        fields = [
            'id', 'phone_number', 'email', 'full_name', 'education', 'experience', 'is_verified',
            'secondary_phone_number', 'languages_known', 'dob', 'bank_username', 
            'bank_account_number', 'ifsc_code', 'address'
        ]
        read_only_fields = ['id', 'is_verified', 'phone_number']

class ServiceTypeSerializer(serializers.ModelSerializer):
    # Adding a custom field to remove underscores from the 'name' field for the serialized output
    name_no_underscore = serializers.SerializerMethodField()

    class Meta:
        model = ServiceType
        fields = '__all__'  # Keep all the model fields

    def get_name_no_underscore(self, obj):
        # Replace underscores with spaces in the 'name' field for display purposes
        return obj.name.replace("_", " ")

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'service_type', 'partner_type', 'is_instant', 'hours', 
            'scheduled_date', 'user_location', 'hospital_location',
            'notes' , 'long', 'lang','scheduled_time',
        ]
    
    def validate(self, data):
        # Validate that scheduled_date is provided for "Book Later"
        if not data.get('is_instant') and not data.get('scheduled_date'):
            raise serializers.ValidationError("Scheduled date is required for 'Book Later' bookings")
        if not data.get('is_instant') and not data.get('scheduled_time'):
            raise serializers.ValidationError("Scheduled time is required for 'Book Later' bookings")
        # Validate that hospital_location is provided for "Checkup Companion"
        service_type = data.get('service_type')
        if service_type and service_type.name == 'checkup_companion' and not data.get('hospital_location'):
            raise serializers.ValidationError("Hospital location is required for 'Checkup Companion' service")

        # Ensure that service_type and partner_type are provided
        if not data.get('service_type'):
            raise serializers.ValidationError("Service type is required.")
        
        if not data.get('partner_type'):
            raise serializers.ValidationError("Partner type is required.")

        return data
    
    def create(self, validated_data):
        # Set the user from the request
        user = self.context['request'].user
        validated_data['user'] = user
        
        if validated_data.get('is_instant', False):
            validated_data['scheduled_date'] = timezone.localdate()
            validated_data['scheduled_time'] = timezone.localtime().time()


        booking = Booking.objects.create(**validated_data)
        # Calculate the total amount
        booking.calculate_total_amount()
        booking.save()
        
        return booking


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

class BookingDetailSerializer(serializers.ModelSerializer):
    review = ReviewSerializer(required=False)
    service_type = ServiceTypeSerializer(read_only=True)
    partner = PartnerSerializer(read_only=True)
    extensions = BookingExtensionSerializer(many=True, read_only=True)

    reassignment_pending = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = [
            'user', 'status', 'work_started_at', 'work_ended_at',
            'total_amount', 'payment_status', 'review','cancellation_reason'
        ]

    def get_reassignment_pending(self, obj):
        return obj.status == 'pending' and obj.released_by is not None





# serializers.py
from rest_framework import serializers
from .models import Partner

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['bank_username', 'bank_account_number', 'ifsc_code']

from rest_framework import serializers
from .models import PartnerWallet, Partner

class WalletDetailsSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_payout_date = serializers.DateTimeField(allow_null=True)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)