from django.urls import path
from routing.views import health, geocode, plan

urlpatterns = [
    path('api/health/', health, name='api_health'),
    path('api/geocode/', geocode, name='api_geocode'),
    path('api/plan/', plan, name='api_plan'),
]
