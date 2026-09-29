import re
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Avg, Count


class Genre(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CastMember(models.Model):
    ROLE_CHOICES = [
        ('ACTOR', 'Actor / Actress'),
        ('DIRECTOR', 'Director'),
        ('PRODUCER', 'Producer'),
        ('WRITER', 'Writer'),
        ('MUSIC_DIRECTOR', 'Music Director'),
    ]

    name = models.CharField(max_length=120, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ACTOR')
    photo = models.ImageField(upload_to='cast/', blank=True, null=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class Movie(models.Model):
    AGE_CERTIFICATIONS = [
        ('U', 'U - Universal (All Ages)'),
        ('UA 7+', 'UA 7+ (Parental Guidance for Children under 7)'),
        ('UA 13+', 'UA 13+ (Parental Guidance for Children under 13)'),
        ('UA 16+', 'UA 16+ (Parental Guidance for Children under 16)'),
        ('A', 'A - Adults Only (18+)'),
        ('PG-13', 'PG-13 (Parents Strongly Cautioned)'),
        ('R', 'R - Restricted'),
    ]

    STATUS_CHOICES = [
        ('NOW_SHOWING', 'Now Showing'),
        ('COMING_SOON', 'Coming Soon'),
        ('ARCHIVED', 'Archived'),
    ]

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration in minutes")
    release_date = models.DateField(db_index=True)
    age_certification = models.CharField(max_length=15, choices=AGE_CERTIFICATIONS, default='UA 13+')
    genres = models.ManyToManyField(Genre, related_name='movies')
    languages = models.ManyToManyField(Language, related_name='movies')
    cast_members = models.ManyToManyField(CastMember, through='MovieCast', related_name='movies')
    youtube_trailer_url = models.URLField(
        help_text="YouTube video link (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)"
    )
    poster_image = models.ImageField(upload_to='movies/posters/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='movies/banners/', blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NOW_SHOWING', db_index=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'), db_index=True)
    total_reviews = models.PositiveIntegerField(default=0)
    is_trending = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date', 'title']
        indexes = [
            models.Index(fields=['status', 'release_date']),
            models.Index(fields=['average_rating', 'is_trending']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.release_date.year if self.release_date else ''})"

    @property
    def duration_formatted(self):
        hours = self.duration_minutes // 60
        mins = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @property
    def youtube_video_id(self):
        if not self.youtube_trailer_url:
            return None
        # Extract YouTube ID using regex
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([\w-]{11})'
        match = re.search(pattern, self.youtube_trailer_url)
        if match:
            return match.group(1)
        return None

    @property
    def youtube_embed_url(self):
        video_id = self.youtube_video_id
        if video_id:
            # Secure privacy-enhanced embed URL with sandbox-friendly parameters
            return f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=0&rel=0&modestbranding=1"
        return None

    def recalculate_rating_stats(self):
        stats = self.reviews.filter(is_approved=True).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        avg = stats['avg_rating'] or 0.00
        self.average_rating = round(Decimal(str(avg)), 2)
        self.total_reviews = stats['count']
        self.save(update_fields=['average_rating', 'total_reviews'])
        return self.average_rating, self.total_reviews


class MovieCast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='movie_cast_entries')
    cast_member = models.ForeignKey(CastMember, on_delete=models.CASCADE, related_name='movie_cast_entries')
    character_name = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('movie', 'cast_member')

    def __str__(self):
        return f"{self.cast_member.name} as {self.character_name or 'Cast'} in {self.movie.title}"


class MoviePoster(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='additional_posters')
    image = models.ImageField(upload_to='movies/gallery/')
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'id']

    def __str__(self):
        return f"Poster for {self.movie.title} ({self.caption or 'Gallery'})"


class Review(models.Model):
    RATING_CHOICES = [(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='movie_reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, db_index=True)
    title = models.CharField(max_length=150)
    content = models.TextField()
    is_verified_viewer = models.BooleanField(default=False, help_text="User booked and watched this movie")
    is_flagged = models.BooleanField(default=False, db_index=True)
    is_approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('movie', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review on {self.movie.title} - {self.rating}★"

    def save(self, *args, **kwargs):
        # Determine verified viewer status if not explicitly set
        if not self.is_verified_viewer and self.user_id:
            self.is_verified_viewer = self.user.has_watched_movie(self.movie)
        super().save(*args, **kwargs)
        self.movie.recalculate_rating_stats()

    def delete(self, *args, **kwargs):
        movie = self.movie
        super().delete(*args, **kwargs)
        movie.recalculate_rating_stats()


class ReviewReport(models.Model):
    REPORT_REASONS = [
        ('SPAM', 'Spam, promotional, or automated content'),
        ('OFFENSIVE', 'Hate speech, harassment, or abusive language'),
        ('SPOILERS', 'Contains major unflagged spoilers'),
        ('INAPPROPRIATE', 'Inappropriate or sexually explicit material'),
        ('OTHER', 'Other violation'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Moderation'),
        ('REVIEWED', 'Reviewed - Kept'),
        ('DISMISSED', 'Dismissed'),
        ('CONTENT_REMOVED', 'Review Removed / Hidden'),
    ]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS, default='INAPPROPRIATE')
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('review', 'reporter')

    def __str__(self):
        return f"Report on {self.review} by {self.reporter.username} ({self.get_reason_display()})"


class UserRecentlyViewed(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recently_viewed_movies'
    )
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='recently_viewed_by')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
            models.Index(fields=['session_key', 'viewed_at']),
        ]

    def __str__(self):
        identifier = self.user.username if self.user else f"Session:{self.session_key[:8]}"
        return f"{identifier} viewed {self.movie.title}"
