from django.urls import path
from .views import StudentCounsellingViewSet

urlpatterns = [
    path('contribution/', StudentCounsellingViewSet.as_view({'post': 'create_contribution'}), name='counselling-create'),
    path('usercontributions/<str:register_no>/', StudentCounsellingViewSet.as_view({'get': 'user_contribution_list'}), name='counselling-user-list'),
    path('contributions/', StudentCounsellingViewSet.as_view({'get': 'contributions_list'}), name='counselling-list'),
    path('requests/', StudentCounsellingViewSet.as_view({'get': 'pending_list'}), name='counselling-pending'),
    path('<int:pk>/update/', StudentCounsellingViewSet.as_view({'put': 'update_contribution'}), name='counselling-update'),
    path('<int:pk>/approve/', StudentCounsellingViewSet.as_view({'post': 'approve_contribution'}), name='counselling-approve'),
    path('<int:pk>/delete/', StudentCounsellingViewSet.as_view({'delete': 'delete_contribution'}), name='counselling-delete'),
]