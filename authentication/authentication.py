# authentication/authentication.py
import traceback
import jwt
from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .utils import get_user_by_id
from .user_wrapper import AuthenticatedMongoUser

class MongoDBAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication backend for MongoDB users.
    """
    keyword = 'Bearer'
    
    def authenticate(self, request):
        try:
            auth = authentication.get_authorization_header(request).split()
            
            if not auth or auth[0].lower() != self.keyword.lower().encode():
                return None
            
            if len(auth) == 1:
                msg = _('Invalid token header. No credentials provided.')
                raise exceptions.AuthenticationFailed(msg)
            elif len(auth) > 2:
                msg = _('Invalid token header. Token string should not contain spaces.')
                raise exceptions.AuthenticationFailed(msg)
            
            try:
                token = auth[1].decode()
            except UnicodeError:
                msg = _('Invalid token header. Token string should not contain invalid characters.')
                raise exceptions.AuthenticationFailed(msg)
            
            return self.authenticate_credentials(token, request)
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            traceback.print_exc()
            raise exceptions.AuthenticationFailed(f"Authentication error: {str(e)}")
    
    def authenticate_credentials(self, token, request):
        try:
            # Print the token for debugging
            print(f"Authenticating token: {token[:10]}...")  # Print the first 10 characters of the token for visibility
            
            # Decode the JWT token
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Print the decoded payload for debugging
            print(f"Decoded payload: {payload}")
            
            user_id = payload.get('user_id')
            print(f"Decoded user_id: {user_id}")  # Print the user_id extracted from the token
            
            if not user_id:
                raise exceptions.AuthenticationFailed(_('Invalid token. No user_id found.'))
            
            # Get the user from MongoDB
            user = get_user_by_id(user_id)
            print(f"Found user in MongoDB: {user is not None}")  # Check if the user exists in MongoDB
            
            if not user:
                raise exceptions.AuthenticationFailed(_('User not found.'))
            
            # Wrap user dict to simulate Django User
            wrapped_user = AuthenticatedMongoUser(user)
            
            # Assign wrapped user to request.user
            request.user = wrapped_user
            request.user_id = user_id
            
            return (wrapped_user, token)
        
        except jwt.ExpiredSignatureError:
            print("Token expired")
            raise exceptions.AuthenticationFailed(_('Token expired.'))
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {str(e)}")
            raise exceptions.AuthenticationFailed(_('Invalid token.'))
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            traceback.print_exc()
            raise exceptions.AuthenticationFailed(f"Authentication error: {str(e)}")
