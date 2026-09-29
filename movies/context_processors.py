from theaters.models import City
from movies.models import Genre


def global_cinema_context(request):
    """
    Supplies cities, genres, and user location preferences to all templates.
    """
    cities = City.objects.filter(is_active=True).order_by('name')
    genres = Genre.objects.all().order_by('name')

    # Selected city logic (stored in session or user preference)
    selected_city_id = request.session.get('selected_city_id')
    selected_city = None

    if selected_city_id:
        selected_city = cities.filter(id=selected_city_id).first()

    if not selected_city and request.user.is_authenticated and request.user.preferred_city:
        selected_city = request.user.preferred_city

    if not selected_city and cities.exists():
        selected_city = cities.first()

    return {
        'global_cities': cities,
        'global_genres': genres,
        'current_city': selected_city,
    }
