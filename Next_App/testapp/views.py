from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

class userhome(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        
        # print("Request Object:", request)  # Print the full request object
        # print("User Object:", request.user)  # Print the user object
        # print("User Data:", request.user.__dict__)  # Print user attributes if available
        # print("User Token:", request.auth)  # Print the token payload
        
        return Response({
            "message": "Welcome to homepage", 
            "user": request.user.full_name
        }, status=status.HTTP_200_OK)
    
class partnerhome(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a partner directly from token payload
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view this page."
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "message": "Welcome to Partner Home!", 
            "partner_id": request.user.id
        }, status=status.HTTP_200_OK)
