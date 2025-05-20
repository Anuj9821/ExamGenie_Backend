from django.urls import path
from .views import upload_syllabus

urlpatterns = [
    path('upload-syllabus/', upload_syllabus, name='upload_syllabus'),
]
