# # authentication/jwt_auth.py
# from rest_framework_simplejwt.authentication import JWTAuthentication
# from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
# from .utils import get_user_by_id

# class CustomJWTAuthentication(JWTAuthentication):
#     def get_user(self, validated_token):
#         """
#         Attempt to find and return a user using the given validated token.
#         """
#         try:
#             user_id = validated_token.get('user_id')
#         except KeyError:
#             raise InvalidToken('Token contained no recognizable user identification')

#         user = get_user_by_id(user_id)
        
#         if user is None:
#             raise AuthenticationFailed('User not found', code='user_not_found')
        
#         if not user.get('is_active', True):
#             raise AuthenticationFailed('User is inactive', code='user_inactive')
            
#         return user