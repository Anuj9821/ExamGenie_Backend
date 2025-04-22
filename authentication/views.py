# authentication/views.py
import jwt
import datetime
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer
from .utils import create_user, authenticate_user, get_user_by_id, update_user
import traceback 

class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user_data, error = create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                name=serializer.validated_data['name'],
                department=serializer.validated_data.get('department', ''),
                institution=serializer.validated_data.get('institution', ''),
                role=serializer.validated_data.get('role', 'teacher')
            )
            
            if error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create JWT token
            payload = {
                'user_id': user_data['_id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow()
            }

            # Print the payload for debugging
            print(f"Token payload: {payload}")

            access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            
            # Create refresh token
            refresh_payload = {
                'user_id': user_data['_id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
                'iat': datetime.datetime.utcnow()
            }
            
            refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
            
            return Response({
                'user': user_data,
                'access': access_token,
                'refresh': refresh_token,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user_data, error = authenticate_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            
            if error:
                return Response({'error': error}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Create JWT token
            payload = {
                'user_id': user_data['_id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow()
            }

            # Print the payload for debugging
            print(f"Token payload: {payload}")

            access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            
            # Create refresh token
            refresh_payload = {
                'user_id': user_data['_id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
                'iat': datetime.datetime.utcnow()
            }
            
            refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
            
            return Response({
                'user': user_data,
                'access': access_token,
                'refresh': refresh_token,
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Update this class in authentication/views.py
class UserDetailView(APIView):
    def get(self, request):
        try:
            # Print request info for debugging
            print(f"Request user: {request.user}")
            print(f"Request auth: {request.auth}")
            
            # Get user_id from authenticated user
            user_id = request.user.get('_id')
            if not user_id:
                return Response({'error': 'User ID not found in token'}, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"Looking up user with ID: {user_id}")
            user_data = get_user_by_id(user_id)
            
            if not user_data:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Convert user_data to a format that can be serialized
            serializable_user_data = {
                '_id': user_data.get('_id'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'department': user_data.get('department', ''),
                'institution': user_data.get('institution', ''),
                'role': user_data.get('role', ''),
                'date_joined': user_data.get('date_joined', datetime.datetime.now()).isoformat() if isinstance(user_data.get('date_joined'), datetime.datetime) else user_data.get('date_joined')
            }
            
            return Response(serializable_user_data)
        except Exception as e:
            # Print the full traceback for debugging
            print(f"Error in UserDetailView.get: {str(e)}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        try:
            user_id = request.user.get('_id')
            if not user_id:
                return Response({'error': 'User ID not found in token'}, status=status.HTTP_400_BAD_REQUEST)
                
            serializer = UserSerializer(data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_user = update_user(user_id, serializer.validated_data)
                
                if not updated_user:
                    return Response({'error': 'Failed to update user'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Convert updated_user to a format that can be serialized
                serializable_user_data = {
                    '_id': updated_user.get('_id'),
                    'email': updated_user.get('email'),
                    'name': updated_user.get('name'),
                    'department': updated_user.get('department', ''),
                    'institution': updated_user.get('institution', ''),
                    'role': updated_user.get('role', ''),
                    'date_joined': updated_user.get('date_joined', datetime.datetime.now()).isoformat() if isinstance(updated_user.get('date_joined'), datetime.datetime) else updated_user.get('date_joined')
                }
                
                return Response(serializable_user_data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Print the full traceback for debugging
            print(f"Error in UserDetailView.put: {str(e)}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
class RefreshTokenView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Decode the refresh token
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            # Get the user from MongoDB
            user_data = get_user_by_id(user_id)
            
            if not user_data:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Create new JWT token
            new_payload = {
                'user_id': user_data['_id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow()
            }
            
            access_token = jwt.encode(new_payload, settings.SECRET_KEY, algorithm='HS256')
            
            return Response({
                'access': access_token,
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Refresh token expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        
# Add this to authentication/views.py
class TestAuthView(APIView):
    def get(self, request):
        # This endpoint just returns the authenticated user's data
        return Response({
            'message': 'Authentication successful',
            'user': request.user
        })
        
# Add this to authentication/views.py
class SimpleUserView(APIView):
    def get(self, request):
        try:
            # Just return the raw user object from request.user
            return Response({
                'message': 'Authentication successful',
                'user_id': request.user.get('_id'),
                'email': request.user.get('email'),
                'name': request.user.get('name')
            })
        except Exception as e:
            print(f"Error in SimpleUserView: {str(e)}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)