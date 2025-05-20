# examgenie/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/questions/', include('questions.urls')),
    path('api/papers/', include('papers.urls')),
    path('api/profiles/', include('profiles.urls')),
    path('api/', include('papers.urls')),
    path('api/syllabus/', include('syllabus.urls'))
]