
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
# from drf_yasg.views import get_schema_view
# from drf_yasg import openapi

# Define the schema view
# schema_view = get_schema_view(
#     openapi.Info(
#         title="Your API",
#         default_version='v1',
#         description="Your API documentation",
#         terms_of_service="https://www.google.com/policies/terms/",
#         contact=openapi.Contact(email="contact@yourapi.com"),
#         license=openapi.License(name="MIT License"),
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
# )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include('authentication.urls')),
    # path("test/", include('testapp.urls'))
    path("user/", include('userapp.urls')),
    path("partner/", include('partnerapp.urls')),

    # path('docs/', schema_view.with_ui('swagger', cache_timeout=0)),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
