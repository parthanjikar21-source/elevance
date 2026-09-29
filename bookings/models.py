import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string


class SeatUnavailableError(Exception):
    """Raised when one or more seats are already reserved or booked by another user."""
    def __init__(self, conflicting_seats):
        self.conflicting_seats = conflicting_seats
        super().__init__(f"The following seat(s) are no longer available: {', '.join(conflicting_seats)}")


class SeatReservation(models.Model):
    STATUS_CHOICES = [
        ('TEMPORARY_RESERVED', 'Temporary Reserved (2 Min Lock)'),
        ('BOOKED', 'Confirmed Booked'),
        ('RELEASED', 'Released / Expired'),
    ]

    show = models.ForeignKey(
        'theaters.ShowSchedule',
        on_delete=models.CASCADE,
        related_name='reservations',
        db_index=True
    )
    seat = models.ForeignKey(
        'theaters.Seat',
        on_delete=models.CASCADE,
        related_name='reservations',
        db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seat_reservations'
    )
    session_key = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TEMPORARY_RESERVED', db_index=True)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    booking = models.ForeignKey(
        'Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seat_reservations'
    )

    class Meta:
        indexes = [
            models.Index(fields=['show', 'status', 'expires_at']),
            models.Index(fields=['session_key', 'status']),
            models.Index(fields=['show', 'seat']),
        ]

    def __str__(self):
        return f"{self.show} - {self.seat.seat_code} ({self.status})"

    @property
    def is_active(self):
        if self.status == 'BOOKED':
            return True
        if self.status == 'TEMPORARY_RESERVED':
            return self.expires_at > timezone.now()
        return False

    @property
    def seconds_remaining(self):
        if self.status != 'TEMPORARY_RESERVED':
            return 0
        diff = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(diff))

    @classmethod
    def cleanup_expired(cls, show=None):
        """
        Releases any temporary reservations whose 2-minute expiration window has elapsed.
        """
        now = timezone.now()
        qs = cls.objects.filter(status='TEMPORARY_RESERVED', expires_at__lte=now)
        if show:
            qs = qs.filter(show=show)
        count = qs.update(status='RELEASED')
        return count

    @classmethod
    def reserve_seats_atomically(cls, show, seat_ids, user=None, session_key='', duration_seconds=120):
        """
        Smart seat reservation using strict database locking (select_for_update)
        and atomic transactions. Guarantees that concurrent requests never produce
        duplicate locks or duplicate bookings.
        """
        from theaters.models import Seat

        with transaction.atomic():
            # First, clean up expired holds for this show
            cls.cleanup_expired(show=show)

            # Query and lock all current reservations for the targeted seats
            now = timezone.now()
            existing_reservations = (
                cls.objects.select_for_update()
                .filter(show=show, seat_id__in=seat_ids)
            )

            conflicts = []
            reserved_by_current = []

            for res in existing_reservations:
                # If permanently booked
                if res.status == 'BOOKED':
                    conflicts.append(res.seat.seat_code)
                # If actively reserved by someone else
                elif res.status == 'TEMPORARY_RESERVED' and res.expires_at > now:
                    is_same_user = False
                    if user and user.is_authenticated and res.user_id == user.id:
                        is_same_user = True
                    elif session_key and res.session_key == session_key:
                        is_same_user = True

                    if not is_same_user:
                        conflicts.append(res.seat.seat_code)
                    else:
                        reserved_by_current.append(res)

            if conflicts:
                raise SeatUnavailableError(conflicts)

            # Lock was successful! Set new expiration time (2 minutes from now)
            expires_at = now + timedelta(seconds=duration_seconds)
            seats = list(Seat.objects.filter(id__in=seat_ids, screen=show.screen, is_active=True))

            created_or_updated = []
            for seat in seats:
                res, created = cls.objects.select_for_update().update_or_create(
                    show=show,
                    seat=seat,
                    defaults={
                        'user': user if user and user.is_authenticated else None,
                        'session_key': session_key,
                        'status': 'TEMPORARY_RESERVED',
                        'expires_at': expires_at,
                    }
                )
                created_or_updated.append(res)

            return created_or_updated, expires_at


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('REFUNDED', 'Refunded'),
    ]

    booking_id = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey('theaters.ShowSchedule', on_delete=models.CASCADE, related_name='bookings')
    total_ticket_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    convenience_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('30.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT', db_index=True)
    qr_code_image = models.ImageField(upload_to='tickets/qr/', blank=True, null=True)
    pdf_ticket = models.FileField(upload_to='tickets/pdf/', blank=True, null=True)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    is_checked_in = models.BooleanField(default=False, db_index=True)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['show', 'status']),
        ]

    def __str__(self):
        return f"{self.booking_id} - {self.show.movie.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.booking_id:
            year = timezone.now().year
            rand_suffix = get_random_string(6, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')
            self.booking_id = f"CIN-{year}-{rand_suffix}"
        super().save(*args, **kwargs)

    @property
    def seats_display(self):
        return ", ".join([bs.seat_code for bs in self.booked_seats.all()])

    @property
    def seats_count(self):
        return self.booked_seats.count()

    def confirm_and_lock_seats(self):
        """
        Transition booking to CONFIRMED and permanently mark its seat reservations as BOOKED.
        """
        with transaction.atomic():
            self.status = 'CONFIRMED'
            self.save(update_fields=['status', 'updated_at'])
            SeatReservation.objects.filter(booking=self).update(status='BOOKED')

    def cancel_and_release_seats(self):
        """
        Releases reserved seats when payment fails or booking is cancelled.
        """
        with transaction.atomic():
            self.status = 'CANCELLED'
            self.save(update_fields=['status', 'updated_at'])
            SeatReservation.objects.filter(booking=self).update(status='RELEASED')


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    seat = models.ForeignKey('theaters.Seat', on_delete=models.CASCADE, related_name='booking_seats')
    seat_code = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ['seat_code']

    def __str__(self):
        return f"{self.booking.booking_id} - Seat {self.seat_code} (₹{self.price})"
