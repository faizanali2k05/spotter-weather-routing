from django.urls import path
from routing.views import plan, geocode, health
urlpatterns=[path('api/health/',health),path('api/geocode/',geocode),path('api/plan/',plan)]
