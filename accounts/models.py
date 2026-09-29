from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="User contact phone number")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    preferred_city = models.ForeignKey(
        'theaters.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_users'
    )
    loyalty_points = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.get_full_name() or self.username

    def has_watched_movie(self, movie):
        """
        Returns True only if the user has a confirmed booking for a show of this movie
        whose schedule is in the past (already screened or currently running).
        """
        now = timezone.now()
        current_date = now.date()
        current_time = now.time()

        return self.bookings.filter(
            status='CONFIRMED',
            show__movie=movie
        ).filter(
            models.Q(show__show_date__lt=current_date) |
            models.Q(show__show_date=current_date, show__start_time__lte=current_time)
        ).exists()

    def is_verified_viewer(self, movie):
        return self.has_watched_movie(movie)

    @property
    def confirmed_bookings_count(self):
        return self.bookings.filter(status='CONFIRMED').count()
