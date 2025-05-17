# URLs
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from authentication.utilities.utils import SaveFCMTokenView


from .views import (
    LogoutView, 
    RegisterPartnerView, 
    RegisterUserView,
    UpdatePartnerView,
    UpdateUserView, 
    VerifyPartnerView, 
    VerifyUserView,
    UserLoginView,
    VerifyUserLoginView,
    PartnerLoginView,
    VerifyPartnerLoginView,
    RefreshTokenView
)
from rest_framework_simplejwt.views import TokenVerifyView

urlpatterns = [
    # Registration endpoints
    path('register/user/', RegisterUserView.as_view(), name='register_user'),
    path('verify/user/', VerifyUserView.as_view(), name='verify_user'),
    path('register/partner/', RegisterPartnerView.as_view(), name='register_partner'),
    path('verify/partner/', VerifyPartnerView.as_view(), name='verify_partner'),
    
    # Login endpoints
    path('login/user/', UserLoginView.as_view(), name='login_user'),
    path('verify/login/user/', VerifyUserLoginView.as_view(), name='verify_login_user'),
    path('login/partner/', PartnerLoginView.as_view(), name='login_partner'),
    path('verify/login/partner/', VerifyPartnerLoginView.as_view(), name='verify_login_partner'),

    # JWT token endpoints
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Logout endpoint
    path('logout/', LogoutView.as_view(), name='logout'),


    # path('users/update/', UpdateUserView.as_view(), name='update-user'),
    path('partners/update/', UpdatePartnerView.as_view(), name='update-partner'),


    path('save-fcm-token/', SaveFCMTokenView.as_view(), name='save-fcm-token'),

]