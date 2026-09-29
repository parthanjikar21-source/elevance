from datetime import timedelta, date, time
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from theaters.models import City, Theater, Screen, Seat, ShowSchedule
from movies.models import Movie, Genre, Review, ReviewReport
from bookings.models import Booking

User = get_user_model()


class MovieReviewAndVerifiedViewerTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_watched = User.objects.create_user(username='watched_user', password='password123')
        self.user_unwatched = User.objects.create_user(username='unwatched_user', password='password123')

        self.city = City.objects.create(name='Mumbai', state='Maharashtra')
        self.theater = Theater.objects.create(city=self.city, name='Cineverse Central')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1')

        self.genre = Genre.objects.create(name='Sci-Fi')
        self.movie = Movie.objects.create(
            title='Interstellar',
            duration_minutes=169,
            release_date=date(2023, 1, 1),
            youtube_trailer_url='https://www.youtube.com/watch?v=zSWdZVtXT7E'
        )
        self.movie.genres.add(self.genre)

        # Past show (Watched)
        self.past_show = ShowSchedule.objects.create(
            movie=self.movie,
            screen=self.screen,
            show_date=timezone.now().date() - timedelta(days=2),
            start_time=time(14, 0),
            base_price=Decimal('200.00'),
            status='COMPLETED'
        )

        # Confirmed Booking for user_watched
        self.booking = Booking.objects.create(
            user=self.user_watched,
            show=self.past_show,
            total_ticket_amount=Decimal('200.00'),
            convenience_fee=Decimal('30.00'),
            final_amount=Decimal('230.00'),
            status='CONFIRMED',
            is_checked_in=True
        )

    def test_youtube_embed_url_property(self):
        """
        Verify YouTube trailer secure embed URL formatting.
        """
        self.assertEqual(self.movie.youtube_video_id, 'zSWdZVtXT7E')
        self.assertIn('https://www.youtube-nocookie.com/embed/zSWdZVtXT7E', self.movie.youtube_embed_url)

    def test_verified_viewer_qualification(self):
        """
        user_watched has a confirmed past booking -> True
        user_unwatched has no booking -> False
        """
        self.assertTrue(self.user_watched.has_watched_movie(self.movie))
        self.assertFalse(self.user_unwatched.has_watched_movie(self.movie))

    def test_unverified_user_cannot_submit_review(self):
        """
        An unverified user attempting to post a review is blocked with an error.
        """
        self.client.login(username='unwatched_user', password='password123')
        response = self.client.post(f'/movies/{self.movie.slug}/review/', {
            'rating': 5,
            'title': 'Great film',
            'content': 'I liked it without seeing it!'
        })
        # Should redirect back to detail page with error message
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(movie=self.movie, user=self.user_unwatched).exists())

    def test_verified_user_can_submit_and_edit_review(self):
        """
        A verified user who watched the movie can submit a review, and average rating updates.
        """
        self.client.login(username='watched_user', password='password123')
        
        # 1. Submit review
        response = self.client.post(f'/movies/{self.movie.slug}/review/', {
            'rating': 5,
            'title': 'Stunning Masterpiece',
            'content': 'The visual effects and emotional depth were incredible.'
        })
        self.assertEqual(response.status_code, 302)

        review = Review.objects.get(movie=self.movie, user=self.user_watched)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_verified_viewer)

        # Average rating updated
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.average_rating, Decimal('5.00'))
        self.assertEqual(self.movie.total_reviews, 1)

        # 2. Edit review
        response2 = self.client.post(f'/movies/{self.movie.slug}/review/', {
            'rating': 4,
            'title': 'Updated: Great film overall',
            'content': 'Slightly slow in the middle, but incredible third act.'
        })
        self.assertEqual(response2.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)

        self.movie.refresh_from_db()
        self.assertEqual(self.movie.average_rating, Decimal('4.00'))

    def test_report_inappropriate_review(self):
        """
        Users can report inappropriate reviews which flags the review for moderation.
        """
        review = Review.objects.create(
            movie=self.movie,
            user=self.user_watched,
            rating=5,
            title='Original Review',
            content='Good movie',
            is_verified_viewer=True
        )

        self.client.login(username='unwatched_user', password='password123')
        response = self.client.post(f'/reviews/{review.id}/report/', {
            'reason': 'SPAM',
            'details': 'Link spamming'
        })
        self.assertEqual(response.status_code, 302)

        review.refresh_from_db()
        self.assertTrue(review.is_flagged)
        self.assertTrue(ReviewReport.objects.filter(review=review, reporter=self.user_unwatched).exists())
