import jwt
from django.conf import settings
from datetime import datetime, timedelta
from .models import User

def create_token(user)->str:
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'department': user.department,
        'register_no': user.register_no,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

def decode_token(token:str)->dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return None
    
def get_token_from_request(request):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None