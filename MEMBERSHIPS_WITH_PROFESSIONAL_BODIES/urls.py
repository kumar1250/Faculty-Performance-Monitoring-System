from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfessionalMembershipViewSet

router = DefaultRouter()
router.register(r'professional', ProfessionalMembershipViewSet, basename='professional-membership')

urlpatterns = [
    path('', include(router.urls)),
]