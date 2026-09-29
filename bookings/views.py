import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages
from django.db import transaction

from theaters.models import ShowSchedule, Seat
from .models import SeatReservation, Booking, BookingSeat, SeatUnavailableError
from .ticket_generator import generate_booking_ticket_pdf


def seat_selection_view(request, show_id):
    """
    Seat Selection & Live Availability view:
    - Renders seat map with row identifiers, seat numbers, types, and prices.
    - Displays live availability (Available, Temporary Reserved with 2-min lock, Booked).
    - Real-time countdown timer if the current user already has active holds.
    """
    show = get_object_or_404(
        ShowSchedule.objects.select_related('movie', 'screen__theater__city'),
        id=show_id
    )

    if show.is_past():
        messages.warning(request, "This show has already started or ended.")
        return redirect('movies:movie_detail', slug=show.movie.slug)

    # Clean up expired reservations
    SeatReservation.cleanup_expired(show=show)

    screen = show.screen
    seats = screen.seats.filter(is_active=True).order_by('row_identifier', 'seat_number')

    # Fetch active reservations for this show
    now = timezone.now()
    active_reservations = SeatReservation.objects.filter(
        show=show,
        status__in=['TEMPORARY_RESERVED', 'BOOKED']
    ).select_related('seat')

    # Map seat ID to reservation state
    session_key = request.session.session_key or ''
    user_id = request.user.id if request.user.is_authenticated else None

    seat_state_map = {}
    user_held_seats = []
    user_held_expires_at = None

    for res in active_reservations:
        if res.status == 'BOOKED':
            seat_state_map[res.seat_id] = {'status': 'BOOKED', 'label': 'Booked'}
        elif res.status == 'TEMPORARY_RESERVED' and res.expires_at > now:
            is_me = (user_id and res.user_id == user_id) or (session_key and res.session_key == session_key)
            if is_me:
                seat_state_map[res.seat_id] = {'status': 'MY_RESERVED', 'label': 'Held by you'}
                user_held_seats.append(res.seat_id)
                if not user_held_expires_at or res.expires_at > user_held_expires_at:
                    user_held_expires_at = res.expires_at
            else:
                seat_state_map[res.seat_id] = {'status': 'RESERVED', 'label': 'Reserved (Temporary Hold)'}

    # Group seats by row
    rows = {}
    for seat in seats:
        row = seat.row_identifier
        if row not in rows:
            rows[row] = []
        
        info = seat_state_map.get(seat.id, {'status': 'AVAILABLE', 'label': 'Available'})
        seat_price = show.calculate_seat_price(seat)
        rows[row].append({
            'seat': seat,
            'status': info['status'],
            'price': seat_price,
            'is_selectable': (info['status'] == 'AVAILABLE' or info['status'] == 'MY_RESERVED'),
        })

    # Seat tiers summary
    tier_prices = {
        'REGULAR': show.calculate_seat_price(Seat(price_multiplier=Decimal('1.00'))),
        'PREMIUM': show.calculate_seat_price(Seat(price_multiplier=Decimal('1.30'))),
        'VIP_RECLINER': show.calculate_seat_price(Seat(price_multiplier=Decimal('1.70'))),
    }

    seconds_remaining = 0
    if user_held_expires_at:
        seconds_remaining = max(0, int((user_held_expires_at - now).total_seconds()))

    context = {
        'show': show,
        'screen': screen,
        'rows': rows,
        'tier_prices': tier_prices,
        'user_held_seats': user_held_seats,
        'seconds_remaining': seconds_remaining,
        'user_held_expires_at': user_held_expires_at.isoformat() if user_held_expires_at else '',
    }
    return render(request, 'bookings/seat_selection.html', context)


def check_seat_availability_api(request, show_id):
    """
    Live Availability Polling Endpoint:
    Returns the real-time reservation status of all seats for live UI updates.
    """
    show = get_object_or_404(ShowSchedule, id=show_id)
    SeatReservation.cleanup_expired(show=show)

    now = timezone.now()
    session_key = request.session.session_key or ''
    user_id = request.user.id if request.user.is_authenticated else None

    active_reservations = SeatReservation.objects.filter(
        show=show,
        status__in=['TEMPORARY_RESERVED', 'BOOKED']
    ).select_related('seat')

    seat_statuses = {}
    for res in active_reservations:
        if res.status == 'BOOKED':
            seat_statuses[res.seat_id] = 'BOOKED'
        elif res.status == 'TEMPORARY_RESERVED' and res.expires_at > now:
            is_me = (user_id and res.user_id == user_id) or (session_key and res.session_key == session_key)
            seat_statuses[res.seat_id] = 'MY_RESERVED' if is_me else 'RESERVED'

    return JsonResponse({
        'show_id': show.id,
        'timestamp': now.isoformat(),
        'seat_statuses': seat_statuses,
    })


@login_required
@require_POST
def reserve_seats_view(request, show_id):
    """
    2-Minute Smart Seat Reservation with strict concurrency protection.
    Accepts seat IDs, locks them atomically, and transitions to checkout.
    """
    show = get_object_or_404(ShowSchedule.objects.select_related('movie', 'screen'), id=show_id)

    # Parse seat IDs
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
            seat_ids = data.get('seat_ids', [])
        else:
            seat_ids = request.POST.getlist('seat_ids')
        seat_ids = [int(s) for s in seat_ids if str(s).isdigit()]
    except Exception:
        seat_ids = []

    if not seat_ids:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': 'Please select at least one seat.'}, status=400)
        messages.error(request, "Please select at least one seat before proceeding.")
        return redirect('bookings:seat_selection', show_id=show.id)

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    # Atomic Reservation with concurrency lock
    try:
        with transaction.atomic():
            reservations, expires_at = SeatReservation.reserve_seats_atomically(
                show=show,
                seat_ids=seat_ids,
                user=request.user,
                session_key=session_key,
                duration_seconds=120  # Strict 2 minute hold
            )

            # Calculate total ticket price
            seats = Seat.objects.filter(id__in=seat_ids)
            total_ticket_amount = sum(show.calculate_seat_price(s) for s in seats)
            convenience_fee = Decimal('30.00')
            final_amount = total_ticket_amount + convenience_fee

            # Create or update Pending Booking
            booking = Booking.objects.create(
                user=request.user,
                show=show,
                total_ticket_amount=total_ticket_amount,
                convenience_fee=convenience_fee,
                final_amount=final_amount,
                status='PENDING_PAYMENT'
            )

            # Link reservations to this booking
            SeatReservation.objects.filter(id__in=[r.id for r in reservations]).update(booking=booking)

            # Create individual BookingSeat records
            BookingSeat.objects.bulk_create([
                BookingSeat(
                    booking=booking,
                    seat=seat,
                    seat_code=seat.seat_code,
                    seat_type=seat.get_seat_type_display(),
                    price=show.calculate_seat_price(seat)
                ) for seat in seats
            ])

        checkout_url = f"/payments/checkout/{booking.booking_id}/"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'booking_id': booking.booking_id,
                'checkout_url': checkout_url,
                'expires_at': expires_at.isoformat(),
                'seconds_remaining': 120,
            })
        return redirect('payments:checkout', booking_id=booking.booking_id)

    except SeatUnavailableError as exc:
        msg = f"Duplicate booking prevented: Seat(s) {', '.join(exc.conflicting_seats)} are already reserved by another user. Please choose different seats."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': msg, 'conflicts': exc.conflicting_seats}, status=409)
        messages.error(request, msg)
        return redirect('bookings:seat_selection', show_id=show.id)


@login_required
def modify_or_release_seats(request, booking_id):
    """
    Allows user to modify their seat selection before payment.
    Releases the temporary reservation immediately and returns to seat map.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    show_id = booking.show_id

    if booking.status == 'PENDING_PAYMENT':
        booking.cancel_and_release_seats()
        messages.info(request, "Seat selection released. You can now select new seats.")

    return redirect('bookings:seat_selection', show_id=show_id)


@login_required
def booking_detail(request, booking_id):
    """
    Booking Confirmation / Summary page.
    Shows confirmed boarding pass, QR code, and ticket download option.
    """
    booking = get_object_or_404(
        Booking.objects.select_related(
            'show__movie', 'show__screen__theater__city', 'user'
        ).prefetch_related('booked_seats', 'payments'),
        booking_id=booking_id
    )

    if booking.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You do not have access to this booking.")

    # Ensure ticket PDF and QR code are ready
    if booking.status == 'CONFIRMED' and not booking.pdf_ticket:
        generate_booking_ticket_pdf(booking, request=request)
        booking.refresh_from_db()

    context = {
        'booking': booking,
        'user_has_watched': request.user.has_watched_movie(booking.show.movie),
    }
    return render(request, 'bookings/booking_detail.html', context)


@login_required
def download_ticket_pdf_view(request, booking_id):
    """
    Downloads the official high-resolution PDF ticket.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if booking.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized to download this ticket.")

    if not booking.pdf_ticket:
        pdf_bytes = generate_booking_ticket_pdf(booking, request=request)
    else:
        booking.pdf_ticket.open()
        pdf_bytes = booking.pdf_ticket.read()
        booking.pdf_ticket.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Cineverse_Ticket_{booking.booking_id}.pdf"'
    return response


def verify_ticket_view(request, token):
    """
    QR Code Verification View:
    Accessed by cinema staff or ticket scanners to verify ticket validity and admission.
    """
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'show__screen__theater__city', 'user')
        .prefetch_related('booked_seats', 'payments'),
        verification_token=token
    )

    action_message = None
    if request.method == 'POST' and request.user.is_staff:
        if not booking.is_checked_in and booking.status == 'CONFIRMED':
            booking.is_checked_in = True
            booking.checked_in_at = timezone.now()
            booking.save(update_fields=['is_checked_in', 'checked_in_at'])
            action_message = f"Check-in successful! Admitted at {booking.checked_in_at.strftime('%I:%M %p')}"
        elif booking.is_checked_in:
            action_message = f"Notice: Already checked in earlier at {booking.checked_in_at.strftime('%I:%M %p')}"

    context = {
        'booking': booking,
        'action_message': action_message,
        'is_staff': request.user.is_staff,
    }
    return render(request, 'bookings/verify_ticket.html', context)
