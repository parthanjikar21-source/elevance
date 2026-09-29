from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'preferred_city', 'loyalty_points', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'preferred_city')
    fieldsets = UserAdmin.fieldsets + (
        ('Cineverse Profile', {'fields': ('phone_number', 'avatar', 'preferred_city', 'loyalty_points', 'bio')}),
    )
