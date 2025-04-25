# papers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaperViewSet, TestOllamaView

router = DefaultRouter()
router.register(r'papers', PaperViewSet, basename='paper')

urlpatterns = [
    path('', include(router.urls)),
    path('api/test-ollama/', TestOllamaView.as_view(), name='test-ollama'),
]