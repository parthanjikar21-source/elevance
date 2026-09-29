import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Booking
from .ticket_generator import generate_booking_ticket_pdf

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation_email_task(self, booking_id):
    """
    Asynchronous background task to generate PDF ticket and deliver
    email confirmation with automated retries.
    """
    try:
        booking = Booking.objects.select_related(
            'user', 'show__movie', 'show__screen__theater__city'
        ).get(id=booking_id)

        # Ensure PDF ticket exists
        if not booking.pdf_ticket:
            generate_booking_ticket_pdf(booking)
            booking.refresh_from_db()

        subject = f"🎟️ Your Cineverse Ticket Confirmed: {booking.booking_id} - {booking.show.movie.title}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = booking.user.email

        if not to_email:
            logger.warning(f"No email address found for user on booking {booking.booking_id}")
            return f"No email for booking {booking.booking_id}"

        context = {
            'booking': booking,
            'user': booking.user,
            'show': booking.show,
            'movie': booking.show.movie,
            'theater': booking.show.screen.theater,
            'screen': booking.show.screen,
            'seats': booking.seats_display,
        }

        # Render HTML template and fallback text
        html_content = render_to_string('emails/booking_confirmation.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")

        # Attach PDF ticket
        if booking.pdf_ticket:
            booking.pdf_ticket.open()
            email.attach(
                f"Cineverse_Ticket_{booking.booking_id}.pdf",
                booking.pdf_ticket.read(),
                'application/pdf'
            )
            booking.pdf_ticket.close()

        email.send(fail_silently=False)
        logger.info(f"Booking confirmation email sent successfully for {booking.booking_id} to {to_email}")
        return f"Email sent successfully for booking {booking.booking_id}"

    except Exception as exc:
        logger.error(f"Error sending booking confirmation email for booking {booking_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc)
