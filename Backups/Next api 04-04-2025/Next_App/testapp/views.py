from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from authentication.models import Partner



class userhome(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        
        print("Request Object:", request)  # Print the full request object
        print("User Object:", request.user)  # Print the user object
        print("User Data:", request.user.__dict__)  # Print user attributes if available
        print("User Token:", request.auth)  # Print the token payload
        
        return Response({
            "message": "Welcome to homepage", 
            "user": request.user.full_name
        }, status=status.HTTP_200_OK)
    


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from authentication.models import Partner  # Import the Partner model

class partnerhome(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Print the full request, user, and token for debugging purposes
        print("Request Object:", request)  
        print("User Object:", request.user)  # Print the user object
        print("User Data:", request.user.__dict__)  # Print user attributes if available
        print("User Token:", request.auth)  # Print the token payload

        # Check if the user is a partner
        if not request.user.is_partner:
            return Response({
                "error": "Access denied. Only partners can view this page."
            }, status=status.HTTP_403_FORBIDDEN)

        # Query the Partner model if the user is a partner
        try:
            partner = Partner.objects.get(id=request.user.id)
            print("User Education:", partner.education)  # Print education details if user is a Partner
        except Partner.DoesNotExist:
            return Response({
                "error": "Partner not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if the partner is verified
        if not hasattr(partner, 'is_verified') or not partner.is_verified:
            return Response({
                "error": "Access denied. You must be a verified partner to view this page."
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "message": "Welcome to Partner Home!", 
            "partner_id": partner.id,
            "education": partner.education 
        }, status=status.HTTP_200_OK)
