from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('export/revenue/', views.export_revenue_csv, name='export_revenue'),
    path('export/occupancy/', views.export_occupancy_csv, name='export_occupancy'),
    path('export/bookings/', views.export_bookings_csv, name='export_bookings'),
]
