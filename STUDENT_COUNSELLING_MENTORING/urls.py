from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentCounsellingViewSet

router = DefaultRouter()
router.register(r'counselling', StudentCounsellingViewSet, basename='counselling')

urlpatterns = [
    path('', include(router.urls)),
]