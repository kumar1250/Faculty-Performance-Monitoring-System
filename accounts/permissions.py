from rest_framework.permissions import BasePermission

from accounts.models import BlacklistedToken
from .token_jwt import decode_token, get_token_from_request
import jwt


def get_user_from_request(request):
    token = get_token_from_request(request)
    if token and BlacklistedToken.objects.filter(token=token).exists():
        return None
    elif token:
        try:
            user = decode_token(token)
            return user
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    return None


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user is not None
    
class IsPrincipal(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role'] == 'principal'

class IsDean(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role'] == 'dean'
    
class IsHOD(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role']=='hod'

class IsCommittee_Coordinator(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role'] == 'committee_coordinator'

class IsDepartment_Incharge(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role'] == 'department_incharge'

class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        user = get_user_from_request(request)
        return user and user['role'] == 'faculty'