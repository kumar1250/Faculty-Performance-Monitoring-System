from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentFeedbackPerformanceViewSet

router = DefaultRouter()
router.register(r'student-feedback', StudentFeedbackPerformanceViewSet, basename='student-feedback')

urlpatterns = [
    path('', include(router.urls)),
]