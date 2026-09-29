from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('checkout/<str:booking_id>/', views.checkout_view, name='checkout'),
    path('razorpay/verify/', views.verify_razorpay_payment, name='verify_razorpay'),
    path('simulate/<str:booking_id>/', views.simulate_payment_action, name='simulate_action'),
    path('webhook/razorpay/', views.razorpay_webhook, name='razorpay_webhook'),
]
