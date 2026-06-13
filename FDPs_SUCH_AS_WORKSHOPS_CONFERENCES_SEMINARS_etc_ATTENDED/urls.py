# urls.py

from rest_framework.routers import DefaultRouter
from .views import FDPsAttendedViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'fdp', FDPsAttendedViewSet, basename='fdp')

urlpatterns = [
    path('', include(router.urls)),
]