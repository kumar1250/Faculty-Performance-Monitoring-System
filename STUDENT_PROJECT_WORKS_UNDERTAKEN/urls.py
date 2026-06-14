from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentProjectWorkViewSet

router = DefaultRouter()
router.register(r'studentproject', StudentProjectWorkViewSet, basename='studentproject')

urlpatterns = [
    path('', include(router.urls)),
]