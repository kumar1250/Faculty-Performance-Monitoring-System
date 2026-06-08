from rest_framework.routers import DefaultRouter
from .views import CourseDone
from django.urls import path, include


router = DefaultRouter()
router.register(r'course', CourseDone, basename='course')
urlpatterns = [
    path('', include(router.urls)),
]