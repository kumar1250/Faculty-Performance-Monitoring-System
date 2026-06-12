
# Create your views here.
from urllib import request

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, BlacklistedToken
from .serializers import UserSerializer, UserRegistrationSerializer,UserUpdateSerializer
from .permissions import IsAuthenticated, IsPrincipal, IsDean, IsHOD, IsCommittee_Coordinator, IsDepartment_Incharge, IsFaculty
from .token_jwt import create_token, decode_token, get_token_from_request
from django.contrib.auth.hashers import check_password
from rest_framework import status


class UserViewSet(ViewSet):

    @action(detail=False, methods=['post'],url_path='register')
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            role_points = {
            'principal': 10,
            'dean': 9,
            'hod': 8,
            'committee_coordinator': 7,
            'department_incharge': 6,
            'faculty': 0,
        }
            if serializer.data['role']in role_points:
                user = User.objects.get(id=serializer.data['id'])
                user.points = role_points[serializer.data['role']]
                user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'],url_path='login')
    def login(self, request):
        username = str(request.data.get('username'))
        password = request.data.get('password')
        try:
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(register_no=username)
            if check_password(password, user.password):
                token = create_token(user)
                return Response({'token': token}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'],url_path='details', permission_classes=[IsAuthenticated])
    def user_details(self, request):
        user = decode_token(get_token_from_request(request))
        if user:
            data = User.objects.get(id=user['user_id'])
            serializer = UserRegistrationSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], url_path='logout', permission_classes=[IsAuthenticated])
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            BlacklistedToken.objects.create(token=token)
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='list', permission_classes=[IsAuthenticated])
    def user_list(self, request):
        users = User.objects.all()
        serializer = UserRegistrationSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='delete', permission_classes=[IsAuthenticated])
    def delete_user(self, request, pk=None):
        user = decode_token(get_token_from_request(request))
        if user and user['role'] in ['principal', 'dean', 'hod']:
            try:
                user_to_delete = User.objects.get(id=pk)
                user_to_delete.delete()
                return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['patch'], url_path='updateuser', permission_classes=[IsAuthenticated])
    def update_user(self, request, pk=None):
        user = decode_token(get_token_from_request(request))
        
        if user and user['role'] in ['principal', 'dean', 'hod']:
            try:
                user_to_update = User.objects.get(id=pk)
                user_to_update_role = user_to_update.role
                serializer = UserUpdateSerializer(user_to_update, data=request.data,partial=True)
                if serializer.is_valid():
                    serializer.save()
                
                    role_points = {
                            'principal': 10,
                            'dean': 9,
                            'hod': 8,
                            'committee_coordinator': 7,
                            'department_incharge': 6,
                            'faculty': 0,
                            }
                    if serializer.data['role'] in role_points:
                        user_to_update.save()
                        new_role = serializer.validated_data.get('role', user_to_update_role)
                        user_to_update.points += role_points[new_role]
                        user_to_update.points -= role_points[user_to_update_role]
                        user_to_update.save()
                    return Response({"username": user_to_update.username,"email": user_to_update.email,"register_no": user_to_update.register_no,"role": user_to_update.role}, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)