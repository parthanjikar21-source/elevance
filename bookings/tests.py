from datetime import timedelta, date, time
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from theaters.models import City, Theater, Screen, Seat, ShowSchedule
from movies.models import Movie, Genre, Language
from bookings.models import SeatReservation, Booking, BookingSeat, SeatUnavailableError
from bookings.ticket_generator import generate_booking_ticket_pdf

User = get_user_model()


class SmartSeatReservationTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@test.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@test.com')

        self.city = City.objects.create(name='Mumbai', state='Maharashtra')
        self.theater = Theater.objects.create(city=self.city, name='Cineverse South')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1', total_seats=20)

        self.seat_a1 = Seat.objects.create(screen=self.screen, row_identifier='A', seat_number=1, seat_code='A1', price_multiplier=Decimal('1.0'))
        self.seat_a2 = Seat.objects.create(screen=self.screen, row_identifier='A', seat_number=2, seat_code='A2', price_multiplier=Decimal('1.0'))

        self.movie = Movie.objects.create(
            title='Inception',
            duration_minutes=148,
            release_date=date(2024, 1, 1),
            youtube_trailer_url='https://www.youtube.com/watch?v=YoHD9XEInc0'
        )

        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            screen=self.screen,
            show_date=timezone.now().date() + timedelta(days=1),
            start_time=time(18, 30),
            base_price=Decimal('250.00'),
            status='SCHEDULED'
        )

    def test_temporary_reservation_2_minute_lock(self):
        """
        Verify that reserving a seat sets a 2-minute lock.
        """
        reservations, expires_at = SeatReservation.reserve_seats_atomically(
            show=self.show,
            seat_ids=[self.seat_a1.id],
            user=self.user1,
            session_key='session_alice',
            duration_seconds=120
        )
        self.assertEqual(len(reservations), 1)
        res = reservations[0]
        self.assertEqual(res.status, 'TEMPORARY_RESERVED')
        self.assertTrue(res.is_active)
        self.assertGreater(res.expires_at, timezone.now())

    def test_concurrent_conflict_prevention(self):
        """
        Verify that when user1 reserves A1, user2 cannot reserve A1 simultaneously.
        """
        # User 1 reserves A1
        SeatReservation.reserve_seats_atomically(
            show=self.show,
            seat_ids=[self.seat_a1.id],
            user=self.user1,
            session_key='session_alice',
            duration_seconds=120
        )

        # User 2 attempts to reserve A1 and A2
        with self.assertRaises(SeatUnavailableError) as ctx:
            SeatReservation.reserve_seats_atomically(
                show=self.show,
                seat_ids=[self.seat_a1.id, self.seat_a2.id],
                user=self.user2,
                session_key='session_bob',
                duration_seconds=120
            )

        self.assertIn('A1', ctx.exception.conflicting_seats)

    def test_expired_hold_is_automatically_released(self):
        """
        Verify that expired reservations (> 2 mins old) are released automatically
        allowing other users to book the seat.
        """
        # Create an expired reservation
        SeatReservation.objects.create(
            show=self.show,
            seat=self.seat_a1,
            user=self.user1,
            session_key='session_alice',
            status='TEMPORARY_RESERVED',
            expires_at=timezone.now() - timedelta(seconds=10) # Expired 10 seconds ago
        )

        # User 2 attempts to reserve A1 - should succeed after cleanup
        reservations, expires_at = SeatReservation.reserve_seats_atomically(
            show=self.show,
            seat_ids=[self.seat_a1.id],
            user=self.user2,
            session_key='session_bob',
            duration_seconds=120
        )
        self.assertEqual(len(reservations), 1)
        self.assertEqual(reservations[0].user, self.user2)

    def test_pdf_ticket_and_qr_generation(self):
        """
        Verify PDF ticket generation with QR code and proper booking fields.
        """
        booking = Booking.objects.create(
            user=self.user1,
            show=self.show,
            total_ticket_amount=Decimal('250.00'),
            convenience_fee=Decimal('30.00'),
            final_amount=Decimal('280.00'),
            status='CONFIRMED'
        )
        BookingSeat.objects.create(
            booking=booking,
            seat=self.seat_a1,
            seat_code='A1',
            seat_type='Regular',
            price=Decimal('250.00')
        )

        pdf_bytes = generate_booking_ticket_pdf(booking)
        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(booking.pdf_ticket)
        self.assertTrue(booking.qr_code_image)
