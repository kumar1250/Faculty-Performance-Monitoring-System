from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FundedProjectViewSet

router = DefaultRouter()
router.register(r'funded-projects', FundedProjectViewSet, basename='funded-project')

urlpatterns = [
    path('', include(router.urls)),
]