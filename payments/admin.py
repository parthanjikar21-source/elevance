from django.contrib import admin
from .models import PaymentTransaction, PaymentWebhookLog


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'booking', 'user', 'gateway', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'gateway', 'currency', 'created_at')
    search_fields = ('transaction_id', 'order_id', 'booking__booking_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('gateway', 'event_type', 'is_verified', 'processed', 'created_at')
    list_filter = ('gateway', 'is_verified', 'processed')
    search_fields = ('event_type',)
    readonly_fields = ('created_at',)
