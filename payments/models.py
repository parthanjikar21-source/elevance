from django.db import models
from django.conf import settings


class PaymentTransaction(models.Model):
    GATEWAY_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('STRIPE', 'Stripe'),
        ('SIMULATION', 'Test Sandbox / Simulation'),
    ]

    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending Verification'),
        ('SUCCESS', 'Success / Paid'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled by User'),
        ('REFUNDED', 'Refunded'),
    ]

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='payments',
        db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='RAZORPAY')
    transaction_id = models.CharField(max_length=120, unique=True, db_index=True)
    order_id = models.CharField(max_length=120, blank=True, db_index=True)
    payment_id = models.CharField(max_length=120, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED', db_index=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_description = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_id} ({self.get_gateway_display()}) - {self.get_status_display()} ₹{self.amount}"


class PaymentWebhookLog(models.Model):
    gateway = models.CharField(max_length=20)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    is_verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.gateway} {self.event_type} - Verified:{self.is_verified} ({self.created_at})"
