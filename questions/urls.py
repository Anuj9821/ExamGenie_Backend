from django.urls import path
from . import views
from .views import update_questions, check_pyq_overlap  


urlpatterns = [
    # ... other routes
    path('update/', views.update_questions, name='update_questions'),
    path("check-pyq-overlap/", views.check_pyq_overlap,name='check_pyq_overlap'), 
]
