from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework import status

class userhome(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Welcome to homepage", "user": request.user.full_name}, status=status.HTTP_200_OK)
    
class partnerhome(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        if not request.user.is_partner:
                    return Response({"error": "Access denied. Only partners can view this page."}, status=status.HTTP_403_FORBIDDEN)

        return Response({"message": "Welcome to Partner Home!", "partner_id": request.user.id}, status=status.HTTP_200_OK)
