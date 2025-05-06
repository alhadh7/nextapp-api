from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from pyfcm import FCMNotification
from .models import FCMToken

class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        if not token:
            return Response({'error': 'Token is required'}, status=400)

        # Save the FCM token to the database, or skip if it already exists
        FCMToken.objects.get_or_create(user=request.user, token=token)
        return Response({'message': 'Token saved'}, status=200)


# Updated FCM configuration
# Make sure to provide the correct path to your service account file and project ID
service_account_file = "lib/health-connect-app-8d8ea-firebase-adminsdk-fbsvc-5486840072.json"  # Update this path
project_id = "health-connect-app-8d8ea"  # Update this

# Initialize the FCM service with the new API format
push_service = FCMNotification(
    service_account_file=service_account_file,
    project_id=project_id
)

def send_push_notification(user, title, body, data=None):
    tokens = list(user.fcm_tokens.values_list('token', flat=True))
    if not tokens:
        return
    
    # For each token, send a notification
    for token in tokens:
        result = push_service.notify(
            fcm_token=token,
            notification_title=title,
            notification_body=body,
            data_payload=data or {}
        )
        
        # Check if there was an error with this token
        if result and isinstance(result, dict) and 'error' in result:
            error = result.get('error')
            if error in ['NotRegistered', 'InvalidRegistration']:
                FCMToken.objects.filter(token=token).delete()
