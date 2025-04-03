# URLs
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    LogoutView, 
    RegisterPartnerView, 
    RegisterUserView, 
    VerifyPartnerView, 
    VerifyUserView,
    UserLoginView,
    VerifyUserLoginView,
    PartnerLoginView,
    VerifyPartnerLoginView
)

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
    
    # Logout endpoint
    path('logout/', LogoutView.as_view(), name='logout'),
]