# papers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from authentication import views
from .views import PaperViewSet, TestOllamaView, download_paper_pdf

router = DefaultRouter()
router.register(r'papers', PaperViewSet, basename='paper')

urlpatterns = [
    path('', include(router.urls)),
    path('api/test-ollama/', TestOllamaView.as_view(), name='test-ollama'),
    path('<str:paper_id>/download/', download_paper_pdf, name='download_paper_pdf')
]