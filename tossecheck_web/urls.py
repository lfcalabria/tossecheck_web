from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def home_redirect(request):
    return redirect("portal:login")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_redirect),
    path("portal/", include(("portal.urls", "portal"), namespace="portal")),
]