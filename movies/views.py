from datetime import datetime, time, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count, Min, Case, When, IntegerField
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from .models import Movie, Genre, Language, Review, ReviewReport, UserRecentlyViewed
from .forms import ReviewForm, ReviewReportForm
from theaters.models import City, Theater, ShowSchedule
from bookings.models import Booking


def movie_list(request):
    """
    Movie Discovery Engine:
    - Search by title, description, cast member
    - Filters: genre, language, city, theater, release date/status, rating, show timings
    - Sort: popularity, newest, rating, price
    - Dynamic matching count & pagination
    - "Recommended for You" section based on user booking history and viewed movies
    """
    queryset = Movie.objects.prefetch_related('genres', 'languages').all()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(cast_members__name__icontains=q)
        ).distinct()

    # Genre filter
    genre_slug = request.GET.get('genre', '').strip()
    if genre_slug:
        queryset = queryset.filter(genres__slug=genre_slug)

    # Language filter
    lang_code = request.GET.get('language', '').strip()
    if lang_code:
        queryset = queryset.filter(languages__code=lang_code)

    # City filter (shows running in theaters of this city)
    city_id = request.GET.get('city', '').strip() or request.session.get('selected_city_id')
    if city_id:
        queryset = queryset.filter(shows__screen__theater__city_id=city_id).distinct()

    # Theater filter
    theater_id = request.GET.get('theater', '').strip()
    if theater_id:
        queryset = queryset.filter(shows__screen__theater_id=theater_id).distinct()

    # Status / Release Date filter
    status = request.GET.get('status', '').strip()
    if status in ['NOW_SHOWING', 'COMING_SOON']:
        queryset = queryset.filter(status=status)

    # Minimum Rating filter
    min_rating = request.GET.get('rating', '').strip()
    if min_rating:
        try:
            queryset = queryset.filter(average_rating__gte=float(min_rating))
        except ValueError:
            pass

    # Show timing filter
    timing = request.GET.get('timing', '').strip()
    now_date = timezone.now().date()
    if timing:
        if timing == 'morning':
            queryset = queryset.filter(
                shows__show_date__gte=now_date,
                shows__start_time__gte=time(6, 0),
                shows__start_time__lt=time(12, 0)
            ).distinct()
        elif timing == 'afternoon':
            queryset = queryset.filter(
                shows__show_date__gte=now_date,
                shows__start_time__gte=time(12, 0),
                shows__start_time__lt=time(17, 0)
            ).distinct()
        elif timing == 'evening':
            queryset = queryset.filter(
                shows__show_date__gte=now_date,
                shows__start_time__gte=time(17, 0),
                shows__start_time__lt=time(21, 0)
            ).distinct()
        elif timing == 'night':
            queryset = queryset.filter(
                shows__show_date__gte=now_date,
                shows__start_time__gte=time(21, 0)
            ).distinct()

    # Annotate min ticket price for sorting if requested
    sort = request.GET.get('sort', 'newest').strip()
    if sort == 'price':
        queryset = queryset.annotate(min_price=Min('shows__base_price')).order_by('min_price')
    elif sort == 'popularity':
        queryset = queryset.order_by('-is_trending', '-total_reviews', '-average_rating')
    elif sort == 'rating':
        queryset = queryset.order_by('-average_rating', '-total_reviews')
    else:  # 'newest'
        queryset = queryset.order_by('-release_date', '-id')

    total_matching_movies = queryset.count()

    # Pagination: 8 movies per page
    paginator = Paginator(queryset, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # "Recommended for You" engine
    recommendations = []
    if request.user.is_authenticated:
        # 1. Inspect user's confirmed bookings to get preferred genres & languages
        booked_movie_ids = Booking.objects.filter(
            user=request.user,
            status='CONFIRMED'
        ).values_list('show__movie_id', flat=True)

        fav_genres = Genre.objects.filter(movies__id__in=booked_movie_ids).annotate(
            count=Count('id')
        ).order_by('-count')[:3]

        if fav_genres.exists():
            recommendations = Movie.objects.filter(
                genres__in=fav_genres,
                status='NOW_SHOWING'
            ).exclude(
                id__in=booked_movie_ids
            ).distinct().order_by('-average_rating', '-is_trending')[:6]

    if not recommendations:
        # Check recently viewed movies in session or table
        if request.user.is_authenticated:
            viewed_genres = Genre.objects.filter(
                movies__recently_viewed_by__user=request.user
            ).distinct()
        else:
            session_key = request.session.session_key
            viewed_genres = Genre.objects.filter(
                movies__recently_viewed_by__session_key=session_key
            ).distinct()

        if viewed_genres.exists():
            recommendations = Movie.objects.filter(
                genres__in=viewed_genres,
                status='NOW_SHOWING'
            ).distinct().order_by('-average_rating')[:6]

    if not recommendations:
        # Fallback to trending and highest rated movies
        recommendations = Movie.objects.filter(status='NOW_SHOWING').order_by('-is_trending', '-average_rating')[:6]

    # Additional dropdown filter options
    theaters = Theater.objects.filter(is_active=True).order_by('name')
    languages = Language.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'total_matching_movies': total_matching_movies,
        'recommendations': recommendations,
        'theaters': theaters,
        'languages': languages,
        'selected_genre': genre_slug,
        'selected_language': lang_code,
        'selected_theater': theater_id,
        'selected_city': city_id,
        'selected_status': status,
        'selected_rating': min_rating,
        'selected_timing': timing,
        'selected_sort': sort,
        'search_query': q,
    }
    return render(request, 'movies/movie_list.html', context)


def movie_detail(request, slug):
    """
    Movie Details Page:
    - Secure YouTube trailer embedding
    - Multiple poster images gallery
    - Detailed description, age certification, duration
    - Show schedules by theater, screen, and dates
    - Verified Viewer reviews & ratings
    - Report inappropriate review modal
    - Similar movies based on genre and language
    - Trending & recently released recommendations
    """
    movie = get_object_or_404(
        Movie.objects.prefetch_related(
            'genres', 'languages', 'movie_cast_entries__cast_member',
            'additional_posters'
        ),
        slug=slug
    )

    # Record recently viewed
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    UserRecentlyViewed.objects.update_or_create(
        user=request.user if request.user.is_authenticated else None,
        session_key=session_key if not request.user.is_authenticated else '',
        movie=movie,
        defaults={'viewed_at': timezone.now()}
    )

    # Date filter for showtimes (Default: today)
    selected_date_str = request.GET.get('date')
    today = timezone.now().date()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # Next 5 days for date tabs
    date_tabs = [today + timedelta(days=i) for i in range(5)]

    # Fetch shows for selected date in selected city
    city_id = request.session.get('selected_city_id')
    shows_qs = ShowSchedule.objects.filter(
        movie=movie,
        show_date=selected_date,
        status__in=['SCHEDULED', 'HOUSEFULL']
    ).select_related('screen__theater__city', 'screen')

    if city_id:
        shows_qs = shows_qs.filter(screen__theater__city_id=city_id)

    # If it's today, exclude past shows
    if selected_date == today:
        current_time = timezone.now().time()
        shows_qs = shows_qs.filter(start_time__gte=current_time)

    shows_qs = shows_qs.order_by('screen__theater__name', 'start_time')

    # Group shows by theater
    theater_shows = {}
    for show in shows_qs:
        th = show.screen.theater
        if th not in theater_shows:
            theater_shows[th] = []
        theater_shows[th].append(show)

    # Similar movies based on genre and language
    similar_movies = Movie.objects.filter(
        Q(genres__in=movie.genres.all()) | Q(languages__in=movie.languages.all())
    ).exclude(id=movie.id).distinct().order_by('-average_rating')[:6]

    # Trending & Recently Released
    trending_movies = Movie.objects.filter(is_trending=True).exclude(id=movie.id)[:5]
    recent_releases = Movie.objects.filter(status='NOW_SHOWING').exclude(id=movie.id).order_by('-release_date')[:5]

    # Reviews & Verification check
    reviews = movie.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')

    user_has_watched = False
    existing_user_review = None
    if request.user.is_authenticated:
        user_has_watched = request.user.has_watched_movie(movie)
        existing_user_review = movie.reviews.filter(user=request.user).first()

    review_form = ReviewForm(instance=existing_user_review) if user_has_watched else None
    report_form = ReviewReportForm()

    context = {
        'movie': movie,
        'theater_shows': theater_shows,
        'date_tabs': date_tabs,
        'selected_date': selected_date,
        'similar_movies': similar_movies,
        'trending_movies': trending_movies,
        'recent_releases': recent_releases,
        'reviews': reviews,
        'user_has_watched': user_has_watched,
        'existing_user_review': existing_user_review,
        'review_form': review_form,
        'report_form': report_form,
    }
    return render(request, 'movies/movie_detail.html', context)


@login_required
def submit_or_edit_review(request, slug):
    """
    Submits or updates a rating and review for a movie.
    Enforces strict verified viewer requirement: user must have booked and watched!
    """
    movie = get_object_or_404(Movie, slug=slug)

    # Strict verification rule:
    if not request.user.has_watched_movie(movie):
        messages.error(request, "Only verified viewers who booked tickets and watched this movie can submit a review.")
        return redirect('movies:movie_detail', slug=movie.slug)

    existing_review = Review.objects.filter(movie=movie, user=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.movie = movie
            review.user = request.user
            review.is_verified_viewer = True  # Confirmed by user.has_watched_movie check
            review.save()

            action_text = "updated" if existing_review else "published"
            messages.success(request, f"Your verified review has been {action_text} successfully!")
        else:
            messages.error(request, "Please check your rating and review content.")

    return redirect('movies:movie_detail', slug=movie.slug)


@login_required
def report_review(request, review_id):
    """
    Allows registered users to report inappropriate review content.
    """
    review = get_object_or_404(Review, id=review_id)
    if request.method == 'POST':
        form = ReviewReportForm(request.POST)
        if form.is_valid():
            report, created = ReviewReport.objects.update_or_create(
                review=review,
                reporter=request.user,
                defaults={
                    'reason': form.cleaned_data['reason'],
                    'details': form.cleaned_data['details'],
                    'status': 'PENDING'
                }
            )
            # Flag the review for moderator attention
            review.is_flagged = True
            review.save(update_fields=['is_flagged'])

            messages.info(request, "Thank you. This review has been reported and sent to moderators.")
        else:
            messages.error(request, "Unable to submit report.")

    return redirect('movies:movie_detail', slug=review.movie.slug)
