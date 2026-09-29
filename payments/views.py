import hmac
import hashlib
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string

from bookings.models import Booking, SeatReservation
from bookings.ticket_generator import generate_booking_ticket_pdf
from bookings.tasks import send_booking_confirmation_email_task
from .models import PaymentTransaction, PaymentWebhookLog


@login_required
def checkout_view(request, booking_id):
    """
    Checkout & Payment Gateway page.
    Displays order breakdown, live countdown timer, and payment choices.
    """
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'show__screen__theater__city', 'user')
        .prefetch_related('booked_seats'),
        booking_id=booking_id,
        user=request.user
    )

    if booking.status == 'CONFIRMED':
        messages.info(request, "This booking has already been paid and confirmed.")
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    # Check 2-minute reservation hold
    SeatReservation.cleanup_expired(show=booking.show)
    active_reservation = booking.seat_reservations.filter(status='TEMPORARY_RESERVED').first()

    if not active_reservation or active_reservation.expires_at <= timezone.now():
        booking.status = 'EXPIRED'
        booking.save(update_fields=['status'])
        messages.error(request, "Your 2-minute seat reservation has expired. Please select your seats again.")
        return redirect('bookings:seat_selection', show_id=booking.show.id)

    seconds_remaining = max(0, int((active_reservation.expires_at - timezone.now()).total_seconds()))

    # Setup Razorpay order ID or simulation order ID
    order_id = f"order_{booking.booking_id}_{get_random_string(6)}"
    amount_in_paise = int(booking.final_amount * 100)

    context = {
        'booking': booking,
        'seconds_remaining': seconds_remaining,
        'expires_at_iso': active_reservation.expires_at.isoformat(),
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': order_id,
        'amount_in_paise': amount_in_paise,
    }
    return render(request, 'payments/checkout.html', context)


@login_required
@require_POST
def verify_razorpay_payment(request):
    """
    Server-side verification of Razorpay payment credentials.
    Enforces HMAC SHA256 signature verification and idempotency.
    """
    razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_signature = request.POST.get('razorpay_signature', '').strip()
    booking_id = request.POST.get('booking_id', '').strip()

    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    # Idempotency check: if booking already confirmed or transaction already processed
    existing_txn = PaymentTransaction.objects.filter(transaction_id=razorpay_payment_id).first()
    if existing_txn and existing_txn.status == 'SUCCESS':
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    # Server-side HMAC SHA256 Verification
    key_secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
    generated_signature = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    is_valid = hmac.compare_digest(generated_signature, razorpay_signature)

    with transaction.atomic():
        if is_valid:
            # Payment signature is authentic!
            txn, _ = PaymentTransaction.objects.select_for_update().update_or_create(
                transaction_id=razorpay_payment_id,
                defaults={
                    'booking': booking,
                    'user': request.user,
                    'gateway': 'RAZORPAY',
                    'order_id': razorpay_order_id,
                    'payment_id': razorpay_payment_id,
                    'signature': razorpay_signature,
                    'amount': booking.final_amount,
                    'status': 'SUCCESS',
                    'raw_response': request.POST.dict(),
                }
            )

            # Confirm booking and permanently lock seats
            booking.confirm_and_lock_seats()

            # Generate PDF ticket
            generate_booking_ticket_pdf(booking, request=request)

            # Dispatch asynchronous confirmation email task
            send_booking_confirmation_email_task.delay(booking.id)

            messages.success(request, f"Payment successful! Your booking {booking.booking_id} is confirmed.")
            return redirect('bookings:booking_detail', booking_id=booking.booking_id)
        else:
            # Payment signature verification failed! Release seats immediately
            PaymentTransaction.objects.create(
                booking=booking,
                user=request.user,
                gateway='RAZORPAY',
                transaction_id=razorpay_payment_id or f"failed_{get_random_string(10)}",
                order_id=razorpay_order_id,
                amount=booking.final_amount,
                status='FAILED',
                error_code='SIGNATURE_VERIFICATION_FAILED',
                error_description="The payment signature provided by Razorpay could not be verified on the server.",
                raw_response=request.POST.dict(),
            )

            booking.cancel_and_release_seats()
            messages.error(request, "Payment verification failed. Your reserved seats have been released.")
            return redirect('bookings:seat_selection', show_id=booking.show.id)


@login_required
@require_POST
def simulate_payment_action(request, booking_id):
    """
    Complete Payment Workflow Simulator:
    Allows robust end-to-end testing of:
    1. 'success' -> Full successful payment with server-side transaction logging, PDF generation, email dispatch
    2. 'failed' -> Failed transaction with automatic seat release and retry support
    3. 'cancel' -> User cancelled payment releasing reserved seats
    """
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    action = request.POST.get('action', 'success')

    # Check expiration
    active_reservation = booking.seat_reservations.filter(status='TEMPORARY_RESERVED').first()
    if not active_reservation or active_reservation.expires_at <= timezone.now():
        booking.status = 'EXPIRED'
        booking.save(update_fields=['status'])
        messages.error(request, "Reservation expired before payment was processed.")
        return redirect('bookings:seat_selection', show_id=booking.show.id)

    txn_id = f"sim_txn_{get_random_string(14)}"
    order_id = f"sim_order_{booking.booking_id}"

    with transaction.atomic():
        if action == 'success':
            # Idempotency check
            if booking.status == 'CONFIRMED':
                return redirect('bookings:booking_detail', booking_id=booking.booking_id)

            PaymentTransaction.objects.create(
                booking=booking,
                user=request.user,
                gateway='SIMULATION',
                transaction_id=txn_id,
                order_id=order_id,
                payment_id=txn_id,
                amount=booking.final_amount,
                status='SUCCESS',
                raw_response={'simulation': True, 'mode': 'successful_payment'},
            )

            booking.confirm_and_lock_seats()
            generate_booking_ticket_pdf(booking, request=request)
            send_booking_confirmation_email_task.delay(booking.id)

            messages.success(request, f"Payment confirmed! Booking {booking.booking_id} is active.")
            return redirect('bookings:booking_detail', booking_id=booking.booking_id)

        elif action == 'failed':
            PaymentTransaction.objects.create(
                booking=booking,
                user=request.user,
                gateway='SIMULATION',
                transaction_id=txn_id,
                order_id=order_id,
                amount=booking.final_amount,
                status='FAILED',
                error_code='INSUFFICIENT_FUNDS_OR_DECLINED',
                error_description="Transaction declined by issuing bank during payment test simulation.",
                raw_response={'simulation': True, 'mode': 'failed_transaction'},
            )

            # Auto-release reserved seats on payment failure
            booking.cancel_and_release_seats()
            messages.error(request, "Payment failed: Bank declined transaction. Reserved seats have been released automatically.")
            return redirect('bookings:seat_selection', show_id=booking.show.id)

        elif action == 'cancel':
            PaymentTransaction.objects.create(
                booking=booking,
                user=request.user,
                gateway='SIMULATION',
                transaction_id=txn_id,
                order_id=order_id,
                amount=booking.final_amount,
                status='CANCELLED',
                error_code='USER_CANCELLED',
                error_description="Payment process was cancelled by the customer.",
            )

            booking.cancel_and_release_seats()
            messages.info(request, "Payment was cancelled. Your reserved seats are released.")
            return redirect('bookings:seat_selection', show_id=booking.show.id)

    return redirect('payments:checkout', booking_id=booking.booking_id)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay Webhook Handler:
    Verifies server-side webhook signature, records payload in PaymentWebhookLog,
    and idempotently handles events (payment.captured, payment.failed).
    """
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8')
    received_signature = request.headers.get('X-Razorpay-Signature', '')
    payload_body = request.body

    # Verify signature
    expected_signature = hmac.new(webhook_secret, payload_body, hashlib.sha256).hexdigest()
    is_verified = hmac.compare_digest(expected_signature, received_signature)

    try:
        data = json.loads(payload_body.decode('utf-8'))
        event_type = data.get('event', 'unknown')
        entity = data.get('payload', {}).get('payment', {}).get('entity', {})
        payment_id = entity.get('id')
    except Exception:
        data = {}
        event_type = 'unknown'
        payment_id = None

    # Log webhook
    log = PaymentWebhookLog.objects.create(
        gateway='RAZORPAY',
        event_type=event_type,
        payload=data,
        headers=dict(request.headers),
        is_verified=is_verified,
    )

    if not is_verified:
        return HttpResponseBadRequest("Invalid webhook signature")

    # Idempotent processing
    if event_type == 'payment.captured' and payment_id:
        with transaction.atomic():
            txn = PaymentTransaction.objects.filter(transaction_id=payment_id).first()
            if txn and txn.status != 'SUCCESS':
                txn.status = 'SUCCESS'
                txn.save(update_fields=['status', 'updated_at'])
                txn.booking.confirm_and_lock_seats()
                log.processed = True
                log.save(update_fields=['processed'])
    elif event_type == 'payment.failed' and payment_id:
        with transaction.atomic():
            txn = PaymentTransaction.objects.filter(transaction_id=payment_id).first()
            if txn and txn.status == 'INITIATED':
                txn.status = 'FAILED'
                txn.save(update_fields=['status', 'updated_at'])
                txn.booking.cancel_and_release_seats()
                log.processed = True
                log.save(update_fields=['processed'])

    return HttpResponse(status=200)
