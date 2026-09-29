from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('shows/<int:show_id>/seats/', views.seat_selection_view, name='seat_selection'),
    path('api/shows/<int:show_id>/availability/', views.check_seat_availability_api, name='check_availability'),
    path('shows/<int:show_id>/reserve/', views.reserve_seats_view, name='reserve_seats'),
    path('booking/<str:booking_id>/release/', views.modify_or_release_seats, name='modify_seats'),
    path('booking/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/<str:booking_id>/ticket/pdf/', views.download_ticket_pdf_view, name='download_ticket_pdf'),
    path('verify/<uuid:token>/', views.verify_ticket_view, name='verify_ticket'),
]
