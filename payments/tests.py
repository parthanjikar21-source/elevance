from datetime import timedelta, date, time
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from theaters.models import City, Theater, Screen, Seat, ShowSchedule
from movies.models import Movie
from bookings.models import Booking, BookingSeat, SeatReservation
from payments.models import PaymentTransaction

User = get_user_model()


class PaymentWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='customer', password='password123', email='cust@test.com')
        self.client.login(username='customer', password='password123')

        self.city = City.objects.create(name='Mumbai', state='Maharashtra')
        self.theater = Theater.objects.create(city=self.city, name='Cineverse Multiplex')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1')
        self.seat = Seat.objects.create(screen=self.screen, row_identifier='B', seat_number=5, seat_code='B5')

        self.movie = Movie.objects.create(
            title='Test Movie',
            duration_minutes=120,
            release_date=date(2024, 1, 1),
            youtube_trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        )

        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            screen=self.screen,
            show_date=timezone.now().date() + timedelta(days=2),
            start_time=time(19, 0),
            base_price=Decimal('300.00'),
            status='SCHEDULED'
        )

        self.booking = Booking.objects.create(
            user=self.user,
            show=self.show,
            total_ticket_amount=Decimal('300.00'),
            convenience_fee=Decimal('30.00'),
            final_amount=Decimal('330.00'),
            status='PENDING_PAYMENT'
        )

        self.reservation = SeatReservation.objects.create(
            show=self.show,
            seat=self.seat,
            user=self.user,
            session_key='test_session',
            status='TEMPORARY_RESERVED',
            expires_at=timezone.now() + timedelta(minutes=2),
            booking=self.booking
        )

    def test_successful_payment_confirms_booking_and_locks_seats(self):
        """
        Verify successful payment marks booking as CONFIRMED and seats as BOOKED.
        """
        response = self.client.post(f'/payments/simulate/{self.booking.booking_id}/', {
            'action': 'success'
        })
        self.assertEqual(response.status_code, 302)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMED')

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'BOOKED')

        self.assertTrue(PaymentTransaction.objects.filter(booking=self.booking, status='SUCCESS').exists())

    def test_failed_payment_automatically_releases_seats(self):
        """
        Verify failed transaction releases the reserved seats back to inventory.
        """
        response = self.client.post(f'/payments/simulate/{self.booking.booking_id}/', {
            'action': 'failed'
        })
        self.assertEqual(response.status_code, 302)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CANCELLED')

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'RELEASED')

        self.assertTrue(PaymentTransaction.objects.filter(booking=self.booking, status='FAILED').exists())

    def test_payment_idempotency_prevents_duplicate_processing(self):
        """
        Duplicate calls for an already confirmed booking return cleanly without duplicates.
        """
        self.client.post(f'/payments/simulate/{self.booking.booking_id}/', {'action': 'success'})
        initial_txns_count = PaymentTransaction.objects.filter(booking=self.booking).count()

        # Call again
        response = self.client.post(f'/payments/simulate/{self.booking.booking_id}/', {'action': 'success'})
        self.assertEqual(response.status_code, 302)

        # Transaction count does not multiply
        self.assertEqual(PaymentTransaction.objects.filter(booking=self.booking).count(), initial_txns_count)
