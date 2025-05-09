from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.core.cache import cache
import random, urllib.parse, urllib.request
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import OTP, FCMToken, Partner, CustomUser

import requests

# Message Central Configuration
AUTH_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJDLTI0QzIxNzgxMEUwOTQ4MyIsImlhdCI6MTc0MzU4NTE1MiwiZXhwIjoxOTAxMjY1MTUyfQ.OEfoWGrxrsFfbX4rWGyME-T_meWSuAdVnsAO5l91oaLx3HbJxLvbqV5UqhLvg2-SfLxm_ZypWkK_JWIdNemP6g"
CUSTOMER_ID = "C-24C217810E09483"
BASE_URL = "https://cpaas.messagecentral.com/verification/v3"

# # Send OTP via Message Central
# def send_otp_via_whatsapp(phone_number):
#     url = f"{BASE_URL}/send?countryCode=91&customerId={CUSTOMER_ID}&flowType=WHATSAPP&mobileNumber={phone_number}"
#     headers = {'authToken': AUTH_TOKEN}
#     response = requests.post(url, headers=headers)
#     return response.json()

# # Verify OTP via Message Central
# def verify_otp_via_whatsapp(phone_number, verification_id, code):
#     url = f"{BASE_URL}/validateOtp?countryCode=91&mobileNumber={phone_number}&verificationId={verification_id}&customerId={CUSTOMER_ID}&code={code}"
#     print(url)
#     headers = {'authToken': AUTH_TOKEN}
#     response = requests.get(url, headers=headers)
#     return response.json()



# Add these functions at the top of your file after your imports
# Mock OTP functions that can be easily toggled

# Configuration flag to toggle between real and mock OTP
USE_MOCK_OTP = True  # Set to False to use real WhatsApp OTP

# Mock OTP functions
def send_mock_otp(phone_number):
    """Mock implementation for sending OTP"""
    return {
        'responseCode': 200,
        'data': {
            'verificationId': '1234'
        }
    }

def verify_mock_otp(phone_number, verification_id, code):
    """Mock implementation for verifying OTP"""
    if verification_id == '1234' and code == '6969':
        return {
            'responseCode': 200,
            'data': {
                'verificationStatus': 'VERIFICATION_COMPLETED'
            }
        }
    else:
        return {
            'responseCode': 702,
            'message': 'Wrong OTP provided. Please try again.'
        }

# Modified send and verify functions that toggle between real and mock
def send_otp_via_whatsapp(phone_number):
    if USE_MOCK_OTP:
        return send_mock_otp(phone_number)
    else:
        url = f"{BASE_URL}/send?countryCode=91&customerId={CUSTOMER_ID}&flowType=WHATSAPP&mobileNumber={phone_number}"
        headers = {'authToken': AUTH_TOKEN}
        response = requests.post(url, headers=headers)
        return response.json()

# Verify OTP via Message Central
def verify_otp_via_whatsapp(phone_number, verification_id, code):
    if USE_MOCK_OTP:
        return verify_mock_otp(phone_number, verification_id, code)
    else:
        url = f"{BASE_URL}/validateOtp?countryCode=91&mobileNumber={phone_number}&verificationId={verification_id}&customerId={CUSTOMER_ID}&code={code}"
        print(url)
        headers = {'authToken': AUTH_TOKEN}
        response = requests.get(url, headers=headers)
        return response.json()

# Get JWT tokens for a user
from rest_framework_simplejwt.tokens import RefreshToken

# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)

#     refresh['phone_number'] = user.phone_number
#     refresh['is_partner'] = user.is_partner


#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token),
#     }


def get_tokens_for_user(user, is_partner=False):
    refresh = RefreshToken.for_user(user)
    
    # Add custom claims to the token
    refresh['phone_number'] = user.phone_number
    refresh['is_partner'] = is_partner  # Use the provided is_partner value
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# Custom Throttling Class
class OTPThrottle(UserRateThrottle):
    rate = '2/min'  # Limit to 2 OTP requests per minute

# Register User API
class RegisterUserView(APIView):
    throttle_classes = [OTPThrottle]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        full_name = request.data.get('full_name')

        if CustomUser.objects.filter(email=email).exists():
            # If the email exists, return a response with an error message
            return JsonResponse({'message': 'This email already exists.'}, status=400)
        
        is_partner = request.data.get('is_partner', False)  # False means normal user, True means partner

        # Check if the phone number is already registered as a normal user
        if not is_partner:
            user_exists = CustomUser.objects.filter(phone_number=phone_number, is_partner=False).exists()
            if user_exists:
                return Response({"error": "A normal user with this phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
        retry_count = cache.get(f'otp_retry_{phone_number}', 0)
        if retry_count >= 3:
            return Response({'error': 'Maximum OTP retries reached. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        otp_response = send_otp_via_whatsapp(phone_number)
        print("OTP Response:", otp_response)  # Debugging

        if otp_response.get('responseCode') == 200:
            verification_id = otp_response['data']['verificationId']

            # Store user registration data in cache with verification ID as part of the key
            user_data = {
                'email': email,
                'full_name': full_name,
                'verification_id': verification_id,  # Store verification ID for additional security
                'timestamp': datetime.now().timestamp()  # Track when the request was made
            }
            cache.set(f'user_data_{phone_number}_{verification_id}', user_data, timeout=1800)
            print(user_data)
            # Increment retry count to prevent spam
            cache.set(f'otp_retry_{phone_number}', retry_count + 1, timeout=600)

            return Response({'message': 'OTP sent successfully', 'verification_id': verification_id}, status=status.HTTP_200_OK)

        return Response({'error': 'Failed to send OTP'}, status=status.HTTP_400_BAD_REQUEST)



# Verify OTP and Create User
class VerifyUserView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        verification_id = request.data.get('verification_id')
        code = request.data.get('otp')
        print(f"{phone_number} {verification_id} {code}")
        user_data = cache.get(f'user_data_{phone_number}_{verification_id}', {})
        if not user_data:
            return Response({'error': 'Registration session expired or invalid. Please register again.'}, 
                           status=status.HTTP_400_BAD_REQUEST)

        verification_response = verify_otp_via_whatsapp(phone_number, verification_id, code)
        print("Verification API Response:", verification_response)  # Debugging
        
        response_code = verification_response.get('responseCode')
        
        if response_code == 200 and verification_response.get('data') and verification_response['data'].get('verificationStatus') == 'VERIFICATION_COMPLETED':
            email = user_data.get('email', '')
            full_name = user_data.get('full_name', '')
            
            # Create or update user with complete information
            user, created = CustomUser.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    'email': email,
                    'full_name': full_name
                }
            )
            
            # Clean up cache
            cache.delete(f'user_data_{phone_number}_{verification_id}')
            cache.delete(f'otp_retry_{phone_number}')
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(user , is_partner = False)
            
            return Response(tokens, status=status.HTTP_200_OK)

        # Handle different response codes
        error_messages = {
            702: "Wrong OTP provided. Please try again.",
            703: "OTP already verified. Try logging in.",
            705: "OTP expired. Please request a new one.",
            505: "Invalid verification ID. Request OTP again.",
            700: "Verification failed. Please try again.",
            800: "Maximum OTP attempts reached. Try later.",
            400: "Bad request. Check the details provided.",
            500: "Server error. Please try again later."
        }
        
        error_message = error_messages.get(response_code, "OTP verification failed. Please try again.")

        return Response({'error': error_message, 'details': verification_response}, status=status.HTTP_400_BAD_REQUEST)





# Register Partner API
class RegisterPartnerView(APIView):
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        # Basic information
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        full_name = request.data.get('full_name')
        education = request.data.get('education')
        experience = request.data.get('experience')
        
        # New personal information fields
        dob = request.data.get('dob')
        languages_known = request.data.get('languages_known')
        secondary_phone_number = request.data.get('secondary_phone_number')
        address = request.data.get('address')
        
        # Bank details
        bank_username = request.data.get('bank_username')
        bank_account_number = request.data.get('bank_account_number')
        ifsc_code = request.data.get('ifsc_code')
        
        # Document files
        medical_certificate = request.FILES.get('medical_certificate')
        adhar_card_front = request.FILES.get('adhar_card_front')
        adhar_card_back = request.FILES.get('adhar_card_back')
        driving_license_front = request.FILES.get('driving_license_front')
        driving_license_back = request.FILES.get('driving_license_back')
        profile_picture = request.FILES.get('profile_picture')

        # Check if a user (either normal or partner) already exists with the same phone number
        user_exists = CustomUser.objects.filter(phone_number=phone_number, is_partner=True).exists()
        if user_exists:
            return Response({"error": "A partner with this phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)

        retry_count = cache.get(f'otp_retry_{phone_number}', 0)
        if retry_count >= 3:
            return Response({'error': 'Maximum OTP retries reached. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        otp_response = send_otp_via_whatsapp(phone_number)
        print("OTP Response:", otp_response)  # Debugging

        if otp_response.get('responseCode') == 200:
            verification_id = otp_response['data']['verificationId']

            # Since we can't store the actual files in cache, we'll need to temporarily save them
            # and store the references/paths in the cache
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import os
            
            # Helper function to save file temporarily
            def save_temp_file(file_obj, file_type):
                if not file_obj:
                    return None
                temp_path = f'temp_{file_type}/{phone_number}_{verification_id}_{os.path.basename(file_obj.name)}'
                path = default_storage.save(temp_path, ContentFile(file_obj.read()))
                return path
            
            # Save all files temporarily
            medical_certificate_ref = save_temp_file(medical_certificate, 'medical_certificates')
            adhar_card_front_ref = save_temp_file(adhar_card_front, 'adhar_front')
            adhar_card_back_ref = save_temp_file(adhar_card_back, 'adhar_back')
            driving_license_front_ref = save_temp_file(driving_license_front, 'license_front')
            driving_license_back_ref = save_temp_file(driving_license_back, 'license_back')
            profile_picture_ref = save_temp_file(profile_picture, 'profile_pictures')

            # Store partner registration data in cache with verification ID as part of the key
            partner_data = {
                # Basic information
                'email': email,
                'full_name': full_name,
                'education': education,
                'experience': experience,
                
                # New personal information fields
                'dob': dob,
                'languages_known': languages_known,
                'secondary_phone_number': secondary_phone_number,
                'address': address,
                
                # Bank details
                'bank_username': bank_username,
                'bank_account_number': bank_account_number,
                'ifsc_code': ifsc_code,
                
                # Document file references
                'medical_certificate_ref': medical_certificate_ref,
                'adhar_card_front_ref': adhar_card_front_ref,
                'adhar_card_back_ref': adhar_card_back_ref,
                'driving_license_front_ref': driving_license_front_ref,
                'driving_license_back_ref': driving_license_back_ref,
                'profile_picture_ref': profile_picture_ref,
                
                'verification_id': verification_id,
                'timestamp': datetime.now().timestamp()
            }
            cache.set(f'partner_data_{phone_number}_{verification_id}', partner_data, timeout=1800)

            # Increment retry count to prevent spam
            cache.set(f'otp_retry_{phone_number}', retry_count + 1, timeout=600)

            return Response({'message': 'OTP sent successfully', 'verification_id': verification_id}, status=status.HTTP_200_OK)

        return Response({'error': 'Failed to send OTP'}, status=status.HTTP_400_BAD_REQUEST)

# Verify OTP and Create Partner
class VerifyPartnerView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        verification_id = request.data.get('verification_id')
        code = request.data.get('otp')

        partner_data = cache.get(f'partner_data_{phone_number}_{verification_id}', {})
        if not partner_data:
            return Response({'error': 'Registration session expired or invalid. Please register again.'}, 
                           status=status.HTTP_400_BAD_REQUEST)

        verification_response = verify_otp_via_whatsapp(phone_number, verification_id, code)
        print("Verification API Response:", verification_response)  # Debugging
        
        response_code = verification_response.get('responseCode')
        
        if response_code == 200 and verification_response.get('data') and verification_response['data'].get('verificationStatus') == 'VERIFICATION_COMPLETED':
            # Extract all partner data
            email = partner_data.get('email', '')
            full_name = partner_data.get('full_name', '')
            education = partner_data.get('education', '')
            experience = partner_data.get('experience', '')
            
            # New personal information fields
            dob = partner_data.get('dob')
            languages_known = partner_data.get('languages_known')
            secondary_phone_number = partner_data.get('secondary_phone_number')
            address = partner_data.get('address')
            
            # Bank details
            bank_username = partner_data.get('bank_username')
            bank_account_number = partner_data.get('bank_account_number')
            ifsc_code = partner_data.get('ifsc_code')
            
            # Document file references
            medical_certificate_ref = partner_data.get('medical_certificate_ref')
            adhar_card_front_ref = partner_data.get('adhar_card_front_ref')
            adhar_card_back_ref = partner_data.get('adhar_card_back_ref')
            driving_license_front_ref = partner_data.get('driving_license_front_ref')
            driving_license_back_ref = partner_data.get('driving_license_back_ref')
            profile_picture_ref = partner_data.get('profile_picture_ref')
            
            # Helper function to save file from temporary storage to model field
            def save_file_to_model(model_instance, field_name, temp_file_ref):
                if not temp_file_ref:
                    return
                    
                from django.core.files.storage import default_storage
                from django.core.files import File
                import os
                
                if default_storage.exists(temp_file_ref):
                    with default_storage.open(temp_file_ref) as f:
                        filename = os.path.basename(temp_file_ref)
                        getattr(model_instance, field_name).save(filename, File(f), save=False)
                    default_storage.delete(temp_file_ref)
            
            # Check if user with this phone number already exists
            existing_user = CustomUser.objects.filter(phone_number=phone_number).first()
            
            if existing_user:
                # If it's already a partner, just update the fields
                if hasattr(existing_user, 'partner'):
                    partner = existing_user.partner
                    
                    # Update basic fields
                    partner.education = education
                    partner.experience = experience
                    
                    # Update new personal information fields
                    if dob:
                        partner.dob = dob
                    partner.languages_known = languages_known
                    partner.secondary_phone_number = secondary_phone_number
                    partner.address = address
                    
                    # Update bank details
                    partner.bank_username = bank_username
                    partner.bank_account_number = bank_account_number
                    partner.ifsc_code = ifsc_code
                    
                    # Handle document files
                    save_file_to_model(partner, 'medical_certificate', medical_certificate_ref)
                    save_file_to_model(partner, 'adhar_card_front', adhar_card_front_ref)
                    save_file_to_model(partner, 'adhar_card_back', adhar_card_back_ref)
                    save_file_to_model(partner, 'driving_license_front', driving_license_front_ref)
                    save_file_to_model(partner, 'driving_license_back', driving_license_back_ref)
                    save_file_to_model(partner, 'profile_picture', profile_picture_ref)
                    
                    partner.save()
                else:
                    # User exists but is not a partner, create partner profile
                    partner = Partner(
                        customuser_ptr=existing_user,
                        education=education,
                        experience=experience,
                        is_partner=True,
                        # New personal information fields
                        dob=dob if dob else None,
                        languages_known=languages_known,
                        secondary_phone_number=secondary_phone_number,
                        address=address,
                        # Bank details
                        bank_username=bank_username,
                        bank_account_number=bank_account_number,
                        ifsc_code=ifsc_code
                    )
                    
                    # Set a default hashed password
                    partner.set_password("defaultpassword123")  # Change this to a secure value
                    
                    # Save the partner first to be able to attach files
                    partner.save_base(raw=True)
                    
                    # Handle document files
                    save_file_to_model(partner, 'medical_certificate', medical_certificate_ref)
                    save_file_to_model(partner, 'adhar_card_front', adhar_card_front_ref)
                    save_file_to_model(partner, 'adhar_card_back', adhar_card_back_ref)
                    save_file_to_model(partner, 'driving_license_front', driving_license_front_ref)
                    save_file_to_model(partner, 'driving_license_back', driving_license_back_ref)
                    save_file_to_model(partner, 'profile_picture', profile_picture_ref)
                    
                    partner.save()
                    
                    # Update the user record to mark as partner
                    existing_user.is_partner = True
                    existing_user.save()

                user_to_token = partner if not existing_user else existing_user
            else:
                # Create a new partner/user with all fields
                partner = Partner(
                    phone_number=phone_number,
                    email=email,
                    full_name=full_name,
                    education=education,
                    experience=experience,
                    is_partner=True,
                    # New personal information fields
                    dob=dob if dob else None,
                    languages_known=languages_known,
                    secondary_phone_number=secondary_phone_number,
                    address=address,
                    # Bank details
                    bank_username=bank_username,
                    bank_account_number=bank_account_number,
                    ifsc_code=ifsc_code
                )

                # Set a default hashed password
                partner.set_password("defaultpassword123")  # Change this to a secure value

                # Save the partner first to be able to attach files
                partner.save()
                
                # Handle document files
                save_file_to_model(partner, 'medical_certificate', medical_certificate_ref)
                save_file_to_model(partner, 'adhar_card_front', adhar_card_front_ref)
                save_file_to_model(partner, 'adhar_card_back', adhar_card_back_ref)
                save_file_to_model(partner, 'driving_license_front', driving_license_front_ref)
                save_file_to_model(partner, 'driving_license_back', driving_license_back_ref)
                save_file_to_model(partner, 'profile_picture', profile_picture_ref)
            
            # Clean up cache
            cache.delete(f'partner_data_{phone_number}_{verification_id}')
            cache.delete(f'otp_retry_{phone_number}')
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(partner, is_partner=True)

            return Response(tokens, status=status.HTTP_200_OK)

        # Handle different response codes
        error_messages = {
            702: "Wrong OTP provided. Please try again.",
            703: "OTP already verified. Try logging in.",
            705: "OTP expired. Please request a new one.",
            505: "Invalid verification ID. Request OTP again.",
            700: "Verification failed. Please try again.",
            800: "Maximum OTP attempts reached. Try later.",
            400: "Bad request. Check the details provided.",
            500: "Server error. Please try again later."
        }
        
        error_message = error_messages.get(response_code, "OTP verification failed. Please try again.")
        
        return Response({'error': error_message, 'details': verification_response}, status=status.HTTP_400_BAD_REQUEST)

# User Login API
class UserLoginView(APIView):
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        
        # Check if user exists
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return Response({'error': 'No user found with this phone number'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if this is a partner trying to use the user login
        # if user.is_partner and not isinstance(user, Partner):
        #     return Response({'error': 'Please use partner login'}, status=status.HTTP_400_BAD_REQUEST)
            
        retry_count = cache.get(f'otp_retry_{phone_number}', 0)
        if retry_count >= 3:
            return Response({'error': 'Maximum OTP retries reached. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        otp_response = send_otp_via_whatsapp(phone_number)
        print("Login OTP Response:", otp_response)  # Debugging
        
        if otp_response.get('responseCode') == 200:
            verification_id = otp_response['data']['verificationId']
            
            # Store login attempt in cache
            login_data = {
                'user_id': user.id,
                'verification_id': verification_id,
                'timestamp': datetime.now().timestamp()
            }
            cache.set(f'login_data_{phone_number}_{verification_id}', login_data, timeout=1800)
            
            # Increment retry count
            cache.set(f'otp_retry_{phone_number}', retry_count + 1, timeout=600)
            
            return Response({'message': 'OTP sent successfully', 'verification_id': verification_id}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Failed to send OTP'}, status=status.HTTP_400_BAD_REQUEST)


# Verify User Login OTP
class VerifyUserLoginView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        verification_id = request.data.get('verification_id')
        code = request.data.get('otp')
        
        login_data = cache.get(f'login_data_{phone_number}_{verification_id}', {})
        if not login_data:
            return Response({'error': 'Login session expired or invalid. Please try again.'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        verification_response = verify_otp_via_whatsapp(phone_number, verification_id, code)
        print("Login Verification API Response:", verification_response)  # Debugging
        
        response_code = verification_response.get('responseCode')
        
        if response_code == 200 and verification_response.get('data') and verification_response['data'].get('verificationStatus') == 'VERIFICATION_COMPLETED':
            user_id = login_data.get('user_id')
            
            try:
                user = CustomUser.objects.get(id=user_id)
                
                # Clean up cache
                cache.delete(f'login_data_{phone_number}_{verification_id}')
                cache.delete(f'otp_retry_{phone_number}')
                
                # Generate JWT tokens
                tokens = get_tokens_for_user(user , is_partner = False)
                
                return Response(tokens, status=status.HTTP_200_OK)
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle different response codes
        error_messages = {
            702: "Wrong OTP provided. Please try again.",
            703: "OTP already verified. Try logging in.",
            705: "OTP expired. Please request a new one.",
            505: "Invalid verification ID. Request OTP again.",
            700: "Verification failed. Please try again.",
            800: "Maximum OTP attempts reached. Try later.",
            400: "Bad request. Check the details provided.",
            500: "Server error. Please try again later."
        }
        
        error_message = error_messages.get(response_code, "OTP verification failed. Please try again.")
        
        return Response({'error': error_message, 'details': verification_response}, status=status.HTTP_400_BAD_REQUEST)


# Partner Login API
class PartnerLoginView(APIView):
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        
        # Check if partner exists
        try:
            partner = Partner.objects.get(phone_number=phone_number)
        except Partner.DoesNotExist:
            return Response({'error': 'No partner found with this phone number'}, status=status.HTTP_404_NOT_FOUND)
        
        retry_count = cache.get(f'otp_retry_{phone_number}', 0)
        if retry_count >= 3:
            return Response({'error': 'Maximum OTP retries reached. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        otp_response = send_otp_via_whatsapp(phone_number)
        print("Partner Login OTP Response:", otp_response)  # Debugging
        
        if otp_response.get('responseCode') == 200:
            verification_id = otp_response['data']['verificationId']
            
            # Store login attempt in cache
            login_data = {
                'partner_id': partner.id,
                'verification_id': verification_id,
                'timestamp': datetime.now().timestamp()
            }
            cache.set(f'partner_login_data_{phone_number}_{verification_id}', login_data, timeout=1800)
            
            # Increment retry count
            cache.set(f'otp_retry_{phone_number}', retry_count + 1, timeout=600)
            
            return Response({'message': 'OTP sent successfully', 'verification_id': verification_id}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Failed to send OTP'}, status=status.HTTP_400_BAD_REQUEST)


# Verify Partner Login OTP
class VerifyPartnerLoginView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        verification_id = request.data.get('verification_id')
        code = request.data.get('otp')
        
        login_data = cache.get(f'partner_login_data_{phone_number}_{verification_id}', {})
        if not login_data:
            return Response({'error': 'Login session expired or invalid. Please try again.'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        verification_response = verify_otp_via_whatsapp(phone_number, verification_id, code)
        print("Partner Login Verification API Response:", verification_response)  # Debugging
        
        response_code = verification_response.get('responseCode')
        
        if response_code == 200 and verification_response.get('data') and verification_response['data'].get('verificationStatus') == 'VERIFICATION_COMPLETED':
            partner_id = login_data.get('partner_id')
            
            try:
                partner = Partner.objects.get(id=partner_id)
                
                # Clean up cache
                cache.delete(f'partner_login_data_{phone_number}_{verification_id}')
                cache.delete(f'otp_retry_{phone_number}')
                
                # Generate JWT tokens
                tokens = get_tokens_for_user(partner , is_partner = True)
                
                return Response(tokens, status=status.HTTP_200_OK)
            except Partner.DoesNotExist:
                return Response({'error': 'Partner not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle different response codes
        error_messages = {
            702: "Wrong OTP provided. Please try again.",
            703: "OTP already verified. Try logging in.",
            705: "OTP expired. Please request a new one.",
            505: "Invalid verification ID. Request OTP again.",
            700: "Verification failed. Please try again.",
            800: "Maximum OTP attempts reached. Try later.",
            400: "Bad request. Check the details provided.",
            500: "Server error. Please try again later."
        }
        
        error_message = error_messages.get(response_code, "OTP verification failed. Please try again.")
        
        return Response({'error': error_message, 'details': verification_response}, status=status.HTTP_400_BAD_REQUEST)


# Token Refresh View
class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            tokens = {
                'access': str(token.access_token),
                'refresh': str(token)
            }
            return Response(tokens, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


# Logout API
# class LogoutView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             refresh_token = request.data.get('refresh')
#             if refresh_token:
#                 token = RefreshToken(refresh_token)
#                 token.blacklist()
#                 return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
#         except TokenError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            fcm_token = request.data.get('fcm_token')  # 🆕 optional token from frontend

            # Blacklist refresh token
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            else:
                return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Remove FCM token from DB
            if fcm_token:
                FCMToken.objects.filter(user=request.user, token=fcm_token).delete()
                print(f"🗑️ Removed FCM token {fcm_token} for user {request.user.id}")

            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)




from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File
import os

from .models import CustomUser, Partner
from .serializers import CustomUserSerializer, PartnerSerializer

# Update User Details View
class UpdateUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        """
        Update user details excluding phone number
        """
        user = request.user
        
        # Exclude phone_number from updatable fields
        updatable_fields = ['email', 'full_name', 'user_address']
        
        # Create a data dict with only allowed fields
        data = {}
        for field in updatable_fields:
            if field in request.data:
                data[field] = request.data.get(field)
        
        serializer = CustomUserSerializer(user, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Update Partner Details View
class UpdatePartnerView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        """
        Update partner details excluding phone number
        """
        user = request.user
        
        # Ensure the user is a partner
        if not user.is_partner or not hasattr(user, 'partner'):
            return Response({"error": "You are not registered as a partner."}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        partner = get_object_or_404(Partner, pk=user.id)
        
        # Helper function to save file
        def save_file_to_model(model_instance, field_name, file_obj):
            if not file_obj:
                return
                
            # Delete old file if it exists
            old_file = getattr(model_instance, field_name)
            if old_file:
                try:
                    old_file_path = old_file.path
                    if default_storage.exists(old_file_path):
                        default_storage.delete(old_file_path)
                except:
                    pass  # If deletion fails, we still proceed
            
            # Save new file
            filename = os.path.basename(file_obj.name)
            getattr(model_instance, field_name).save(filename, file_obj, save=False)
        
        # Handle text fields
        updatable_fields = [
            'email', 'full_name', 'education', 'experience',
            'secondary_phone_number', 'languages_known', 'dob',
            'bank_username', 'bank_account_number', 'ifsc_code',
            'address'
        ]
        
        # Create a data dict with only allowed fields
        data = {}
        for field in updatable_fields:
            if field in request.data:
                data[field] = request.data.get(field)
        
        # Handle file fields separately
        file_fields = [
            'adhar_card_front', 'adhar_card_back',
            'driving_license_front', 'driving_license_back',
            'profile_picture', 'medical_certificate'
        ]
        
        for field in file_fields:
            file_obj = request.FILES.get(field)
            if file_obj:
                save_file_to_model(partner, field, file_obj)
        
        # Apply text fields with serializer
        serializer = PartnerSerializer(partner, data=data, partial=True)
        
        if serializer.is_valid():
            # Save changes from serializer
            updated_partner = serializer.save()
            
            # Return updated data
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

