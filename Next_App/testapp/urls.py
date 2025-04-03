
from django.urls import path

from . import views


urlpatterns = [
    path("user/home/", views.userhome.as_view(), name="userhome"),
    path("partner/home/", views.partnerhome.as_view(), name="partnerhome")

]
