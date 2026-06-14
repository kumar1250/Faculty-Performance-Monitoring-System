from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookPublicationViewSet

router = DefaultRouter()
router.register(r'book-publications', BookPublicationViewSet, basename='book-publication')

urlpatterns = [
    path('', include(router.urls)),
]