from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResearchGuidanceViewSet

router = DefaultRouter()
router.register(r'research', ResearchGuidanceViewSet, basename='research')

urlpatterns = [
    path('', include(router.urls)),
]