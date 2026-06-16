from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FacultySummaryViewSet

router = DefaultRouter()
router.register(r'faculty-summary', FacultySummaryViewSet, basename='faculty-summary')

urlpatterns = [
    path('', include(router.urls)),
]
