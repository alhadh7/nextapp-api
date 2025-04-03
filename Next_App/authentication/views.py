from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
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

from .models import OTP, Partner, CustomUser

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
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
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
            tokens = get_tokens_for_user(user)
            
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
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        full_name = request.data.get('full_name')
        education = request.data.get('education')
        medical_certificate = request.FILES.get('medical_certificate')

        retry_count = cache.get(f'otp_retry_{phone_number}', 0)
        if retry_count >= 3:
            return Response({'error': 'Maximum OTP retries reached. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        otp_response = send_otp_via_whatsapp(phone_number)
        print("OTP Response:", otp_response)  # Debugging

        if otp_response.get('responseCode') == 200:
            verification_id = otp_response['data']['verificationId']

            # Since we can't store the actual file in cache, we'll need to temporarily save it
            # and store the reference/path in the cache if a medical certificate was provided
            medical_certificate_ref = None
            if medical_certificate:
                # You might need to implement a temporary storage solution here
                # This is a placeholder for that logic
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                import os
                
                # Generate a unique temporary path
                temp_path = f'temp_medical_certificates/{phone_number}_{verification_id}_{os.path.basename(medical_certificate.name)}'
                path = default_storage.save(temp_path, ContentFile(medical_certificate.read()))
                medical_certificate_ref = path

            # Store partner registration data in cache with verification ID as part of the key
            partner_data = {
                'email': email,
                'full_name': full_name,
                'education': education,
                'medical_certificate_ref': medical_certificate_ref,  # Store the reference to the file
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
            email = partner_data.get('email', '')
            full_name = partner_data.get('full_name', '')
            education = partner_data.get('education', '')
            medical_certificate_ref = partner_data.get('medical_certificate_ref')
            
            # Check if user with this phone number already exists
            existing_user = CustomUser.objects.filter(phone_number=phone_number).first()
            
            if existing_user:
                # If it's already a partner, just update the fields
                if hasattr(existing_user, 'partner'):
                    partner = existing_user.partner
                    partner.education = education
                    
                    # Handle medical certificate if a reference was stored
                    if medical_certificate_ref:
                        from django.core.files.storage import default_storage
                        if default_storage.exists(medical_certificate_ref):
                            with default_storage.open(medical_certificate_ref) as f:
                                import os
                                filename = os.path.basename(medical_certificate_ref)
                                from django.core.files import File
                                partner.medical_certificate.save(filename, File(f), save=False)
                            default_storage.delete(medical_certificate_ref)
                    
                    partner.save()
                else:
                    # User exists but is not a partner, create partner profile
                    partner = Partner(
                        customuser_ptr=existing_user,
                        education=education,
                        is_partner=True
                    )
                    
                    # Handle medical certificate
                    if medical_certificate_ref:
                        from django.core.files.storage import default_storage
                        if default_storage.exists(medical_certificate_ref):
                            with default_storage.open(medical_certificate_ref) as f:
                                import os
                                filename = os.path.basename(medical_certificate_ref)
                                from django.core.files import File
                                partner.medical_certificate.save(filename, File(f), save=False)
                            default_storage.delete(medical_certificate_ref)
                    
                    # This approach might need adjustment based on Django version and exact model setup
                    partner.save_base(raw=True)
                    
                    # Update the user record to mark as partner
                    existing_user.is_partner = True
                    existing_user.save()

                user_to_token = partner if not existing_user else existing_user
            else:
                # Create a new partner/user
                partner = Partner.objects.create(
                    phone_number=phone_number,
                    email=email,
                    full_name=full_name,
                    education=education,
                    is_partner=True
                )
                
                # Handle medical certificate
                if medical_certificate_ref:
                    from django.core.files.storage import default_storage
                    if default_storage.exists(medical_certificate_ref):
                        with default_storage.open(medical_certificate_ref) as f:
                            import os
                            filename = os.path.basename(medical_certificate_ref)
                            from django.core.files import File
                            partner.medical_certificate.save(filename, File(f), save=True)
                        default_storage.delete(medical_certificate_ref)
                
                user_to_token = partner
            
            # Clean up cache
            cache.delete(f'partner_data_{phone_number}_{verification_id}')
            cache.delete(f'otp_retry_{phone_number}')
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(user_to_token)
            
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
        if user.is_partner and not isinstance(user, Partner):
            return Response({'error': 'Please use partner login'}, status=status.HTTP_400_BAD_REQUEST)
            
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
                tokens = get_tokens_for_user(user)
                
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
                tokens = get_tokens_for_user(partner)
                
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
class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)