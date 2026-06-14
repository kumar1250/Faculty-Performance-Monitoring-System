from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FDPsOrganizedViewSet

router = DefaultRouter()
router.register(r'fdpso', FDPsOrganizedViewSet, basename='fdps')

urlpatterns = [
    path('', include(router.urls)),
]