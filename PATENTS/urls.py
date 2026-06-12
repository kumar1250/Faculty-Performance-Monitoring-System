from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatentViewSet

router = DefaultRouter()
router.register(r'', PatentViewSet, basename='patent')

urlpatterns = [
    path('', include(router.urls)),
]