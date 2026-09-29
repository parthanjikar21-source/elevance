from django.urls import path
from . import views

app_name = 'theaters'

urlpatterns = [
    path('', views.theater_list, name='theater_list'),
    path('<slug:slug>/', views.theater_detail, name='theater_detail'),
]
