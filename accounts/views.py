from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileUpdateForm
from theaters.models import City
from bookings.models import Booking


def register_view(request):
    if request.user.is_authenticated:
        return redirect('movies:movie_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Cineverse, {user.first_name or user.username}! Your account has been created.")
            return redirect('movies:movie_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('movies:movie_list')

    next_url = request.GET.get('next', 'movies:movie_list')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(request.POST.get('next') or 'movies:movie_list')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('movies:movie_list')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = UserProfileUpdateForm(instance=user)

    # User bookings and payment history
    bookings = Booking.objects.filter(user=user).select_related(
        'show__movie', 'show__screen__theater__city'
    ).prefetch_related('booked_seats', 'payments').order_by('-created_at')

    context = {
        'form': form,
        'bookings': bookings,
        'user': user,
    }
    return render(request, 'accounts/profile.html', context)


def set_preferred_city_view(request):
    city_id = request.POST.get('city_id') or request.GET.get('city_id')
    if city_id:
        city = City.objects.filter(id=city_id, is_active=True).first()
        if city:
            request.session['selected_city_id'] = city.id
            if request.user.is_authenticated:
                request.user.preferred_city = city
                request.user.save(update_fields=['preferred_city'])
            messages.success(request, f"City switched to {city.name}")
    
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)
