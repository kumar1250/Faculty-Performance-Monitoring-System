from rest_framework.routers import DefaultRouter
from .views import UserViewSet ,ProfileViewSet
from django.urls import path, include
router = DefaultRouter()
router.register(r'user', UserViewSet, basename='user')
router.register(r'profiles', ProfileViewSet, basename='profile')
urlpatterns = [
    path('', include(router.urls)),
]