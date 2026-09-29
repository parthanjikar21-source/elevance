from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal


class City(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    state = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.state}"


class Theater(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    slug = models.SlugField(max_length=180, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='theaters')
    address = models.TextField()
    landmark = models.CharField(max_length=150, blank=True)
    pincode = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=20, blank=True)
    facilities = models.CharField(
        max_length=255,
        default="Dolby Atmos, 4K Projection, Recliner Seats, Gourmet Food, Parking",
        help_text="Comma-separated list of amenities"
    )
    image = models.ImageField(upload_to='theaters/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('city', 'name')
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.city.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.city.name}"

    @property
    def amenities_list(self):
        return [f.strip() for f in self.facilities.split(',') if f.strip()]


class Screen(models.Model):
    SCREEN_TYPES = [
        ('STANDARD', 'Standard 2D/3D'),
        ('IMAX_3D', 'IMAX with Laser 3D'),
        ('DOLBY_ATMOS', 'Dolby Atmos 4K'),
        ('4DX', '4DX Motion'),
        ('GOLD_CLASS', 'Gold Class / Luxury VIP'),
    ]

    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=100)
    screen_type = models.CharField(max_length=20, choices=SCREEN_TYPES, default='STANDARD')
    total_seats = models.PositiveIntegerField(default=0)
    rows_count = models.PositiveIntegerField(default=8)
    cols_count = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('theater', 'name')
        ordering = ['theater', 'name']

    def __str__(self):
        return f"{self.theater.name} - {self.name} ({self.get_screen_type_display()})"

    def recalculate_total_seats(self):
        count = self.seats.filter(is_active=True).count()
        self.total_seats = count
        self.save(update_fields=['total_seats'])
        return count


class Seat(models.Model):
    SEAT_TYPES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('VIP_RECLINER', 'VIP Recliner'),
    ]

    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    row_identifier = models.CharField(max_length=5, db_index=True, help_text="e.g. A, B, C")
    seat_number = models.PositiveIntegerField(help_text="e.g. 1, 2, 3")
    seat_code = models.CharField(max_length=10, db_index=True, help_text="e.g. A1, B12")
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES, default='REGULAR')
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'))
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('screen', 'row_identifier', 'seat_number')
        ordering = ['row_identifier', 'seat_number']
        indexes = [
            models.Index(fields=['screen', 'seat_code']),
        ]

    def save(self, *args, **kwargs):
        if not self.seat_code:
            self.seat_code = f"{self.row_identifier}{self.seat_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.screen.name} - {self.seat_code} ({self.get_seat_type_display()})"


class ShowSchedule(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('HOUSEFULL', 'Housefull'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]

    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='shows')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows')
    show_date = models.DateField(db_index=True)
    start_time = models.TimeField(db_index=True)
    end_time = models.TimeField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Standard regular seat price")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SCHEDULED', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['show_date', 'start_time']
        indexes = [
            models.Index(fields=['show_date', 'start_time']),
            models.Index(fields=['movie', 'show_date']),
        ]

    def __str__(self):
        return f"{self.movie.title} | {self.screen} | {self.show_date} {self.start_time.strftime('%I:%M %p')}"

    def calculate_seat_price(self, seat):
        return round(self.base_price * seat.price_multiplier, 2)

    def is_past(self):
        now = timezone.now()
        if self.show_date < now.date():
            return True
        if self.show_date == now.date() and self.start_time < now.time():
            return True
        return False
