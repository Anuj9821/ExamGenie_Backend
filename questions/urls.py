from django.urls import path
from . import views

urlpatterns = [
    # ... other routes
    path('update/', views.update_questions, name='update_questions'),
]
