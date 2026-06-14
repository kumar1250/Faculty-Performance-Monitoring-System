from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JournalPublicationViewSet

router = DefaultRouter()
router.register(r'journalpublication', JournalPublicationViewSet, basename='journalpublication')

urlpatterns = [
    path('', include(router.urls)),
]