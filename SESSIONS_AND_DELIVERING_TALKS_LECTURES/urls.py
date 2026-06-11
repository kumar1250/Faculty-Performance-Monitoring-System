from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChairingSessionViewSet

router = DefaultRouter()
router.register(r'chairing', ChairingSessionViewSet, basename='chairing')

urlpatterns = [
    path('', include(router.urls)),
]