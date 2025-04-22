# authentication/urls.py
from django.urls import path
from .views import RegisterView, LoginView, UserDetailView, RefreshTokenView, TestAuthView, SimpleUserView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('me/', UserDetailView.as_view(), name='user_detail'),
    # Add to authentication/urls.py
    path('test-auth/', TestAuthView.as_view(), name='test_auth'),
    # Add to authentication/urls.py
    path('simple-user/', SimpleUserView.as_view(), name='simple_user'),
]