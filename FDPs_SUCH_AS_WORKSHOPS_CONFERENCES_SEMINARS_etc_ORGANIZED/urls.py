from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseDone, FDPsOrganizedViewSet

router = DefaultRouter()
router.register(r'courses', CourseDone, basename='courses')
router.register(r'fdps', FDPsOrganizedViewSet, basename='fdps')

urlpatterns = [
    path('', include(router.urls)),
]