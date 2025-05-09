from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
# from pyfcm import FCMNotification
from .models import FCMToken

# class SaveFCMTokenView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         token = request.data.get('fcm_token')
#         if not token:
#             return Response({'error': 'Token is required'}, status=400)

#         # Save the FCM token to the database, or skip if it already exists
#         FCMToken.objects.get_or_create(user=request.user, token=token)
#         return Response({'message': 'Token saved'}, status=200)

from django.db import IntegrityError

class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        if not token:
            return Response({'error': 'Token is required'}, status=400)

        try:
            # Attempt to get or create the token
            fcm_token, created = FCMToken.objects.get_or_create(user=request.user, token=token)
            print(f"Saving FCM token for user {request.user.id}: {token}")
            print(f"Current tokens: {FCMToken.objects.filter(user=request.user)}")

            if created:
                return Response({'message': 'Token saved'}, status=200)
            else:
                return Response({'message': 'Token already exists'}, status=200)
        except IntegrityError:
            # Handle case where duplicate key error occurs
            return Response({'error': 'Duplicate token entry'}, status=400)


# Updated FCM configuration
# Make sure to provide the correct path to your service account file and project ID
# service_account_file = "lib/health-connect-app-8d8ea-firebase-adminsdk-fbsvc-5486840072.json"  # Update this path
# project_id = "health-connect-app-8d8ea"  # Update this

# # Initialize the FCM service with the new API format
# push_service = FCMNotification(
#     service_account_file=service_account_file,
#     project_id=project_id
# )

# def send_push_notification(user, title, body, data=None):
#     tokens = list(user.fcm_tokens.values_list('token', flat=True))
#     if not tokens:
#         return
    
#     # For each token, send a notification
#     for token in tokens:
#         result = push_service.notify(
#             fcm_token=token,
#             notification_title=title,
#             notification_body=body,
#             data_payload=data or {}
#         )
        
#         # Check if there was an error with this token
#         if result and isinstance(result, dict) and 'error' in result:
#             error = result.get('error')
#             if error in ['NotRegistered', 'InvalidRegistration']:
#                 FCMToken.objects.filter(token=token).delete()


import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from .models import FCMToken  # Adjust this import if needed

# Initialize Firebase Admin SDK
cred_path = "lib/health-connect-app-8d8ea-firebase-adminsdk-fbsvc-5486840072.json"  # ✅ Update this
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to all valid FCM tokens for the user.
    Removes invalid or unregistered tokens from the database.
    """
    tokens = list(user.fcm_tokens.values_list('token', flat=True))
    if not tokens:
        print(f"⚠️ No tokens found for user {user}")
        return

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                token=token,
                data={str(k): str(v) for k, v in (data or {}).items()},
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            content_available=True
                        )
                    )
                )
            )
            response = messaging.send(message)
            print(f"✅ Sent to {token}: {response}")

        except FirebaseError as e:
            error_message = str(e)
            print(f"❌ Failed for token {token}: {error_message}")

            # Handle known invalid token cases
            if any(err in error_message.lower() for err in [
                "registration-token-not-registered",
                "invalid-registration-token"
            ]):
                print(f"🗑 Removing invalid token: {token}")
                FCMToken.objects.filter(token=token).delete()

        except Exception as e:
            # Catch any other unknown error
            print(f"❌ Unexpected error for token {token}: {e}")