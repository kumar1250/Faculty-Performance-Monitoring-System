from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectContributionViewSet

router = DefaultRouter()
router.register(r'learning-material', SubjectContributionViewSet, basename='subject')

urlpatterns = [
    path('', include(router.urls)),
]