import io
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, Line
from django.core.files.base import ContentFile
from django.conf import settings
from django.urls import reverse


def generate_qr_code_image(token_or_url):
    """
    Generates a QR code image as bytes using qrcode and PIL.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(token_or_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def generate_booking_ticket_pdf(booking, request=None):
    """
    Generates an enterprise-quality cinematic PDF boarding-pass style ticket.
    Returns bytes of the generated PDF and saves it to booking.pdf_ticket.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom palette
    primary_color = colors.HexColor('#0F172A')   # Slate 900
    brand_gold = colors.HexColor('#F59E0B')      # Amber 500
    accent_violet = colors.HexColor('#6366F1')   # Indigo 500
    text_dark = colors.HexColor('#1E293B')       # Slate 800
    text_muted = colors.HexColor('#64748B')      # Slate 500
    card_bg = colors.HexColor('#F8FAFC')         # Slate 50
    border_color = colors.HexColor('#E2E8F0')    # Slate 200

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=brand_gold,
        alignment=2 # Right
    )

    movie_title_style = ParagraphStyle(
        'MovieTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=text_dark,
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=text_muted,
    )

    val_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=text_dark,
    )

    val_accent = ParagraphStyle(
        'ValueAccent',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=accent_violet,
    )

    # Verification URL for QR Code
    if request:
        verify_url = request.build_absolute_uri(
            reverse('bookings:verify_ticket', kwargs={'token': booking.verification_token})
        )
    else:
        verify_url = f"https://cineverse.com/bookings/verify/{booking.verification_token}/"

    # Generate QR Code buffer
    qr_buf = generate_qr_code_image(verify_url)
    qr_img = RLImage(qr_buf, width=110, height=110)

    # Header Banner Table
    header_data = [
        [
            Paragraph("<b>🎬 CINEVERSE CINEMAS</b><br/><font size=8 color='#94A3B8'>OFFICIAL E-TICKET & BOARDING PASS</font>", title_style),
            Paragraph(f"<b>STATUS: {booking.get_status_display().upper()}</b><br/><font color='#CBD5E1'>BOOKING ID: {booking.booking_id}</font>", badge_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[360, 180])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_color),
        ('PADDING', (0, 0), (-1, -1), 16),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
    ]))

    # Movie & Booking Details
    show = booking.show
    movie = show.movie
    screen = show.screen
    theater = screen.theater

    seat_codes = booking.seats_display or "N/A"
    genres_str = ", ".join([g.name for g in movie.genres.all()[:3]])
    languages_str = ", ".join([l.name for l in movie.languages.all()[:2]])

    movie_meta = f"<font color='#64748B'>{movie.get_age_certification_display()} | {movie.duration_formatted} | {genres_str} | {languages_str}</font>"

    details_data = [
        [
            Paragraph(f"<b>{movie.title}</b><br/>{movie_meta}", movie_title_style),
            Paragraph(f"<b>VERIFICATION QR</b><br/><font size=7 color='#64748B'>Scan at cinema gate</font>", label_style)
        ],
        [
            # Left side: Show & Venue Info
            Table([
                [
                    Paragraph("CINEMA & THEATER", label_style),
                    Paragraph("AUDITORIUM / SCREEN", label_style)
                ],
                [
                    Paragraph(f"<b>{theater.name}</b><br/><font size=8 color='#64748B'>{theater.city.name} - {theater.landmark or theater.address[:30]}</font>", val_style),
                    Paragraph(f"<b>{screen.name}</b><br/><font size=8 color='#6366F1'>{screen.get_screen_type_display()}</font>", val_style)
                ],
                [
                    Paragraph("SHOW DATE", label_style),
                    Paragraph("SHOW TIME", label_style)
                ],
                [
                    Paragraph(f"<b>{show.show_date.strftime('%A, %d %B %Y')}</b>", val_style),
                    Paragraph(f"<b>{show.start_time.strftime('%I:%M %p')}</b>", val_accent)
                ],
                [
                    Paragraph("BOOKED SEATS", label_style),
                    Paragraph("TOTAL SEATS", label_style)
                ],
                [
                    Paragraph(f"<b>{seat_codes}</b>", val_accent),
                    Paragraph(f"<b>{booking.seats_count} Seat(s)</b>", val_style)
                ],
                [
                    Paragraph("BOOKED BY", label_style),
                    Paragraph("PAYMENT STATUS", label_style)
                ],
                [
                    Paragraph(f"<b>{booking.user.get_full_name() or booking.user.username}</b><br/><font size=8 color='#64748B'>{booking.user.email}</font>", val_style),
                    Paragraph(f"<b>PAID (₹{booking.final_amount})</b><br/><font size=8 color='#10B981'>Verified Online</font>", val_style)
                ],
            ], colWidths=[200, 180]),
            # Right side: QR Code
            Table([
                [qr_img],
                [Paragraph(f"<font size=7 color='#94A3B8'>TOKEN: {str(booking.verification_token)[:13]}...</font>", label_style)]
            ], colWidths=[140])
        ]
    ]

    details_table = Table(details_data, colWidths=[390, 150])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), card_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 1), (1, 1), 'CENTER'),
    ]))

    # Terms & Instructions Table
    terms_text = (
        "<b>Important Guidelines:</b><br/>"
        "• Please arrive at the cinema auditorium at least 15 minutes before showtime.<br/>"
        "• Present this e-ticket QR code on your mobile device at the entrance scanner for seamless check-in.<br/>"
        "• Age certification guidelines apply. Valid government photo ID may be verified at the premises.<br/>"
        "• Outside food, beverages, and recording equipment are strictly prohibited inside the theater.<br/>"
        "• Once confirmed, tickets are governed by Cineverse cinema policies."
    )
    terms_data = [
        [
            Paragraph(terms_text, ParagraphStyle('Terms', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=text_muted)),
            Paragraph(f"<b>Total Paid: ₹{booking.final_amount}</b><br/><font size=7 color='#64748B'>Inc. GST & Fees</font>", ParagraphStyle('Total', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=text_dark, alignment=2))
        ]
    ]
    terms_table = Table(terms_data, colWidths=[400, 140])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story = [
        header_table,
        Spacer(1, 4),
        details_table,
        Spacer(1, 4),
        terms_table,
    ]

    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()

    # Save to model instance
    filename = f"ticket_{booking.booking_id}.pdf"
    booking.pdf_ticket.save(filename, ContentFile(pdf_value), save=False)
    
    # Also save QR code image if not saved yet
    qr_buf.seek(0)
    qr_filename = f"qr_{booking.booking_id}.png"
    booking.qr_code_image.save(qr_filename, ContentFile(qr_buf.getvalue()), save=False)
    
    booking.save(update_fields=['pdf_ticket', 'qr_code_image'])

    return pdf_value
