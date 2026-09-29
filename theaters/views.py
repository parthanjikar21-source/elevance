from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Theater, City, ShowSchedule


def theater_list(request):
    city_id = request.session.get('selected_city_id')
    theaters = Theater.objects.filter(is_active=True).select_related('city')
    if city_id:
        theaters = theaters.filter(city_id=city_id)
    return render(request, 'theaters/theater_list.html', {'theaters': theaters})


def theater_detail(request, slug):
    theater = get_object_or_404(Theater.objects.select_related('city').prefetch_related('screens'), slug=slug)
    today = timezone.now().date()
    current_time = timezone.now().time()
    
    shows = ShowSchedule.objects.filter(
        screen__theater=theater,
        show_date__gte=today,
        status__in=['SCHEDULED', 'HOUSEFULL']
    ).select_related('movie', 'screen').order_by('show_date', 'start_time')
    
    return render(request, 'theaters/theater_detail.html', {'theater': theater, 'shows': shows})
