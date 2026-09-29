from django.contrib import admin
from .models import SeatReservation, Booking, BookingSeat


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    readonly_fields = ('seat', 'seat_code', 'seat_type', 'price')


@admin.register(SeatReservation)
class SeatReservationAdmin(admin.ModelAdmin):
    list_display = ('show', 'seat', 'user', 'session_key', 'status', 'reserved_at', 'expires_at')
    list_filter = ('status', 'show__show_date', 'show__screen__theater')
    search_fields = ('seat__seat_code', 'session_key', 'user__username', 'show__movie__title')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'user', 'show', 'final_amount', 'status', 'is_checked_in', 'created_at')
    list_filter = ('status', 'is_checked_in', 'created_at', 'show__show_date')
    search_fields = ('booking_id', 'user__username', 'show__movie__title')
    inlines = [BookingSeatInline]
    readonly_fields = ('verification_token', 'created_at', 'updated_at')
