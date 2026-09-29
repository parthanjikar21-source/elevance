from django.contrib import admin
from .models import City, Theater, Screen, Seat, ShowSchedule


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fields = ('row_identifier', 'seat_number', 'seat_code', 'seat_type', 'price_multiplier', 'is_active')


class ScreenInline(admin.TabularInline):
    model = Screen
    extra = 1
    fields = ('name', 'screen_type', 'total_seats', 'rows_count', 'cols_count', 'is_active')


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'state')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'contact_number', 'is_active')
    list_filter = ('city', 'is_active')
    search_fields = ('name', 'address', 'landmark')
    inlines = [ScreenInline]


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'theater', 'screen_type', 'total_seats', 'is_active')
    list_filter = ('theater__city', 'screen_type', 'is_active')
    search_fields = ('name', 'theater__name')
    inlines = [SeatInline]


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_code', 'screen', 'seat_type', 'price_multiplier', 'is_active')
    list_filter = ('seat_type', 'is_active', 'screen__theater')
    search_fields = ('seat_code', 'screen__name', 'screen__theater__name')


@admin.register(ShowSchedule)
class ShowScheduleAdmin(admin.ModelAdmin):
    list_display = ('movie', 'screen', 'show_date', 'start_time', 'base_price', 'status')
    list_filter = ('status', 'show_date', 'screen__theater__city', 'screen__theater')
    search_fields = ('movie__title', 'screen__theater__name')
