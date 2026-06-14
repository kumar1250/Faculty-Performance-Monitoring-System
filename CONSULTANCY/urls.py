from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultancyViewSet

router = DefaultRouter()
router.register(r'', ConsultancyViewSet, basename='consultancy')

urlpatterns = [
    path('', include(router.urls)),
]