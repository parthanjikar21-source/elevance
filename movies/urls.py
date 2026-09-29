from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('movies/<slug:slug>/', views.movie_detail, name='movie_detail'),
    path('movies/<slug:slug>/review/', views.submit_or_edit_review, name='submit_review'),
    path('reviews/<int:review_id>/report/', views.report_review, name='report_review'),
]
